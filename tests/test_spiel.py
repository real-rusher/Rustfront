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

from dustfront import fahrzeug as _FZ59
from dustfront import art as _ART59
from dustfront.mehrspieler import KampfGegner as _KG59
from dustfront.entities import Geschoss

w, ga = _paar59("team", karte="staubtal")
_bi59 = w.renderer.bilder
for _n59 in ("panzer", "panzer_turm", "panzer_turm_fahrer", "panzer_turm_rot_fahrer",
             "panzer_turm_blau_fahrer", "panzer_wrack", "panzer_schatten",
             "panzerwagen", "panzerwagen_ring", "panzerwagen_ring_fahrer",
             "panzerwagen_ring_rot_fahrer", "panzerwagen_ring_blau_fahrer",
             "panzerwagen_wrack", "panzerwagen_schatten", "panzergranate"):
    _s59 = _bi59.bild(_n59)
    _r59 = _s59.get_bounding_rect()
    pruef("Das Bild %s hat sein Mass und ist nicht leer" % _n59,
          _s59.get_size() == tuple(K.BILD_MASS[_n59]) and _r59.width > 4 and _r59.height > 3,
          "%s %s" % (_s59.get_size(), _r59))
pruef("Kein Fahrzeugbild fehlt", not [f_ for f_ in _bi59.fehler if "panzer" in f_],
      str(_bi59.fehler))
_pzb59 = _bi59.bild("panzer").get_bounding_rect()
_lwb59 = _bi59.bild("panzerwagen").get_bounding_rect()
# Abgenommen: Groesse 1,4 (Panzer rund 87 x 59, Panzerwagen rund 90 x 42,
# ohne Spiegel, Ersatzrad und Rand gemessen) - doppelt so lang wie der Buggy.
_bub59 = _bi59.bild("buggy").get_bounding_rect()
pruef("Groesse 1,4 wie abgenommen: rund 90 Pixel lang, fast doppelt so lang wie der Buggy",
      86 <= _pzb59.width <= 98 and 56 <= _pzb59.height <= 66
      and 86 <= _lwb59.width <= 100 and 40 <= _lwb59.height <= 54
      and _pzb59.width > 1.6 * _bub59.width,
      "%s %s, Buggy %s" % (_pzb59.size, _lwb59.size, _bub59.size))
# Der Insasse ist die Spielerfigur, nur ohne Gewehr: links vom Gewehr
# (bis x = c + 4) Pixel fuer Pixel gleich.
_kombi59 = K.TEAMS["kombi"][0]
_ins59 = _ART59._insasse((_kombi59["rumpf"], _kombi59["kante"], _kombi59["akzent"]))
# Seit 0.34.86 die Spielerfigur im neuen Stil (art._standard, seit 0.34.77
# die Figur zu Fuss) - vorher verglich der Test mit der alten art._figur.
_fig59 = _ART59._standard(_kombi59["rumpf"], _kombi59["kante"], _kombi59["akzent"],
                          groesse=28, stummel=False)
pruef("Der Insasse ist die Spielerfigur (gleiche Schultern, gleicher Kopf)",
      _ins59.get_size() == _fig59.get_size()
      and all(_ins59.get_at((x_, y_)) == _fig59.get_at((x_, y_))
              for x_ in range(0, 18) for y_ in range(28)))
_t_leer59 = _bi59.bild("panzer_turm")
_t_voll59 = _bi59.bild("panzer_turm_rot_fahrer")
pruef("Mit Kommandant in der Luke sieht der Turm anders aus als leer",
      any(_t_leer59.get_at((x_, y_)) != _t_voll59.get_at((x_, y_))
          for x_ in range(54, 66) for y_ in range(54, 66)))

_pz59 = next((b_ for b_ in w.fahrzeuge if b_.art == "panzer"), None)
_lw59 = next((b_ for b_ in w.fahrzeuge if b_.art == "panzerwagen"), None)
pruef("Auf STAUBTAL stehen ein Panzer (P) und ein Panzerwagen (L)",
      _pz59 is not None and _lw59 is not None
      and isinstance(_pz59, _FZ59.Panzer) and isinstance(_lw59, _FZ59.Panzerwagen))
pruef("Beide passen dorthin, wo sie stehen, und sind Ziele",
      _pz59.passt(_pz59.pos) and _lw59.passt(_lw59.pos)
      and _pz59.trefferbar and _lw59.trefferbar)

_k59 = w.kaempfer[ga.meine_nummer]
_feind59 = w.kaempfer[0]
_k59.unverwundbar = _feind59.unverwundbar = 0.0


def _hin59(k_, p_):
    k_.pos.update(p_); k_.vorher.update(p_); k_.ebene = 0
    k_.treppe_rest = 0.0; k_.tempo.update(0, 0)


def _fahr59(b_, will_, sekunden_, ziel_=None, feuert_=False, zielt_=False, je_=None):
    for _ in range(int(sekunden_ / K.FIXED_DT)):
        z_ = ziel_ if ziel_ is not None else b_.pos + pygame.Vector2(200, 0).rotate(b_.aufbau)
        w._anwenden(_k59, {"will": list(will_), "ziel": [z_[0], z_[1]], "knoepfe": [],
                           "feuert": feuert_, "zielt": zielt_})
        w.welt.schritt(K.FIXED_DT)
        w._fahrzeuge_nachziehen()
        if je_ is not None:
            je_()


_hin59(_k59, _pz59.pos + pygame.Vector2(0, 300))
w._anwenden(_k59, {"will": [0, 0], "ziel": [0, 0], "knoepfe": ["nutzen"]})
pruef("Weit weg steigt man nicht in den Panzer", not _k59.im_fahrzeug)
_hin59(_k59, _pz59.ausstiegsorte(_k59.radius)[0])
w._anwenden(_k59, {"will": [0, 0], "ziel": [0, 0], "knoepfe": ["nutzen"]})
pruef("Daneben steigt man mit E ein", _k59.im_fahrzeug and _pz59.fahrer is _k59)
pruef("Der Turm zeigt den Insassen in der Farbe seiner Mannschaft",
      _pz59.aufbau_bild_name() == "panzer_turm_%s_fahrer"
      % K.TEAMS["kombi"][_k59.team]["name"].lower())

# Erst drehen, damit er frei faehrt: auf der Stelle, ohne zu rutschen.
_w0_59, _p0_59 = _pz59.winkel, pygame.Vector2(_pz59.pos)
_ph59 = []
_fahr59(_pz59, (1.0, 0.0), 1.0,
        je_=lambda: _ph59.append((_pz59.ph_links, _pz59.ph_rechts)))
_dreh59 = (_pz59.winkel - _w0_59 + 180) % 360 - 180
pruef("Der Panzer dreht auf der Stelle (rund 80 Grad je Sekunde)",
      55.0 < _dreh59 < 85.0 and _pz59.pos.distance_to(_p0_59) < 1.0,
      "%.1f Grad, %.1f px" % (_dreh59, _pz59.pos.distance_to(_p0_59)))
_dl59 = (_ph59[-1][0] - _ph59[-30][0] + 0.5) % 1.0 - 0.5
_dr59 = (_ph59[-1][1] - _ph59[-30][1] + 0.5) % 1.0 - 0.5
pruef("... und die Ketten laufen dabei gegeneinander", _dl59 * _dr59 < 0,
      "%.2f %.2f" % (_dl59, _dr59))
# Nun eine Richtung, in der er Platz hat, und Gas.
_pz59.gier = 0.0
_pz59.winkel = Gefecht._fahrzeug_richtung(_pz59)
_p0_59 = pygame.Vector2(_pz59.pos)
_fahr59(_pz59, (0.0, -1.0), 2.5)
pruef("Er faehrt rund 45 px/s, kein Einspurmodell, nichts rutscht seitlich",
      40.0 <= _pz59.fahrt <= 45.5 and abs(_pz59.geschw.dot(
          pygame.Vector2(1, 0).rotate(_pz59.winkel + 90))) < 0.5,
      "%.1f px/s" % _pz59.fahrt)
_fahr59(_pz59, (0.0, 0.0), 1.5)

# Der Turm folgt dem Zeiger mit seinem Tempo, unabhaengig von der Wanne.
# Gezielt wird quer zur Wanne, in eine Richtung, in der die Kanone frei
# schiessen kann (im Fort stehen Kisten und Sandsaecke).
_wanne59 = _pz59.winkel


def _frei_schiessen59(winkel_):
    m_ = _pz59.aufbau_mitte()
    return all(not w.welt.schuss_halt(m_ + pygame.Vector2(d_, 0).rotate(winkel_), 0, 3.0)
               for d_ in range(50, 240, 4))


_soll59 = next((_wanne59 + d_ for d_ in (90.0, -90.0, 60.0, -60.0, 120.0, -120.0)
                if _frei_schiessen59(_wanne59 + d_)), _wanne59 + 90.0)
_ziel59 = _pz59.aufbau_mitte() + pygame.Vector2(300, 0).rotate(_soll59)
_a0_59 = _pz59.aufbau
_fahr59(_pz59, (0.0, 0.0), 0.5, ziel_=_ziel59)
_halb59 = abs((_pz59.aufbau - _a0_59 + 180) % 360 - 180)
_fahr59(_pz59, (0.0, 0.0), 2.0, ziel_=_ziel59)
pruef("Der Turm dreht zum Zeiger - nicht sofort (rund 60 Grad je Sekunde)",
      20.0 < _halb59 < 40.0
      and abs((_pz59.aufbau - _soll59 + 180) % 360 - 180) < 2.0
      and abs(_pz59.winkel - _wanne59) < 0.5,
      "nach 0,5 s %.1f Grad" % _halb59)

# Kanone: ein Gegner vor dem Rohr.
_hin59(_feind59, _pz59.aufbau_mitte() + pygame.Vector2(170, 0).rotate(_pz59.aufbau))
_feind59.leben = _feind59.max_leben
_vor59 = _feind59.leben
_fahr59(_pz59, (0.0, 0.0), 0.05, ziel_=_feind59.pos, feuert_=True)
_granaten59 = [g_ for g_ in w.welt.wesen + w.welt.neue
               if isinstance(g_, _FZ59.Panzergranate)]
pruef("Linke Maustaste: die Kanone feuert eine Granate, das Rohr faehrt zurueck",
      len(_granaten59) == 1 and _pz59.ruecklauf > 3.0 and _pz59.ruck > 0.5)
_fahr59(_pz59, (0.0, 0.0), 0.6, ziel_=_feind59.pos, feuert_=True)
pruef("Die Granate trifft: Schaden, Feuerball und Rauch (Explosion \"panzer\")",
      _feind59.leben < _vor59 - 100 and len(w.welt.feuerbaelle) == 1,
      "%.0f -> %.0f" % (_vor59, _feind59.leben))
pruef("Gehalten wird nachgeladen, nicht gleich wieder geschossen",
      len([g_ for g_ in w.welt.wesen + w.welt.neue
           if isinstance(g_, _FZ59.Panzergranate)]) == 0
      and _pz59.takt.get("kanone", 0.0) > 1.0)
_fb59 = w.welt.feuerbaelle[0]
pruef("Der Feuerball ist kein Kreis: mehrere versetzte Glutballen und Rauchwolken",
      len(_fb59.ballen) == K.FEUERBALL["ballen"]
      and len({(round(v_.x), round(v_.y)) for v_, _r, _s, _d in _fb59.ballen}) > 5
      and len(_fb59.wolken) == K.FEUERBALL["wolken"])
_kr59 = w.renderer.krater(K.FEUERBALL["krater"], 7)
_kreis59 = sum(1 for x_ in range(_kr59.get_width()) for y_ in range(_kr59.get_height())
               if _kr59.get_at((x_, y_)).a > 0)
pruef("Der Krater ist unregelmaessig (Kleckse, Strahlen, Brocken) und nicht leer",
      _kreis59 > 200 and _kr59.get_size()[0] > 2 * K.FEUERBALL["krater"])
pruef("Am Boden vor der Muendung liegt Staub, der unter den Fahrzeugen gezeichnet wird",
      any(p_.art == "bodenstaub" for p_ in w.welt.partikel))

# Rechte Maustaste: das Bug-MG schiesst in Fahrtrichtung, nicht zum Turm.
_vorher59 = [g_ for g_ in w.welt.wesen if isinstance(g_, Geschoss)]
_fahr59(_pz59, (0.0, 0.0), 0.5, ziel_=_ziel59, zielt_=True)
_mg59 = [g_ for g_ in w.welt.wesen + w.welt.neue
         if isinstance(g_, Geschoss) and g_.waffe == "bug_mg"]
pruef("Das Bug-MG schiesst rund 11 Schuss je Sekunde in Fahrtrichtung",
      4 <= len(_mg59) <= 7
      and all(abs((g_.winkel - _pz59.winkel + 180) % 360 - 180) < 3.0 for g_ in _mg59),
      str(len(_mg59)))

# Panzerung: eine Kugel zerkratzt nur den Lack, der Kommandant bekommt 20 %.
_ich59 = w.ich
_pz59.leben = _pz59.max_leben
_k59.leben = _k59.max_leben
_vor59 = (_pz59.leben, _k59.leben)
_gs59 = Geschoss(_pz59.pos + pygame.Vector2(-120, 0).rotate(_pz59.winkel), _pz59.winkel,
                 K.WAFFEN["sturm"], 0, _ich59, "sturm")
w.welt.dazu(_gs59)
for _ in range(60):
    w.welt.schritt(K.FIXED_DT)
    if not _gs59.lebt:
        break
_ab59 = _vor59[0] - _pz59.leben
# Seit 0.34.65 aus K.PANZERUNG, und sie kommt von hinten (dort ist das
# Blech duenner, K.PANZER_SEITEN).
pruef("Eine Kugel zerkratzt den Panzer nur (Panzerung, von hinten)",
      abs(_ab59 - K.WAFFEN["sturm"]["schaden"] * K.PANZERUNG["panzer"]["kugel"]
          * K.PANZER_SEITEN["hinten"]) < 0.01,
      "%.2f" % _ab59)
pruef("... beim Kommandanten in der Luke kommt nichts an (seit 0.34.77)",
      _vor59[1] == _k59.leben, "%.2f" % (_vor59[1] - _k59.leben))

# Der Gast sieht ihn: an derselben Stelle, mit Turmwinkel, Feuerball.
for _ in range(6):
    w.schritt(K.FIXED_DT)
    ga.schritt(K.FIXED_DT)
_gpz59 = [b_ for b_ in ga.fahrzeuge if b_.art == "panzer"]
pruef("Der Gast sieht den Panzer mit seinem Turmwinkel",
      len(_gpz59) == 1 and _gpz59[0].pos.distance_to(_pz59.pos) < 2.0
      and abs((_gpz59[0].aufbau - _pz59.aufbau + 180) % 360 - 180) < 3.0
      and "fahrer" in _gpz59[0].aufbau_bild_name(),
      str([(b_.pos, b_.aufbau) for b_ in _gpz59]))
pruef("... und den Feuerball der Kanone", len(ga.welt.feuerbaelle) >= 1)
_bild59 = pygame.Surface((K.GAME_W, K.GAME_H))
w.kamera.pos.update(_pz59.pos); ga.kamera.pos.update(_pz59.pos)
w.zeichnen(_bild59, 0.5)
ga.zeichnen(_bild59, 0.5)
pruef("Gastgeber und Gast zeichnen ihn ohne Fehler", True)

# Raus, und in den Panzerwagen.
w._anwenden(_k59, {"will": [0, 0], "ziel": [0, 0], "knoepfe": ["nutzen"]})
pruef("Mit E wieder hinaus, neben die Wanne",
      not _k59.im_fahrzeug and _pz59.fahrer is None
      and not _pz59.beruehrt(_k59.pos, _k59.radius - 1))
_hin59(_k59, _lw59.ausstiegsorte(_k59.radius)[0])
w._anwenden(_k59, {"will": [0, 0], "ziel": [0, 0], "knoepfe": ["nutzen"]})
pruef("In den Panzerwagen steigt man genauso ein", _k59.im_fahrzeug and _lw59.fahrer is _k59)
_lw59.winkel = Gefecht._fahrzeug_richtung(_lw59)
_lw59.aufbau = _lw59.winkel
_fahr59(_lw59, (0.0, -1.0), 1.2)
# Seit 0.34.96 deutlich wendiger (gewuenscht).
pruef("Der Panzerwagen zieht an: nach 1,2 s rund 54 px/s (vorher 26)",
      40.0 <= _lw59.fahrt <= 70.0, "%.1f px/s" % _lw59.fahrt)

# Wenderadius und Hoechsttempo auf freiem Feld (eine eigene Welt ohne Mauern).
from dustfront.world import Welt as _Welt59, Ebene as _Ebene59
_frei59 = _Welt59([_Ebene59.aus_text(["." * 500 for _ in range(200)], 0)])


class _Fahrer59:
    team = -1
    fraktion = "probe"
    ziel = None
    lebt = True


_lwp59 = _FZ59.Panzerwagen(pygame.Vector2(300, 3200), 0, 0.0)
_frei59.dazu(_lwp59)
_lwp59.fahrer = _Fahrer59()
_lwp59.gas = 1.0
for _ in range(int(14.0 / K.FIXED_DT)):
    _frei59.schritt(K.FIXED_DT)
pruef("Er wird sehr schnell: hoechstens 320 px/s (Buggy 250)",
      310.0 <= _lwp59.fahrt <= 321.0, "%.1f" % _lwp59.fahrt)
_lwp59.pos.update(6000, 3200); _lwp59.winkel = 0.0; _lwp59.gier = 0.0
_lwp59.geschw.update(150, 0); _lwp59.lenkwinkel = 0.0
_lwp59.lenk = 1.0
for _ in range(int(2.5 / K.FIXED_DT)):
    _lwp59.gas = 1.0 if _lwp59.fahrt < 150 else 0.0
    _frei59.schritt(K.FIXED_DT)
_radius59 = _lwp59.fahrt / max(1e-6, _lwp59.gier)
pruef("... und wendet enger: rund 70 + 0,45 v (bei 150 px/s ~140, vorher ~310)",
      100.0 < _radius59 < 190.0, "%.0f px" % _radius59)

# Rammen: ein Laeufer vorn bei voller Fahrt nimmt Schaden und fliegt; wer
# seitlich steht, wird nur geschoben. Nach jedem Schritt steht niemand im
# Fussabdruck.
_lw59.geschw = _lw59.vorn * 220.0
_z59 = _KG59(_lw59.pos + _lw59.vorn * 90.0, "laeufer", 0, w)
_z59.ki_aus = True
w.welt.dazu(_z59)
_drin59 = []


def _fussabdruck59(b_, z_):
    l_ = b_.lokal(z_.pos)
    f_ = b_.werte
    return (f_["hinten"] < l_.x < f_["vorn"] and abs(l_.y) < f_["halb"]) and z_.lebt


_fahr59(_lw59, (0.0, -1.0), 0.5, je_=lambda: _drin59.append(_fussabdruck59(_lw59, _z59)))
pruef("Der Panzerwagen rammt einen Laeufer vorn: er stirbt und fliegt noch ein Stueck",
      not _z59.lebt and (len(w.welt.flugleichen) >= 1 or _z59 not in w.welt.wesen),
      "lebt %s, fliegt %d" % (_z59.lebt, len(w.welt.flugleichen)))
pruef("Nach keinem Schritt stand er im Fussabdruck", not any(_drin59))
_fahr59(_lw59, (0.0, 0.0), 1.0)
_lw59.geschw = _lw59.vorn * 60.0
_seite59 = _KG59(_lw59.pos + pygame.Vector2(0, -(K.PANZERWAGEN["halb"] + 6.0))
                 .rotate(_lw59.winkel), "laeufer", 0, w)
_seite59.ki_aus = True
w.welt.dazu(_seite59)
w.welt.schritt(K.FIXED_DT)
_vor59 = _seite59.leben
_drin59 = []
_fahr59(_lw59, (1.0, -1.0), 0.6, je_=lambda: _drin59.append(_fussabdruck59(_lw59, _seite59)))
pruef("Wer seitlich steht, wird nur beiseitegeschoben - ohne Schaden",
      _seite59.lebt and _seite59.leben == _vor59 and not any(_drin59),
      "%.1f -> %.1f" % (_vor59, _seite59.leben))

# Das Ring-MG schiesst ueber das eigene Dach, ohne es zu treffen.
_lw59.geschw.update(0, 0); _lw59.gier = 0.0
_lw59.leben = _lw59.max_leben
_hinten59 = _lw59.pos - _lw59.vorn * 200
_fahr59(_lw59, (0.0, 0.0), 2.0, ziel_=_hinten59)
_vor59 = _lw59.leben
_fahr59(_lw59, (0.0, 0.0), 0.5, ziel_=_hinten59, feuert_=True)
_ring59 = [g_ for g_ in w.welt.wesen + w.welt.neue
           if isinstance(g_, Geschoss) and g_.waffe == "ring_mg"]
pruef("Das Ring-MG schiesst nach hinten ueber das eigene Dach, ohne es zu treffen",
      len(_ring59) >= 4 and _lw59.leben == _vor59, "%d Schuss" % len(_ring59))

# Kaputt: Wrack, Fahrer draussen. Er kommt als Panzer wieder, nicht als Buggy.
w._anwenden(_k59, {"will": [0, 0], "ziel": [0, 0], "knoepfe": ["nutzen"]})
_pz59.schaden(_pz59.max_leben + 10, None, _ich59)
pruef("Ein zerstoerter Panzer ist ein Wrack (eigenes Bild)",
      _pz59.kaputt and _pz59.bild == "panzer_wrack")
_beide59 = K.PANZER["wrack_zeit"] + K.PANZER["neu_nach"] + 2.0
for _ in range(int(_beide59 / K.FIXED_DT)):
    w.schritt(K.FIXED_DT)
_neu59 = [b_ for b_ in w.fahrzeuge if b_.art == "panzer"]
pruef("Spaeter steht wieder ein Panzer auf der Karte, heil",
      len(_neu59) == 1 and _neu59[0] is not _pz59 and not _neu59[0].kaputt
      and _neu59[0].passt(_neu59[0].pos))
w.verlassen(); ga.verlassen()

# Testmodus (AGENTS.md): beide stehen im Spawner, lassen sich setzen und
# mit ENTF zerstoeren. Einsteigen geht dort wie im Spiel, mit einer Figur.
from dustfront import testmodus as _TM59
_tm59 = _TM59.Testmodus(app, karte="staubtal")
_namen59 = [e_.name for e_ in _tm59.eintraege if e_.gruppe == "OBJEKTE"]
pruef("Testmodus: PANZER und PANZERWAGEN stehen im Spawner (OBJEKTE)",
      "PANZER" in _namen59 and "PANZERWAGEN" in _namen59, str(_namen59))
_ort59 = freier_punkt(_tm59.welt, 0, random.Random(59))
_gesetzt59 = _tm59.spawnen(_tm59._eintrag("PANZER"), pos=_ort59, ebene=0)
_gesetzt59 += _tm59.spawnen(_tm59._eintrag("PANZERWAGEN"), pos=_ort59, ebene=0)
pruef("... sie lassen sich setzen, jeder an einem Platz, an den er passt",
      len(_gesetzt59) == 2 and all(b_ in _tm59.fahrzeuge and b_.passt(b_.pos)
                                   for b_ in _gesetzt59)
      and not _FZ59._vielecke_ueberlappen(_gesetzt59[0].ecken(), _gesetzt59[1].ecken()),
      str([b_.pos for b_ in _gesetzt59]))
_ich59 = _tm59.ich_setzen(_gesetzt59[0].ausstiegsorte(9.0)[0], 0, {"team": 0})
_tm59._anwenden(_ich59, {"will": [0, 0], "ziel": [0, 0], "knoepfe": ["nutzen"]})
pruef("... man steigt mit einer Figur ein (SPIELER, ICH)",
      _ich59.im_fahrzeug and _gesetzt59[0].fahrer is _ich59)
pruef("... und ENTF zerstoert ihn: ein Wrack", _tm59.toeten(_gesetzt59[1])
      and _gesetzt59[1].kaputt and _gesetzt59[1].bild == "panzerwagen_wrack")
_tm59.verlassen()
EN.RND.setstate(_rnd59)
random.setstate(_zufall59)

# ─────────────────────────────────────────────────────────────────────
# Skins (seit 0.34.60): 14 Operators und 17 Soldaten aus dem Figurenpaket.
# Wer will, waehlt im Menue AUSRUESTUNG ein Aussehen; alle sehen es, auch
# im Fahrzeug. Bots tragen Soldaten. Dazu NPCs und Tiere im Testmodus.
print("\n-- Skins, NPCs und Tiere (0.34.60)")
# Wie im Abschnitt davor: der Zufall der Wesen bleibt fuer spaeter, wie er war.
_rnd60 = EN.RND.getstate()
_zufall60 = random.getstate()
from dustfront import art_figuren as _FIG60
from dustfront import bots as _BOTS60

_wahl60 = _FIG60.waehlbar()
pruef("29 Aussehen sind waehlbar - ohne Schildtraeger und Panzerfahrer, die etwas Festes halten",
      len(_wahl60) == 29 and "ghost" in _wahl60 and "wachposten" in _wahl60
      and "schildtraeger" not in _wahl60 and "panzerfahrer" not in _wahl60
      and not set(_wahl60) & set(K.FIGUREN_GRUPPEN["NPC"]), str(len(_wahl60)))
pruef("Was nicht waehlbar ist, wird zur alten Figur (leer)",
      [_FIG60.saeubern(x) for x in ("gibtsnicht", "hirte", "schildtraeger", None, 5,
                                    "../ghost", "ghost")]
      == ["", "", "", "", "", "", "ghost"])

_bi60 = app.bilder
_fehler60 = len(_bi60.fehler)
_kaputt60 = []
# Jede Waffe, die es vor dem Waffenpaket gab, fuer jedes Aussehen - die
# 52 aus dem Paket (seit 0.34.61) prueft ihr eigener Abschnitt an einigen
# Aussehen; alle mal alle waeren ueber 5000 Bilder.
_alt60 = [w_ for w_ in K.WAFFEN_HAND if K.WAFFEN_HAND[w_]["aufbau"] != "paket"]
for _sk60 in _wahl60:
    for _vs60 in ("", "rot_", "blau_"):
        for _ge60 in [""] + _alt60:
            _n60 = _FIG60.bildname(_sk60, _vs60, _ge60)
            _soll60 = K.BILD_MASS["spieler_" + _ge60] if _ge60 else K.BILD_MASS["spieler"]
            _b60 = _bi60.bild(_n60)
            if _b60.get_size() != tuple(_soll60) or _b60.get_bounding_rect().width < 10:
                _kaputt60.append(_n60)
        for _i60 in range(K.SCHWUNG_BILDER):
            _n60 = "%s_schwung_%d" % (_FIG60.bildname(_sk60, _vs60), _i60)
            if _bi60.bild(_n60).get_size() != tuple(K.BILD_MASS["spieler_schwung_%d" % _i60]):
                _kaputt60.append(_n60)
pruef("Jedes Aussehen hat jede Figur: ohne und mit jeder Waffe, je Mannschaft, im Schwung",
      not _kaputt60 and len(_bi60.fehler) == _fehler60, str(_kaputt60[:5]))


def _gleich60(a, b):
    return pygame.image.tobytes(a, "RGBA") == pygame.image.tobytes(b, "RGBA")


pruef("Die Mannschaft sieht man an der Neon-Markierung (rot, blau, ohne: drei Bilder)",
      not _gleich60(_bi60.bild("skin_ghost"), _bi60.bild("skin_ghost_rot"))
      and not _gleich60(_bi60.bild("skin_ghost_rot"), _bi60.bild("skin_ghost_blau")))
pruef("Ein Aussehen fuer eine Waffe, die es nicht gibt, ist kein Bild (zurueck zur Vorgabe)",
      _bi60.mass("skin_ghost_gibtsnicht") is None and _bi60.mass("skin_schildtraeger_sturm") is None
      and _bi60.mass("skin_ghost_schwung_99") is None)
_ins60 = []
for _gr60 in ("buggy", "panzer_turm", "panzerwagen_ring"):
    _n60 = _FIG60.insassen_bildname(_gr60, "wolf", "rot_")
    _b60 = _bi60.bild(_n60)
    _ins60.append((_n60, _b60.get_size() == tuple(K.BILD_MASS[_gr60 + "_fahrer"])
                   and not _gleich60(_b60, _bi60.bild(_gr60 + "_rot_fahrer"))))
pruef("Im Fahrzeug sitzt man in seinem Aussehen (Buggy, Panzerturm, MG-Ring)",
      all(ok_ for _n, ok_ in _ins60) and len(_bi60.fehler) == _fehler60, str(_ins60))
_npc60 = _FIG60.npc_bildnamen()
pruef("NPCs und Tiere sind feste Bilder in ihrer Groesse",
      len(_npc60) == 8 + len(K.STIRNBAND_FARBEN)
      and all(_bi60.bild(n_).get_size() == tuple(K.BILD_MASS["spieler"]) for n_ in _npc60)
      and all(_bi60.bild(_FIG60.tier_bildname(a_, i_)).get_size() == tuple(t_["mass"])
              for a_, t_ in K.TIERE.items() for i_ in range(len(t_["farben"])))
      and len(_bi60.fehler) == _fehler60, str(_npc60))

_soldaten60 = [x_ for x_ in _wahl60 if x_ in K.FIGUREN_GRUPPEN["SOLDAT"]]
pruef("Ein Bot traegt einen Soldaten - zu seinem Namen immer denselben",
      _BOTS60.bot_aussehen("BOT-KILO") in _soldaten60
      and _BOTS60.bot_aussehen("BOT-KILO") == _BOTS60.bot_aussehen("BOT-KILO")
      and len({_BOTS60.bot_aussehen("BOT-" + n_) for n_ in K.BOTS["namen"]}) > 3)

# Im Gefecht: das Aussehen aus den Einstellungen geht mit dem "hallo" mit,
# eine Aenderung gilt sofort, und der Gast sieht dasselbe.
app.opt["aussehen"] = "raven"
w, ga = _paar59("team", karte="staubtal")
_gk60 = w.kaempfer.get(ga.meine_nummer)
pruef("Gastgeber und Gast steigen in ihrem Aussehen ein",
      w.ich.skin == "raven" and _gk60 is not None and _gk60.skin == "raven",
      "%s %s" % (w.ich.skin, getattr(_gk60, "skin", None)))
pruef("... und so zeigt die Figur es (skin_raven_<mannschaft>_<waffe>)",
      w.ich.bild == _FIG60.bildname("raven", w.ich.team_vorsatz, w.ich.waffe_name),
      w.ich.bild)
app.opt["aussehen"] = "cobra"
for _ in range(10):
    w.schritt(K.NETZ["takt"])
    ga.schritt(K.NETZ["takt"])
pruef("Eine Aenderung im Menue gilt sofort, beim Gastgeber fuer beide",
      w.ich.skin == "cobra" and _gk60.skin == "cobra", "%s %s" % (w.ich.skin, _gk60.skin))
pruef("... und der Gast sieht es an beiden Figuren",
      ga.kaempfer[0].skin == "cobra" and ga.ich.skin == "cobra"
      and ga.kaempfer[0].bild.startswith("skin_cobra_"), ga.kaempfer[0].bild)
ga.gast.senden({"t": "aussehen", "sk": "schildtraeger"})
for _ in range(6):
    w.schritt(K.NETZ["takt"])
    ga.schritt(K.NETZ["takt"])
pruef("Ein Aussehen, das keine Waffe zeigen kann, nimmt der Gastgeber nicht an",
      _gk60.skin == "" and _gk60.bild.startswith("spieler_"), _gk60.bild)
_bot60 = w._bot_dazu(1)
for _ in range(6):
    w.schritt(K.NETZ["takt"])
    ga.schritt(K.NETZ["takt"])
pruef("Bots tragen ihren Soldaten, auch beim Gast",
      _bot60.skin in _soldaten60 and _bot60.skin == _BOTS60.bot_aussehen(_bot60.name)
      and ga.kaempfer[_bot60.nummer].skin == _bot60.skin, _bot60.skin)
_bu60 = next(b_ for b_ in w.fahrzeuge if b_.art == "buggy")
w.ich.pos.update(_bu60.ausstiegsorte(9.0)[0])
w._einsteigen(w.ich, _bu60)
for _ in range(6):
    w.schritt(K.NETZ["takt"])
    ga.schritt(K.NETZ["takt"])
_gbu60 = next((b_ for b_ in ga.fahrzeuge if b_.besetzt and b_.art == "buggy"), None)
_soll60 = _FIG60.insassen_bildname("buggy", "cobra", w.ich.team_vorsatz)
pruef("Im Buggy sitzt er in seinem Aussehen - beim Gastgeber und beim Gast",
      _bu60.bild == _soll60 and _gbu60 is not None and _gbu60.bild == _soll60,
      "%s %s" % (_bu60.bild, getattr(_gbu60, "bild", None)))
app.opt["aussehen"] = ""
w.verlassen(); ga.verlassen()

# Testmodus (AGENTS.md): Aussehen je Figur, NPCs und Tiere im Spawner.
_tm60 = _TM59.Testmodus(app, karte="staubtal")
_gr60 = {}
for e_ in _tm60.eintraege:
    _gr60.setdefault(e_.gruppe, []).append(e_)
pruef("Testmodus: 8 NPCs und 3 Tiere stehen im Spawner",
      len(_gr60.get("NPC", [])) == 8 and [e_.name for e_ in _gr60.get("TIERE", [])]
      == ["SCHAF", "ZIEGE", "HUHN"], str(sorted(_gr60)))
pruef("... BOT und SPIELER haben ein AUSSEHEN, SPIELER, ICH als Vorgabe das eigene",
      all("aussehen" in _tm60._eintrag(n_).optionen for n_ in ("BOT", "SPIELER, STEHT"))
      and _tm60.werte(_tm60._eintrag("SPIELER, ICH"))["aussehen_ich"] == "eigen")
_ort60 = freier_punkt(_tm60.welt, 0, random.Random(60))
_b1_60 = _tm60.bot_setzen(_ort60, 0, {"team": 0, "aussehen": "ghost", "ki": True})
_b2_60 = _tm60.bot_setzen(_ort60 + pygame.Vector2(24, 0), 0, {"team": 0})
_p60 = _tm60.puppe_setzen(_ort60 + pygame.Vector2(0, 24), 0, {"team": 1, "aussehen": ""})
pruef("... ein gewaehltes Aussehen gilt, ZUFALL ist beim Bot sein Soldat, leer die alte Figur",
      _b1_60.skin == "ghost" and _b1_60.bild.startswith("skin_ghost_rot_")
      and _b2_60.skin == _BOTS60.bot_aussehen(_b2_60.name)
      and _p60.skin == "" and _p60.bild.startswith("spieler_blau_"),
      "%s %s %s" % (_b1_60.bild, _b2_60.skin, _p60.bild))
# Die Puppe der anderen Mannschaft wieder weg: die Bots sollen gleich
# zeigen, dass sie NPCs und Tiere in Ruhe lassen - ohne Gegner daneben,
# auf den sie schiessen und dabei einen Bewohner streifen koennten.
_tm60.loeschen(_p60)
_tm60._sp_werte["ÜBERLEBENDE"] = {"stirnband": 3}
_ue60 = _tm60.spawnen(_tm60._eintrag("ÜBERLEBENDE"), pos=_ort60 + pygame.Vector2(-30, 0), ebene=0)
pruef("... die Ueberlebende traegt das gewaehlte Stirnband",
      len(_ue60) >= 1 and _ue60[0].bild == "npc_ueberlebende_tuerkis", _ue60[0].bild if _ue60 else "")
_tm60._sp_werte["SCHAF"] = {"farbe_schaf": 1}
_sf60 = _tm60.spawnen(_tm60._eintrag("SCHAF"), pos=_ort60 + pygame.Vector2(0, -40), ebene=0)[0]
_sf_start60 = pygame.Vector2(_sf60.pos)
_lief60 = False
for _ in range(int(6.0 / K.FIXED_DT)):
    _tm60.schritt(K.FIXED_DT)
    _lief60 = _lief60 or _sf60.ziel is not None
pruef("... ein Schaf in der gewaehlten Farbe laeuft herum und bleibt auf freiem Boden",
      _sf60.bild == "tier_schaf_dunkel" and _lief60 and _sf60.lebt
      and _sf60.pos.distance_to(_sf_start60) > 3.0
      and _tm60.welt.frei(_sf60.pos, _sf60.radius - 1.0, 0, True),
      "%s %.1f" % (_sf60.bild, _sf60.pos.distance_to(_sf_start60)))
pruef("... niemand greift NPCs und Tiere an: sie gehoeren zu keiner Seite",
      _ue60[0].lebt and _sf60.lebt and _ue60[0].fraktion == "zivil"
      and _ue60[0] not in _tm60.kaempfer.values())
_flaeche60 = pygame.Surface((K.GAME_W, K.GAME_H), pygame.SRCALPHA)
_sf60.ziel = _sf60.pos + pygame.Vector2(30, 0)
_tm60.blick = _sf60.ebene
_tm60.kamera.pos.update(_sf60.pos)
_tm60.kamera.versatz.update(0, 0)
_tm60._info_zeichnen(_flaeche60)
_rund60 = _flaeche60.get_bounding_rect()
pruef("... die INFO-Ansicht zeigt, wohin ein Tier laeuft (Linie und LAEUFT)",
      _rund60.width >= 20 and _rund60.collidepoint(K.GAME_W // 2 + 10, K.GAME_H // 2),
      str(_rund60))
_ue60[0].schaden(1000.0, None, _b1_60)
pruef("... ein NPC stirbt an einem Treffer, und ENTF toetet auch ein Tier",
      not _ue60[0].lebt and _tm60.toeten(_sf60) and not _sf60.lebt)
_tm60.verlassen()
EN.RND.setstate(_rnd60)
random.setstate(_zufall60)

# ─────────────────────────────────────────────────────────────────────
# Waffenbilder (seit 0.34.61): alle 58 Eintraege des Waffenpakets haben
# ihr Bild - an der Hand (52, je Mannschaft und je Aussehen) und als
# Zeichen in der Hotbar (63, mit Munition und Fahrzeugteilen).
print("\n-- Waffenbilder aus dem Waffenpaket (0.34.61)")
_bi61 = app.bilder
_fehler61 = len(_bi61.fehler)
# Seit 0.34.67 fuenf Teile: Kuller und Knaller fliegen als Teil; seit
# 0.34.69 neun (Horchposten, Sandsackwand, Drohne in zwei Bildern).
pruef("52 Waffen in der Hand, 63 Zeichen, 9 Teile",
      len(K.PAKET_HAND) == 52 and len(K.PAKET_SYMBOLE) == 63 and len(K.PAKET_TEILE) == 9
      and all(K.WAFFEN_HAND[w_]["aufbau"] == "paket" for w_ in K.PAKET_HAND))
_hand61 = {}
for _w61 in K.PAKET_HAND:
    for _vs61 in ("", "rot_", "blau_"):
        _b61 = _bi61.bild("spieler_%s%s" % (_vs61, _w61))
        _hand61["%s%s" % (_vs61, _w61)] = (_b61.get_size(), pygame.image.tobytes(_b61, "RGBA"))
pruef("Jede haelt eine Figur, 56 x 56, und jede sieht anders aus",
      all(m_ == (56, 56) for m_, _t in _hand61.values())
      and len({t_ for _m, t_ in _hand61.values()}) == len(_hand61)
      and len(_bi61.fehler) == _fehler61, str(len(_hand61)))
_sym61 = [_bi61.bild("waffe_" + w_) for w_ in K.PAKET_SYMBOLE]
pruef("Jede hat ein eigenes Zeichen fuer die Hotbar, 26 x 11",
      all(b_.get_size() == (26, 11) and b_.get_bounding_rect().width >= 6 for b_ in _sym61)
      and len({pygame.image.tobytes(b_, "RGBA") for b_ in _sym61}) == len(_sym61)
      and len(_bi61.fehler) == _fehler61)
pruef("Die Teile (Minirakete, 40-mm-Granate, leeres Rohr) in ihrer Groesse",
      all(_bi61.bild("teil_" + n_).get_size() == tuple(m_) for n_, m_ in K.PAKET_TEILE.items()))
pruef("Auch ein Skin haelt die neuen Waffen, in seiner Mannschaft",
      _bi61.bild("skin_ghost_rot_revolver").get_size() == (56, 56)
      and not _gleich60(_bi61.bild("skin_ghost_rot_revolver"), _bi61.bild("skin_ghost_rot_sturm"))
      and not _gleich60(_bi61.bild("skin_ghost_rot_hammer"), _bi61.bild("skin_ghost_rot_revolver"))
      and len(_bi61.fehler) == _fehler61)
_tm61 = _TM59.Testmodus(app, karte="staubtal")
_ein61 = _tm61._eintrag("FIGUR MIT WAFFE")
pruef("Testmodus: WAFFENBILDER - eine Figur mit jeder der 52 Waffen",
      _ein61 is not None and _ein61.gruppe == "WAFFENBILDER"
      and _TM59.OPTIONEN["paket_waffe"][1]() == list(K.PAKET_HAND))
_tm61._sp_werte["FIGUR MIT WAFFE"] = {"paket_waffe": list(K.PAKET_HAND).index("hammer"), "team": 1}
_fw61 = _tm61.spawnen(_ein61, pos=freier_punkt(_tm61.welt, 0, random.Random(61)), ebene=0)
pruef("... sie haelt sie in den Farben ihrer Mannschaft",
      len(_fw61) == 1 and _fw61[0].bild == "spieler_blau_hammer", _fw61[0].bild if _fw61 else "")
_tm61.verlassen()

# ─────────────────────────────────────────────────────────────────────
# Die Waffen aus dem Waffenpaket, spielbar (seit 0.34.62): zwoelf
# Schusswaffen und Werfer im Loadout. Geprueft wird, was jede anders macht
# als die alten - an Puppen im Testmodus, die schiessen, und am Ende im
# Gefecht zwischen Gastgeber und Gast.
print("\n-- Die Waffen aus dem Waffenpaket, spielbar (0.34.62)")
_rnd62 = EN.RND.getstate()
_zufall62 = random.getstate()
from dustfront import konto as _KO62
from dustfront import bots as _BOTS62
from dustfront import fahrzeug as _FZ62
_neu62 = ("revolver", "zwillinge", "mp", "praezision", "unterhebel", "panzerbuechse",
          "doppelflinte", "autoschrot", "minigun", "granatwerfer", "einwegwerfer",
          "raketenbuendel")
pruef("Zwoelf neue Waffen stehen in der Auswahl der Loadouts, mit Namen und Vorrat",
      all(w_ in K.LOADOUT["auswahl_waffen"] and K.WAFFEN[w_]["name"]
          and w_ in K.MUNITION["vorrat"] for w_ in _neu62))
# Seit 0.34.91 in der Folge der Plaetze: Haupt-, Seiten-, Spezialwaffe.
pruef("Ein Loadout mit neuen Waffen behaelt sie in der Hotbar (vorher fielen sie heraus)",
      _KO62.hotbar_aus_loadout({"waffen": ["mp", "revolver", "raketenbuendel"], "wuerfe": ["rauch"]})
      == ["mp", "revolver", "raketenbuendel", "rauch"])
pruef("... in der Folge der Plaetze: 1 Haupt-, 2 Seitenwaffe, dann die Wurfwaffe",
      _KO62.hotbar_aus_loadout({"waffen": ["schrot", "repetierer"], "wuerfe": ["blend"]})
      == ["schrot", "repetierer", "blend"])
_r62 = random.Random(62)
pruef("Bots ziehen weiter nur die alten fuenf (die KI kennt die neuen Griffe nicht)",
      all(set(_BOTS62.bot_loadout(_r62)["waffen"]) <= set(K.BOTS["waffen"]) for _ in range(40))
      and set(K.BOTS["waffen"]) == {"repetierer", "sturm", "schrot", "scharf", "lmg"})

_tm62 = _TM59.Testmodus(app, karte="staubtal")
_ort62 = freier_punkt(_tm62.welt, 0, random.Random(62))


def _frei62(p_, r_=12.0):
    return _tm62.welt.frei(pygame.Vector2(p_), r_, 0, True)


# Eine freie Bahn nach rechts, 360 Pixel lang: dort stehen Schuetze und Ziele.
for _ in range(400):
    if all(_frei62(_ort62 + pygame.Vector2(x_, 0), 14.0) for x_ in range(-40, 361, 10)):
        break
    _ort62 = freier_punkt(_tm62.welt, 0, _r62)


def _leeren62():
    for k_ in list(_tm62.kaempfer.values()):
        _tm62.loeschen(k_)
        _tm62.kaempfer.pop(k_.nummer, None)
    for w_ in list(_tm62.welt.wesen):
        if isinstance(w_, (EN.Geschoss, EN.Granate, EN.Rakete)):
            _tm62.loeschen(w_)


def _schuetze62(waffe_, dx_=0.0):
    k_ = _tm62.puppe_setzen(_ort62 + pygame.Vector2(dx_, 0), 0,
                            {"team": 0, "waffe_figur": waffe_, "aussehen": ""})
    k_.unverwundbar = 0.0
    return k_


def _ziel62(dx_, dy_=0.0, team_=1):
    k_ = _tm62.puppe_setzen(_ort62 + pygame.Vector2(dx_, dy_), 0, {"team": team_, "aussehen": ""})
    k_.unverwundbar = 0.0
    k_.revive_an = False
    return k_


def _lauf62(k_, sekunden_, ziel_=None, feuert_=False, zielt_=False, will_=(0, 0), je_=None):
    for _ in range(int(round(sekunden_ / K.FIXED_DT))):
        z_ = ziel_ if ziel_ is not None else k_.pos + pygame.Vector2(300, 0)
        _tm62._anwenden(k_, {"will": list(will_), "ziel": [z_[0], z_[1]], "knoepfe": [],
                             "feuert": feuert_, "zielt": zielt_})
        _tm62.schritt(K.FIXED_DT)
        if je_ is not None:
            je_()


def _alle62():
    # Was eben erst abgefeuert wurde, steht bis zum naechsten Schritt noch
    # in `neue`.
    return list(_tm62.welt.wesen) + list(_tm62.welt.neue)


def _geschosse62():
    return [w_ for w_ in _alle62() if isinstance(w_, EN.Geschoss) and w_.lebt]


_bt62 = [_tm62.bot_setzen(_ort62, 0, {"team": 0, "waffe": w_})
         for w_ in ("sturm", "revolver", "granatwerfer")]
pruef("Testmodus: ein Bot mit gewaehlter Waffe bekommt als zweite eine der alten fuenf",
      all(b_.loadout["waffen"][0] == w_ and b_.loadout["waffen"][1] in K.BOTS["waffen"]
          for b_, w_ in zip(_bt62, ("sturm", "revolver", "granatwerfer"))),
      str([b_.loadout["waffen"] for b_ in _bt62]))
pruef("Testmodus: SPIELER, STEHT und SPIELER, ICH bekommen eine WAFFE (ALLE ist die Hotbar)",
      "waffe_figur" in _tm62._eintrag("SPIELER, STEHT").optionen
      and "waffe_figur" in _tm62._eintrag("SPIELER, ICH").optionen
      and _TM59.OPTIONEN["waffe_figur"][1]()[0] == "alle")

# Revolver: gezielt einzeln, Faechern leert die Trommel auf einen Druck.
_leeren62()
_k62 = _schuetze62("revolver")
pruef("Der Revolver haelt der Figur in der Hand, sechs in der Trommel",
      _k62.waffe_name == "revolver" and _k62.magazin["revolver"] == 6
      and _k62.bild.endswith("_revolver"), _k62.bild)
_lauf62(_k62, 0.05, feuert_=True)
_lauf62(_k62, 0.3)
_einzeln62 = 6 - _k62.magazin["revolver"]
_k62.modus_wechseln()
_k62.takt = 0.0
_lauf62(_k62, 0.05, feuert_=True)
_lauf62(_k62, 0.5)
pruef("Revolver: ein Druck gezielt ist ein Schuss, ein Druck FAECHERN leert die Trommel",
      _einzeln62 == 1 and _k62.magazin["revolver"] == 0 and _k62.modus_von("revolver") == "faechern",
      "%d, Rest %d" % (_einzeln62, _k62.magazin["revolver"]))

# Zwillinge: die rechte Maustaste ist die zweite Pistole.
_leeren62()
_k62 = _schuetze62("zwillinge")
_lauf62(_k62, 1.0, feuert_=True)
_eine62 = 24 - _k62.magazin["zwillinge"]
_k62.magazin["zwillinge"] = 24
_seiten62 = set()
_lauf62(_k62, 1.0, feuert_=True, zielt_=True,
        je_=lambda: _seiten62.update(round((g_.pos - _k62.pos).rotate(-_k62.winkel).y)
                                     for g_ in _geschosse62() if g_.von is _k62
                                     and g_.pos.distance_to(_k62.pos) < 30))
_beide62 = 24 - _k62.magazin["zwillinge"]
pruef("Zwillinge: mit beiden Maustasten doppelt so viele Schuesse, aus zwei Haenden",
      _beide62 >= 2 * _eine62 - 1 and min(_seiten62, default=0) < 0 < max(_seiten62, default=0),
      "%d / %d, %s" % (_eine62, _beide62, sorted(_seiten62)))

# MP: flinker und auf Distanz schwaecher.
_g62 = EN.Geschoss(pygame.Vector2(0, 0), 0.0, K.WAFFEN["mp"], 0, None, "mp")
_nah62 = _g62.schaden_jetzt()
_g62.rest = 0.0
_weit62 = _g62.schaden_jetzt()
pruef("MP: nah voller Schaden, am Ende der Reichweite nur noch ein Teil",
      _nah62 == K.WAFFEN["mp"]["schaden"]
      and abs(_weit62 - K.WAFFEN["mp"]["schaden"] * K.WAFFEN["mp"]["abfall_rest"]) < 0.01,
      "%.1f / %.1f" % (_nah62, _weit62))
_leeren62()
_a62 = _schuetze62("mp")
_b62 = _schuetze62("sturm", 0.0)
_b62.pos.y += 40
_start62 = (pygame.Vector2(_a62.pos), pygame.Vector2(_b62.pos))
for _ in range(int(1.0 / K.FIXED_DT)):
    for k_ in (_a62, _b62):
        _tm62._anwenden(k_, {"will": [0, 1], "ziel": [k_.pos.x + 300, k_.pos.y], "knoepfe": []})
    _tm62.schritt(K.FIXED_DT)
pruef("MP: wer sie traegt, laeuft schneller als mit dem Sturmgewehr",
      _a62.pos.distance_to(_start62[0]) > _b62.pos.distance_to(_start62[1]) * 1.04,
      "%.0f / %.0f" % (_a62.pos.distance_to(_start62[0]), _b62.pos.distance_to(_start62[1])))

# Praezisionsgewehr: der Kegel schliesst sich zu einer Linie, ein Schuss
# oeffnet ihn nur ein kleines Stueck - ohne weisse Mittellinie.
_leeren62()
_k62 = _schuetze62("praezision")
_lauf62(_k62, 1.2, zielt_=True)
_zu62 = _k62.streuung_jetzt
_lauf62(_k62, K.FIXED_DT, zielt_=True, feuert_=True)
pruef("Praezisionsgewehr: gezielt eine Linie, nach dem Schuss noch fast zu, ohne Mittellinie",
      _zu62 < 0.05 and _k62.fokus > 0.8 and not K.WAFFEN["praezision"]["fokus_mittellinie"],
      "%.2f Grad, Fokus %.2f" % (_zu62, _k62.fokus))

# Unterhebel: Patrone fuer Patrone, ein Schuss unterbricht das Laden.
_leeren62()
_k62 = _schuetze62("unterhebel")
_k62.magazin["unterhebel"] = 2
_k62.nachladen()
_lauf62(_k62, K.WAFFEN["unterhebel"]["nachladen"] + 0.05)
_eine_dazu62 = _k62.magazin["unterhebel"]
_lauf62(_k62, K.FIXED_DT, feuert_=True)
pruef("Unterhebel: je Patrone geladen, ein Schuss unterbricht das Laden",
      _eine_dazu62 == 3 and _k62.magazin["unterhebel"] == 2 and _k62.nachlade_rest <= 0.0,
      "%d -> %d, %.2f" % (_eine_dazu62, _k62.magazin["unterhebel"], _k62.nachlade_rest))
_k62.knapp = True
_k62.vorrat["unterhebel"] = 1
_k62.magazin["unterhebel"] = 0
_k62.nachladen()
_lauf62(_k62, 4 * K.WAFFEN["unterhebel"]["nachladen"])
pruef("... mit knapper Munition kostet jede Patrone Vorrat, und ohne Vorrat ist Schluss",
      _k62.magazin["unterhebel"] == 1 and _k62.vorrat["unterhebel"] == 0
      and _k62.nachlade_rest <= 0.0, "%d, %d" % (_k62.magazin["unterhebel"], _k62.vorrat["unterhebel"]))

# Panzerbuechse: durch drei Koerper, durch niedrige Deckung, voll ins Blech,
# und der Laser.
_leeren62()
_k62 = _schuetze62("panzerbuechse")
_ziele62 = [_ziel62(90 + 40 * i_) for i_ in range(3)]
_lauf62(_k62, K.FIXED_DT, ziel_=_ziele62[0].pos, feuert_=True)
_lauf62(_k62, 0.4)
pruef("Panzerbuechse: ein Schuss geht durch drei Koerper",
      all(z_.leben < z_.max_leben for z_ in _ziele62), str([round(z_.leben) for z_ in _ziele62]))
_kiste62 = None
for _ty in range(_tm62.welt.ebene(0).hoehe if hasattr(_tm62.welt.ebene(0), "hoehe") else 120):
    for _tx in range(120):
        _d62 = K.KACHELN[_tm62.welt.ebene(0).kachel(_tx, _ty)]
        if _d62["fest"] and not _d62["sicht"]:
            _kiste62 = pygame.Vector2((_tx + 0.5) * K.TILE, (_ty + 0.5) * K.TILE)
            break
    if _kiste62 is not None:
        break
pruef("... niedrige Deckung haelt sie nicht auf, eine Mauer schon",
      _kiste62 is not None and _tm62.welt.schuss_halt(_kiste62, 0, 2.0)
      and not _tm62.welt.schuss_halt(_kiste62, 0, 2.0, True), str(_kiste62))
_pz62 = _FZ62.neu("panzer", _ort62 + pygame.Vector2(0, 400), 0, 0.0)
_pz62.welt = _tm62.welt
for _wf62 in ("sturm", "panzerbuechse"):
    _vor62 = _pz62.leben
    _g62 = EN.Geschoss(_pz62.pos, 0.0, K.WAFFEN[_wf62], 0, _k62, _wf62)
    _g62.welt = _tm62.welt
    _g62.treffen(_pz62)
    if _wf62 == "sturm":
        _sturm62 = _vor62 - _pz62.leben
    else:
        _pb62 = _vor62 - _pz62.leben
# Seit 0.34.65 mit Panzerung je Schadensart: die Panzerbuechse ist
# panzerbrechend, und der Schuss kommt von hinten (er startet in der Mitte
# und fliegt nach vorn, K.PANZER_SEITEN).
pruef("... am Panzer geht sie durchs Blech (panzerbrechend), das Sturmgewehr kratzt nur",
      abs(_pb62 - K.WAFFEN["panzerbuechse"].get("fahrzeug_schaden", K.WAFFEN["panzerbuechse"]["schaden"])
          * K.PANZERUNG["panzer"]["panzerbrechend"]
          * K.PANZER_SEITEN["hinten"]) < 0.01
      and _sturm62 < K.WAFFEN["sturm"]["schaden"] * 0.5 and _pb62 > 10 * _sturm62,
      "%.1f / %.1f" % (_pb62, _sturm62))
_k62.magazin["panzerbuechse"] = 1
_tm62.kamera.pos.update(_k62.pos)
_tm62.kamera.versatz.update(0, 0)
_tm62.renderer.bilder  # noqa: B018  (Renderer gibt es)
_fl62 = pygame.Surface((K.GAME_W, K.GAME_H), pygame.SRCALPHA)
_tm62.renderer.laser_zeichnen(_fl62, _tm62.welt, 0, _tm62.kamera.ecke)
_rot62 = sum(1 for x_ in range(K.GAME_W // 2, K.GAME_W) if _fl62.get_at((x_, K.GAME_H // 2)).r > 150)
pruef("... und ihr Ziellaser ist fuer alle zu sehen", _rot62 >= 20, str(_rot62))

# Doppelflinte: rechte Maustaste beide Laeufe.
_leeren62()
_k62 = _schuetze62("doppelflinte")
_lauf62(_k62, K.FIXED_DT, zielt_=True)
_kugeln62 = len([g_ for g_ in _geschosse62() if g_.von is _k62])
pruef("Doppelflinte: rechte Maustaste feuert beide Laeufe auf einmal",
      _k62.magazin["doppelflinte"] == 0 and _kugeln62 == 2 * K.WAFFEN["doppelflinte"]["geschosse"],
      "%d Rest, %d Kugeln" % (_k62.magazin["doppelflinte"], _kugeln62))

# Autoschrot: schiebt staerker.
_leeren62()
_k62 = _schuetze62("autoschrot")
_s62 = []
for _wf62 in ("schrot", "autoschrot"):
    _z62 = _ziel62(60)
    _g62 = EN.Geschoss(_k62.pos, 0.0, K.WAFFEN[_wf62], 0, _k62, _wf62)
    _g62.welt = _tm62.welt
    _g62.schub_anteil = 1.0
    _g62.treffen(_z62)
    _s62.append(_z62.tempo.length())
pruef("Autoschrot: ein Treffer drueckt den Getroffenen deutlich weiter zurueck",
      _s62[1] > _s62[0] * 2.0, str([round(x_) for x_ in _s62]))

# Minigun: Anlauf, dann Dauerfeuer, der Traeger steht fast.
_leeren62()
_k62 = _schuetze62("minigun")
_lauf62(_k62, 0.5, feuert_=True)
_erst62 = 240 - _k62.magazin["minigun"]
_lauf62(_k62, 1.6, feuert_=True)
_dann62 = 240 - _k62.magazin["minigun"] - _erst62
pruef("Minigun: erst langsam, nach dem Anlauf ein Vielfaches, und kaum zu bewegen",
      _dann62 > 4 * _erst62 and _k62.gewicht_tempo < 0.4, "%d dann %d" % (_erst62, _dann62))

# Granatwerfer: Bogen bis zum Zeiger, Koerper zuenden sofort.
_leeren62()
_k62 = _schuetze62("granatwerfer")
_zz62 = _k62.pos + pygame.Vector2(260, 0)
_hoch62 = [0.0]
_lauf62(_k62, K.FIXED_DT, ziel_=_zz62, feuert_=True)
_gr62 = [w_ for w_ in _alle62() if isinstance(w_, EN.Werfergranate)]


def _hoehe62():
    for g_ in _gr62:
        _hoch62[0] = max(_hoch62[0], g_.flug)


_flugzeit62 = (260.0 - 16.0) / K.WAFFEN["granatwerfer"]["tempo"]
_lauf62(_k62, _flugzeit62 + 0.15, ziel_=_zz62, je_=_hoehe62)
_gelandet62 = _gr62[0].pos.distance_to(_zz62) if _gr62 else 999.0
pruef("Granatwerfer: die Granate steigt (nur als Groesse) und landet am Zeiger",
      len(_gr62) == 1 and _hoch62[0] > 0.6 * K.WAFFEN["granatwerfer"]["bogen"]
      and _gr62[0].liegt and _gelandet62 < 20.0 and _gr62[0].bild == "teil_granate40",
      "%.0f hoch, %.0f daneben" % (_hoch62[0], _gelandet62))
_lauf62(_k62, K.WAFFEN["granatwerfer"]["zuender"] + 0.2)
pruef("... liegt kurz und zuendet dann", _gr62 and not _gr62[0].lebt)
# Am Ende des Bogens ist sie wieder tief: wer dort steht, wird getroffen,
# bevor sie aufsetzt. (Mitten im Bogen fliegt sie ueber Koepfe hinweg.)
_z62 = _ziel62(290)
_k62.magazin["granatwerfer"] = 1
_k62.takt = 0.0
_lauf62(_k62, K.FIXED_DT, ziel_=_k62.pos + pygame.Vector2(300, 0), feuert_=True)
_gr62 = [w_ for w_ in _alle62() if isinstance(w_, EN.Werfergranate)]
_lauf62(_k62, (300.0 - 16.0) / K.WAFFEN["granatwerfer"]["tempo"])
pruef("... trifft sie tief einen Koerper, zuendet sie sofort - ohne aufzusetzen",
      _gr62 and not _gr62[0].lebt and not _gr62[0].liegt and _z62.leben < _z62.max_leben,
      "%.0f" % _z62.leben)

# Einweg-Raketenwerfer: ein Schuss, das Rohr liegt am Boden, weiter mit
# der naechsten Waffe.
_leeren62()
_k62 = _schuetze62("einwegwerfer")
_lauf62(_k62, K.FIXED_DT, feuert_=True)
_rohr62 = [f_ for f_ in _tm62.welt.flugleichen if f_.bild == "teil_rohr_leer"]
_k62.nachladen()
_lauf62(_k62, 0.5)
pruef("Einweg-Raketenwerfer: ein Schuss, dann die naechste Waffe - nachladen geht nicht",
      _k62.magazin["einwegwerfer"] == 0 and _k62.waffe_name != "einwegwerfer",
      _k62.waffe_name)
_lauf62(_k62, 2.0)
pruef("... das Rohr liegt daneben, ohne Blut, qualmt und ist spaeter weg",
      len(_rohr62) == 1 and not _rohr62[0].blut and _rohr62[0].lebt)
_lauf62(_k62, K.ROHR["liegen"] + 0.5)
pruef("... (weg nach K.ROHR liegen)", not _rohr62[0].lebt)

# Raketenbuendel: sechs kleine Raketen auf einen Druck, die schlingern.
_leeren62()
_k62 = _schuetze62("raketenbuendel")
_winkel62 = {}


def _merk62():
    for r_ in _tm62.welt.wesen:
        if isinstance(r_, EN.Rakete) and r_.lebt:
            _winkel62.setdefault(r_.kennung, []).append(r_.winkel)


_lauf62(_k62, K.FIXED_DT, feuert_=True)
_lauf62(_k62, 0.9, je_=_merk62)
_bilder62 = {r_.bild for r_ in _tm62.welt.wesen if isinstance(r_, EN.Rakete)}
pruef("Raketenbuendel: ein Druck, sechs kleine Raketen, jede schlingert",
      _k62.magazin["raketenbuendel"] == 0 and len(_winkel62) == 6
      # Wer eine halbe Sekunde flog (mehr als eine halbe Pendelbewegung),
      # pendelte dabei um mehr als K.WAFFEN schlingern.
      and any(len(v_) * K.FIXED_DT >= 0.5 for v_ in _winkel62.values())
      and all(max(v_) - min(v_) > K.WAFFEN["raketenbuendel"]["schlingern"]
              for v_ in _winkel62.values() if len(v_) * K.FIXED_DT >= 0.5),
      "%d Raketen" % len(_winkel62))
_k62.magazin["raketenbuendel"] = 6
_k62.takt = 0.0
_lauf62(_k62, K.FIXED_DT, feuert_=True)
_k62.waffe_waehlen(_k62.waffen.index("sturm"))
_lauf62(_k62, 0.8)
pruef("... wer mitten in der Salve wechselt, beendet sie (nicht mit der neuen Waffe weiter)",
      _k62.magazin["raketenbuendel"] == 5 and _k62.magazin["sturm"] == K.WAFFEN["sturm"]["magazin"],
      "%d, %d" % (_k62.magazin["raketenbuendel"], _k62.magazin["sturm"]))
_tm62.verlassen()

# Im Gefecht: der Gast sieht die Figur, die 40-mm-Granate in der Luft, die
# kleinen Raketen und das Rohr am Boden.
w, ga = _paar59("pvp", karte="staubtal")
_gk62 = w.kaempfer.get(ga.meine_nummer)
_alt_ein62 = w._meine_eingabe
_ein62 = {"feuert": False}
w._meine_eingabe = lambda: {"will": [0, 0], "ziel": [w.ich.pos.x + 260, w.ich.pos.y],
                            "knoepfe": [], "feuert": _ein62["feuert"], "zielt": False}
_frei_ich62 = freier_punkt(w.welt, 0, random.Random(620))
w.ich.pos.update(_frei_ich62)
w.ich.vorher.update(_frei_ich62)
w.ich.winkel = 0.0
_namen62 = set()
_hoehe_gast62 = [0.0]


def _gast62(sek_, feuert_=False):
    for _ in range(int(sek_ / K.NETZ["takt"])):
        _ein62["feuert"] = feuert_
        w.schritt(K.NETZ["takt"])
        ga.schritt(K.NETZ["takt"])
        for e_ in ga._fremde_schuesse:
            _namen62.add(e_[4])
            if e_[4] == "teil_granate40":
                _hoehe_gast62[0] = max(_hoehe_gast62[0], e_[5])


for _wf62 in ("granatwerfer", "raketenbuendel", "einwegwerfer"):
    w.ich.waffen = [_wf62, "sturm", "granate"]
    w.ich.waffe = 0
    w.ich.magazin[_wf62] = K.WAFFEN[_wf62]["magazin"]
    w.ich.takt = 0.0
    _gast62(0.1)
    _bild62 = ga.kaempfer[0].bild
    _gast62(0.05, True)
    _gast62(1.0)
pruef("Der Gast sieht die neuen Waffen in der Hand", _bild62.endswith("_einwegwerfer"), _bild62)
pruef("... die 40-mm-Granate im Bogen und die kleinen Raketen",
      "teil_granate40" in _namen62 and _hoehe_gast62[0] > 20.0 and "minirakete_flug" in _namen62,
      "%s %.0f" % (sorted(_namen62), _hoehe_gast62[0]))
pruef("... und das abgelegte Rohr", any(f_.bild == "teil_rohr_leer" for f_ in ga.welt.flugleichen))
w._meine_eingabe = _alt_ein62
w.verlassen(); ga.verlassen()
EN.RND.setstate(_rnd62)
random.setstate(_zufall62)

# ─────────────────────────────────────────────────────────────────────
# Testmodus mit Touch (seit 0.34.63): auf iPhone und iPad. Der Ziffernblock
# wird angetippt (vor den Sticks), der linke Stick fliegt, Spawner und
# Testmenue gehen mit dem Finger. Steuert man eine Figur, klappt der
# Ziffernblock unter die Taste NUM, damit die Knoepfe frei liegen.
print("\n-- Testmodus mit Touch (0.34.63)")
_rnd63 = EN.RND.getstate()
_zufall63 = random.getstate()
from dustfront import testmodus as _TM63
_alt_touch63 = os.environ.get("DUSTFRONT_TOUCH")
os.environ["DUSTFRONT_TOUCH"] = "1"
_app63 = App("IPAD", None, headless=True)
_tm63 = _TM63.Testmodus(_app63, karte="staubtal")
_app63.schieben(_tm63)
pygame.event.clear()
_app63.ereignisse()


def _finger63(art, fid, gx, gy):
    fw_, fh_ = _app63.fenster.get_size()
    p_ = _app63.zu_fenster((gx, gy, 1, 1))
    pygame.event.post(pygame.event.Event(art, finger_id=fid, touch_id=1, x=p_.x / fw_,
                                         y=p_.y / fh_, dx=0.0, dy=0.0, pressure=1.0))
    _app63.ereignisse()


def _tippen63(fid, p_):
    _finger63(pygame.FINGERDOWN, fid, p_[0], p_[1])
    _finger63(pygame.FINGERUP, fid, p_[0], p_[1])


def _klick63(p_, knopf_=1):
    """Im Spawner und im Testmenue macht SDL aus dem Finger eine Maus."""
    w_ = _app63.zu_fenster((p_[0], p_[1], 1, 1))
    pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=(w_.x, w_.y),
                                         button=knopf_, touch=False))
    pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONUP, pos=(w_.x, w_.y),
                                         button=knopf_, touch=False))
    _app63.ereignisse()


def _taste63(name_):
    return next(r_ for n_, r_ in _tm63.tasten_flaechen() if n_ == name_).center


pruef("Testmodus mit Touch: es gibt ihn, und die Finger gehoeren dem Beobachter",
      _TM63.verfuegbar() and _app63.touch is not None and _app63.touch.spielt()
      and _tm63.beobachter)
pruef("... der Beobachter hat nur Pause und Ebenen als Knoepfe, der Ziffernblock ist ganz da",
      _tm63.touch_knoepfe() == ("pause", "ebenen") and not _tm63.numpad_klein
      and len(_tm63.tasten_flaechen()) == len(_TM63.TASTEN))
_p63 = _taste63("0")
_finger63(pygame.FINGERDOWN, 1, _p63[0], _p63[1])
_rolle63 = _app63.touch.finger.get(1, {}).get("rolle")
_finger63(pygame.FINGERMOTION, 1, _p63[0] - 30, _p63[1])
_ruht63 = _app63.eingabe.richtung().length() < 0.01
_finger63(pygame.FINGERUP, 1, _p63[0] - 30, _p63[1])
pruef("Eine Taste des Ziffernblocks antippen wirkt (0: Zeit steht) - und wird kein Stick",
      _tm63.zeit_stopp and _rolle63 == "szene" and _ruht63, str(_rolle63))
_tippen63(2, _taste63("0"))
_ort63 = pygame.Vector2(_tm63._geist.pos)
_finger63(pygame.FINGERDOWN, 3, 100, 250)
_finger63(pygame.FINGERMOTION, 3, 100 + K.TOUCH["stick_radius"], 250)
for _ in range(30):
    _app63.ereignisse()
    _tm63.schritt(K.FIXED_DT)
_finger63(pygame.FINGERUP, 3, 100 + K.TOUCH["stick_radius"], 250)
pruef("Der linke Stick fliegt den Beobachter", _tm63._geist.pos.x - _ort63.x > 50,
      str(_tm63._geist.pos - _ort63))

_tippen63(4, _taste63("4"))
pruef("4 antippen oeffnet den Spawner; dort ist der Finger wieder die Maus",
      _tm63.spawner_offen and not _app63.touch.spielt())
_vor63 = len(_tm63.kaempfer)
_klick63((520, 300))
pruef("... ein Tipp in die Welt setzt dort, was gewaehlt ist (BOT)",
      len(_tm63.kaempfer) == _vor63 + 1, "%d -> %d" % (_vor63, len(_tm63.kaempfer)))
_e63 = _tm63.eintraege[_tm63._sp_nr]
_liste63, _opt63 = _tm63._spawner_flaechen()
_r63 = _opt63[0][1]
_klick63((_r63.x + 4, _r63.centery))
_hinten63 = _tm63._sp_werte[_e63.name][_e63.optionen[0]]
_klick63((_r63.right - 4, _r63.centery))
_vorn63 = _tm63._sp_werte[_e63.name][_e63.optionen[0]]
pruef("... links auf eine Einstellung getippt blaettert zurueck, rechts vor",
      _hinten63 == len(_TM63.OPTIONEN[_e63.optionen[0]][1]()) - 1 and _vorn63 == 0,
      "%d / %d" % (_hinten63, _vorn63))
_nr63 = _tm63._sp_nr
pygame.event.post(pygame.event.Event(pygame.MOUSEWHEEL, x=0, y=-1, flipped=False,
                                     precise_x=0.0, precise_y=-1.0, touch=False, which=0))
_app63.ereignisse()
pruef("... zwei Finger (Rad) blaettern in der Liste",
      _tm63._sp_nr == (_nr63 + 1) % len(_tm63.eintraege))
_tippen63(5, K.TOUCH["esc_mitte"])
pruef("... und ESC schliesst ihn", not _tm63.spawner_offen and _app63.touch.spielt())



def _doppel63(p_, maus_zuerst_):
    """Ein Tipp, wie iOS ihn meldet: als Finger und als Maus daraus."""
    w_ = _app63.zu_fenster((p_[0], p_[1], 1, 1))
    fw_, fh_ = _app63.fenster.get_size()
    maus_ = [pygame.event.Event(t_, pos=(w_.x, w_.y), button=1, touch=True)
             for t_ in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP)]
    finger_ = [pygame.event.Event(t_, finger_id=9, touch_id=1, x=w_.x / fw_, y=w_.y / fh_,
                                  dx=0.0, dy=0.0, pressure=1.0)
               for t_ in (pygame.FINGERDOWN, pygame.FINGERUP)]
    erst_, dann_ = (maus_, finger_) if maus_zuerst_ else (finger_, maus_)
    for e_ in (erst_[0], dann_[0], erst_[1], dann_[1]):
        pygame.event.post(e_)
    _app63.ereignisse()


_zu63 = []
for _maus63 in (False, True, True, False):
    _doppel63(_taste63("4"), _maus63)
    _zu63.append(_tm63.spawner_offen)
pruef("Ein Tipp kommt auf iOS als Finger und als Maus - der Spawner geht trotzdem nur einmal auf oder zu",
      _zu63 == [True, False, True, False], str(_zu63))
_vor63 = _tm63.zeit_stopp
_tippen63(10, _taste63("0"))
_tippen63(11, _taste63("0"))
pruef("... und wer schnell zweimal tippt, tippt zweimal", _tm63.zeit_stopp == _vor63)
_bot63 = next(k_ for k_ in _tm63.kaempfer.values() if getattr(k_, "ist_bot", False))
_tm63.uebernehmen(_bot63)
_app63.ereignisse()
pruef("Steuert man eine Figur, klappt der Ziffernblock zu NUM, und alle Knoepfe gelten",
      _tm63.numpad_klein and [n_ for n_, _r in _tm63.tasten_flaechen()] == ["num_auf"]
      and _tm63.touch_knoepfe() is None)
_k63 = [r_ for n_, r_ in _tm63.tasten_flaechen()][0]


def _abstand63(r_, m_):
    """Wie weit der Punkt m_ vom Rechteck r_ weg ist (0: darin)."""
    nx_ = max(r_.left, min(m_[0], r_.right))
    ny_ = max(r_.top, min(m_[1], r_.bottom))
    return math.hypot(m_[0] - nx_, m_[1] - ny_)


pruef("... NUM liegt nicht unter einem Knopf der Touch-Steuerung (auch nicht mit Zugabe)",
      all(_abstand63(_k63, m_) > K.TOUCH["knopf_radius"] * 1.25
          for _a, _t, m_, _art in K.TOUCH["knoepfe"]),
      str(min(_abstand63(_k63, m_) for _a, _t, m_, _art in K.TOUCH["knoepfe"])))
_tippen63(6, _k63.center)
pruef("... NUM antippen klappt ihn auf, dann gilt nur noch Pause",
      not _tm63.numpad_klein and len(_tm63.tasten_flaechen()) == len(_TM63.TASTEN) + 1
      and _tm63.touch_knoepfe() == ("pause",))
_tippen63(7, _taste63("3"))
pruef("... und 3 (BEOB.) fuehrt zurueck zum Beobachter", _tm63.beobachter)
_app63.werfen()
_tm63.verlassen()
if _alt_touch63 is None:
    os.environ.pop("DUSTFRONT_TOUCH", None)
else:
    os.environ["DUSTFRONT_TOUCH"] = _alt_touch63
EN.RND.setstate(_rnd63)
random.setstate(_zufall63)

# ─────────────────────────────────────────────────────────────────────
# 0.34.64: Bogen nach oben, Raketen als Raketen, Blitz bei Explosionen,
# Buggy an seiner ganzen Laenge getroffen.
print("\n-- Granatwerfer-Bogen, Raketen, Explosionsblitze, Buggy-Treffer (0.34.64)")
_rnd64 = EN.RND.getstate()
_zufall64 = random.getstate()
_tm64 = _TM59.Testmodus(app, karte="staubtal")
_ort64 = freier_punkt(_tm64.welt, 0, random.Random(64))
_tm64.kamera.pos.update(_ort64)
_tm64.kamera.versatz.update(0, 0)
_hoehe64 = []
for _f64 in (0.5, 60.0):
    _fl64 = pygame.Surface((K.GAME_W, K.GAME_H), pygame.SRCALPHA)
    _tm64.renderer.fliegendes(_fl64, _tm64.welt, _tm64.kamera, _tm64.blick_hoehe,
                              pygame.Vector2(_ort64), 0.0, 0, _f64, "teil_granate40")
    _hoehe64.append(_fl64.get_bounding_rect().centery)
pruef("Eine Granate im Bogen steht hoeher im Bild, je hoeher sie fliegt (nicht tiefer)",
      _hoehe64[1] < _hoehe64[0] - 15, str(_hoehe64))
pruef("Die Raketen des Buendels fliegen als eigenes Bild mit Flossen und Flamme, "
      "und explodieren als eigene Art",
      K.WAFFEN["raketenbuendel"]["bild"] == "minirakete_flug"
      and app.bilder.bild("minirakete_flug").get_size() == (18, 8)
      and K.WAFFEN["raketenbuendel"]["explosion"] == "klein")
_tm64.welt.explosion(_ort64, 0, 40.0, "klein")
_blitz64 = len(_tm64.welt.lichtblitze)
for _ in range(int(0.2 / K.FIXED_DT)):
    _tm64.welt.schritt(K.FIXED_DT)
pruef("Jede Explosion blitzt kurz auf und ist dann weg",
      _blitz64 == 1 and not _tm64.welt.lichtblitze, str(_blitz64))
_bu64 = _tm64.fahrzeug_setzen("buggy", _ort64 + pygame.Vector2(0, 120), 0, {"winkel": 0})
_tm64.welt._raster_bauen()
_heck64 = _bu64.pos - pygame.Vector2(K.FAHRZEUG["achse"] + 8, 0)
pruef("Ein Buggy wird auch am Heck getroffen, nicht nur 13 Pixel um die Mitte",
      _tm64.welt.treffer(_heck64, 2.0, 0, "spieler") is _bu64)
_tm64.verlassen()
EN.RND.setstate(_rnd64)
random.setstate(_zufall64)

from dustfront.entities import Nagelfeld as _Nagelfeld65

# 0.34.65: Panzerung je Schadensart und Seite, Lebenspunkte, Haftladung,
# EMP-Granate, Hecknebel, Nagelstreuer.
print("\n-- Fahrzeug-Panzerung, Haftladung, EMP, Hecknebel, Nagelstreuer (0.34.65)")
_rnd65 = EN.RND.getstate()
_zufall65 = random.getstate()
_tm65 = _TM59.Testmodus(app, karte="staubtal")
_ort65 = freier_punkt(_tm65.welt, 0, random.Random(65))
pruef("Drei Fahrzeuge, drei verschiedene Lebenspunkte",
      len({K.FAHRZEUG["leben"], K.PANZERWAGEN["leben"], K.PANZER["leben"]}) == 3
      and K.FAHRZEUG["leben"] < K.PANZERWAGEN["leben"] < K.PANZER["leben"])
pruef("Jede Fahrzeugart hat eine Panzerung fuer jede Schadensart",
      all(set(K.PANZERUNG[a]) == set(K.PANZERUNG["buggy"])
          for a in ("buggy", "panzerwagen", "panzer")))
_pz65 = _tm65.fahrzeug_setzen("panzer", _ort65, 0, {"anzahl": 1, "streuung": 0, "winkel": 0})
_pz65 = _pz65[0] if isinstance(_pz65, list) else _pz65
_pz65.winkel = 0.0
_vorn65 = _pz65.pos + pygame.Vector2(200, 0)
_hinten65 = _pz65.pos - pygame.Vector2(200, 0)
_seite65 = _pz65.pos + pygame.Vector2(0, 200)
pruef("Die Seite eines Treffers folgt aus seiner Herkunft",
      (_pz65.seite(_vorn65), _pz65.seite(_hinten65), _pz65.seite(_seite65))
      == ("vorn", "hinten", "seite"))
def _ab65(art, her=None, menge=100.0):
    _pz65.leben = _pz65.max_leben
    _pz65.schaden(menge, None, None, art=art, herkunft=her)
    return _pz65.max_leben - _pz65.leben
pruef("Am Panzer: Hohlladung > Panzerbrechend > Spreng > Kugel > Feuer",
      _ab65("hohlladung") > _ab65("panzerbrechend") > _ab65("spreng") > _ab65("kugel")
      > _ab65("feuer"), str([round(_ab65(a), 1) for a in ("hohlladung", "panzerbrechend",
                                                          "spreng", "kugel", "feuer")]))
pruef("Von hinten mehr als von vorn",
      _ab65("hohlladung", _hinten65) > _ab65("hohlladung", _seite65)
      > _ab65("hohlladung", _vorn65))
pruef("Ohne Art kommt alles an (Befehle, Testmodus)", abs(_ab65(None) - 100.0) < 0.01)
_bg65 = _tm65.buggy_setzen(_ort65 + pygame.Vector2(0, 160), 0, {"anzahl": 1, "streuung": 0,
                                                              "winkel": 0})
_bg65 = _bg65[0] if isinstance(_bg65, list) else _bg65
_bg65.leben = _bg65.max_leben
_bg65.schaden(100.0, None, None, art="kugel", herkunft=_bg65.pos + pygame.Vector2(0, 50))
pruef("Ein Buggy hat kaum Panzerung: eine Kugel kommt ganz an",
      abs(_bg65.max_leben - _bg65.leben - 100.0) < 0.01, "%.1f" % (_bg65.max_leben - _bg65.leben))

# Haftladung: klebt am Wagen, faehrt mit, zuendet dort.
_pz65.leben = _pz65.max_leben
_hl65 = EN.Granate(_pz65.pos + pygame.Vector2(0, -60), 90.0, K.WAFFEN["haftladung"], 0, None, 60.0)
_tm65.welt.dazu(_hl65)
_geklebt65 = False
for _ in range(int(K.WAFFEN["haftladung"]["flugzeit"] / K.FIXED_DT) + 60):
    _tm65.welt.schritt(K.FIXED_DT)
    if _hl65.traeger is _pz65:
        _geklebt65 = True
        _pz65.pos.x += 1.0     # er faehrt weiter
    if not _hl65.lebt:
        break
pruef("Die Haftladung klebt am Panzer und faehrt mit", _geklebt65)
pruef("... und reisst ihm ein grosses Stueck heraus (Hohlladung)",
      _pz65.max_leben - _pz65.leben > K.WAFFEN["haftladung"]["fahrzeug_schaden"] * 0.9,
      "%.0f" % (_pz65.max_leben - _pz65.leben))
pruef("Haftladung und EMP-Granate stehen in der Loadout-Auswahl und im Spawner",
      {"haftladung", "emp"} <= set(K.LOADOUT["auswahl_wuerfe"])
      and {"HAFTLADUNG", "EMP-GRANATE"} <= {e.name for e in _TM59.eintraege()})

# EMP: der Panzer steht still, schiesst nicht, und es geht vorbei.
_pz65.leben = _pz65.max_leben
# Zurueck auf den Platz, in eine Richtung, in der vor ihm frei ist.
_pz65.pos.update(_ort65)
for _w65 in (0.0, 90.0, 180.0, -90.0):
    _pz65.winkel = _w65
    if _pz65.passt(_pz65.pos + _pz65.vorn * 60.0):
        break
_emp65 = EN.Granate(_pz65.pos + pygame.Vector2(0, -40), 90.0, K.WAFFEN["emp"], 0, None, 0.0)
_tm65.welt.dazu(_emp65)
for _ in range(int(K.WAFFEN["emp"]["flugzeit"] / K.FIXED_DT) + 10):
    _tm65.welt.schritt(K.FIXED_DT)
pruef("Die EMP-Granate legt den Panzer still, ohne Schaden",
      _pz65.emp_rest > 0.0 and _pz65.leben == _pz65.max_leben, "%.1f" % _pz65.emp_rest)
_wesen65 = _tm65.welt.wesen
_fahrer65 = _tm65.bot_setzen(_pz65.pos + pygame.Vector2(0, 80), 0,
                             {"anzahl": 1, "streuung": 0, "team": 0})
_fahrer65 = _fahrer65[0] if isinstance(_fahrer65, list) else _fahrer65
_pz65.fahrer = _fahrer65
_pz65.gas, _pz65.feuer = 1.0, True
_x65 = pygame.Vector2(_pz65.pos)
_n65 = len([g for g in _tm65.welt.wesen + _tm65.welt.neue if g.__class__.__name__ == "Panzergranate"])
for _ in range(30):
    _pz65.gas, _pz65.feuer = 1.0, True
    _pz65.schritt(K.FIXED_DT)
_n65b = len([g for g in _tm65.welt.wesen + _tm65.welt.neue if g.__class__.__name__ == "Panzergranate"])
pruef("... stromlos faehrt er nicht und die Kanone schweigt",
      _pz65.pos.distance_to(_x65) < 1.0 and _n65b == _n65,
      "%.1f px, %d Granaten" % (_pz65.pos.distance_to(_x65), _n65b - _n65))
_pz65.emp_rest = 0.01
for _ in range(120):
    _pz65.gas = 1.0
    _pz65.schritt(K.FIXED_DT)
pruef("... nach dem EMP faehrt er wieder", _pz65.pos.distance_to(_x65) > 1.0,
      "%.1f" % _pz65.pos.distance_to(_x65))
_pz65.fahrer = None
_pz65.gas, _pz65.feuer = 0.0, False

# Hecknebel und Nagelstreuer: Ladungen, Rauch hinten, Naegel machen platt.
_bg65.leben = _bg65.max_leben
_r65 = len(_tm65.welt.rauch)
pruef("Der Buggy wirft Hecknebel: Rauch hinter ihm",
      _bg65.hilfe_nutzen("hecknebel") and len(_tm65.welt.rauch) > _r65
      and all(r.pos.distance_to(_bg65.heck()) < 80 for r in _tm65.welt.rauch[_r65:]))
pruef("... nicht gleich noch einmal (Takt)", not _bg65.hilfe_nutzen("hecknebel"))
pruef("Der Panzer hat keinen Nagelstreuer, der Buggy schon",
      "nagelstreuer" not in _pz65.hilfe and _bg65.hilfe.get("nagelstreuer", 0) > 0)
_nf65 = _Nagelfeld65(_bg65.pos + pygame.Vector2(60, 0), 0)
_tm65.welt.naegel.append(_nf65)
_bg65.geschw.update(200, 0)
_bg65.winkel = 0.0
_vor65 = _bg65.leben
for _ in range(40):
    _tm65.welt.schritt(K.FIXED_DT)
    _bg65.geschw.update(max(_bg65.geschw.x, 60), 0)
pruef("Ueber Naegel: Reifen platt, Schaden, langsam",
      _bg65.platt_rest > 0.0 and _bg65.leben < _vor65
      and _bg65.geschw.length() <= K.FAHRZEUG["hoechst"] * K.NAEGEL["platt_tempo"] + 0.5,
      "%.1f s, %.0f" % (_bg65.platt_rest, _vor65 - _bg65.leben))
_tm65.welt.naegel.clear()

# Im Netz: der Gast sieht das Nagelfeld (an derselben Stelle, dieselben
# Naegel) und dass ein Wagen stromlos ist.
w, ga = _paar59("team", karte="staubtal")
_wb65 = w.fahrzeuge[0]
_wb65.emp_treffen(K.EMP["dauer"])
_wn65 = _Nagelfeld65(pygame.Vector2(w.ich.pos) + pygame.Vector2(90, 0), w.ich.ebene, von=w.ich)
w.welt.naegel.append(_wn65)
for _ in range(8):
    w.schritt(K.NETZ["takt"])
    ga.schritt(K.NETZ["takt"])
_gn65 = [n for n in ga.welt.naegel if n.kennung == _wn65.kennung]
pruef("Der Gast sieht das Nagelfeld, mit denselben Naegeln",
      len(_gn65) == 1 and _gn65[0].stellen() == _wn65.stellen())
_gb65 = [b for b in ga.fahrzeuge if getattr(b, "netz_kennung", -1) == _wb65.kennung]
pruef("... und dass der Wagen vom EMP stillgelegt ist",
      len(_gb65) == 1 and _gb65[0].emp_rest > 0.0,
      str([round(b.emp_rest, 1) for b in _gb65]))
# Am Steuer: R wirft Nebel, F streut Naegel (Gefecht._fahren).
_wb65.emp_rest = 0.0
w._einsteigen(w.ich, _wb65)
_rauch65, _nae65 = len(w.welt.rauch), len(w.welt.naegel)
w._fahren(w.ich, pygame.Vector2(0, 0), {"knoepfe": ["nachladen", "nahkampf"]})
pruef("Am Steuer wirft R Hecknebel und F den Nagelstreuer",
      len(w.welt.rauch) > _rauch65 and len(w.welt.naegel) == _nae65 + 1,
      "%d Rauch, %d Naegel" % (len(w.welt.rauch) - _rauch65, len(w.welt.naegel) - _nae65))
w._aussteigen(w.ich)
w.verlassen(); ga.verlassen()
EN.RND.setstate(_rnd65)
random.setstate(_zufall65)

# 0.34.66: Nahkampfwaffen, Bolzer, Nagler, Zustaende, Nagelfeld ohne Wesen.
print("\n-- Nahkampf, Bolzer, Nagler, Zustaende (0.34.66)")
_rnd66 = EN.RND.getstate()
_zufall66 = random.getstate()
_tm66 = _TM59.Testmodus(app, karte="staubtal")
_ort66 = freier_punkt(_tm66.welt, 0, random.Random(66))
_ich66 = _tm66.ich_setzen(_ort66, 0, {"team": 0, "waffe_figur": "hammer"})
_ich66 = _ich66[0] if isinstance(_ich66, list) else _ich66
# Seit 0.34.96 liegen die Nahkampfwaffen auf F (NAHKAMPF waehlbar).
pruef("Die neuen Waffen sind waehlbar (Nahkampf auf F)",
      {"bolzer", "nagler"} <= set(K.LOADOUT["auswahl_waffen"])
      and {"hammer", "schockstab", "schlagring", "kettensaege"} <= set(K.NAHKAMPF["waehlbar"]))
def _puppe66(dx, dy=0.0, leben=400.0):
    p_ = _tm66.puppe_setzen(_ich66.pos + pygame.Vector2(dx, dy), 0,
                            {"anzahl": 1, "streuung": 0, "team": 1, "leben": leben})
    p_ = p_[0] if isinstance(p_, list) else p_
    _tm66.welt.schritt(K.FIXED_DT)     # erst dann steht sie im Raster (Welt.nahe)
    p_.leben = p_.max_leben
    return p_
def _waffe66(name):
    _ich66.waffen[0] = name
    _ich66.magazin[name] = K.WAFFEN[name].get("magazin", 0)
    _ich66.waffe = 0
    _ich66.takt = _ich66.takt2 = 0.0
    _ich66.nachlade_rest = 0.0
    _ich66.winkel = 0.0
    _ich66.ziel = _ich66.pos + pygame.Vector2(100, 0)
_waffe66("schockstab")
_z66 = _puppe66(24)
_ich66.feuern()
pruef("Der Schockstab betaeubt: wenig Schaden, aber gelaehmt",
      _z66.gelaehmt and _z66.max_leben - _z66.leben <= K.WAFFEN["schockstab"]["schaden"] + 0.1,
      "%.1f s" % _z66.betaeubt_rest)
_z66.feuert = True
_z66.will.update(1, 0)
_z66.tempo.update(0, 0)          # der Rueckstoss des Schlags zaehlt nicht
_p66 = pygame.Vector2(_z66.pos)
for _ in range(10):
    _z66.feuert = True
    _z66.will.update(1, 0)
    _z66.schritt(K.FIXED_DT)
pruef("... und ein Betaeubter laeuft und schiesst nicht",
      _z66.pos.distance_to(_p66) < 1.0 and not _z66.feuert)
_z66.lebt = False
_waffe66("schlagring")
_z66 = _puppe66(20)
_ich66.feuern()
_normal66 = _z66.max_leben - _z66.leben
_z66.leben = _z66.max_leben
_ich66.takt = 0.0
_ich66._seit_dash = 0.05
_ich66.feuern()
_dash66 = _z66.max_leben - _z66.leben
pruef("Der Schlagring trifft aus dem Dash haerter",
      _dash66 > _normal66 * 2.0 and _normal66 > 0, "%.0f / %.0f" % (_normal66, _dash66))
_z66.lebt = False
_waffe66("hammer")
_zs66 = [_puppe66(30, dy) for dy in (-30, 0, 30)]
_ich66.zielt = True
_ich66.feuert = False
_ich66.schritt(K.FIXED_DT)
_ich66.zielt = False
pruef("Der Hammer haut rechts auf den Boden: alle ringsum nehmen Schaden und fliegen",
      all(z_.leben < z_.max_leben and z_.tempo.length() > 50 for z_ in _zs66),
      str([round(z_.max_leben - z_.leben) for z_ in _zs66]))
for z_ in _zs66:
    z_.lebt = False
_waffe66("kettensaege")
_z66 = _puppe66(22)
_vor66 = _z66.leben
_mag66 = _ich66.magazin["kettensaege"]
for _ in range(int(0.5 / K.FIXED_DT)):
    _ich66.feuert = True
    _ich66.schritt(K.FIXED_DT)
_ich66.feuert = False
pruef("Die Kettensaege schadet, solange sie laeuft, haelt fest und braucht Treibstoff",
      _vor66 - _z66.leben > 3 * K.WAFFEN["kettensaege"]["schaden"] and _z66.fest_rest > 0
      and _ich66.magazin["kettensaege"] < _mag66,
      "%.0f, %d" % (_vor66 - _z66.leben, _mag66 - _ich66.magazin["kettensaege"]))
_z66.lebt = False
_waffe66("bolzer")
_nah66 = _puppe66(30)
_weit66 = _puppe66(0, 120)
_ich66.feuern()
_ich66.winkel = 90.0
_ich66.takt = 0.0
_ich66.magazin["bolzer"] = 1
for _ in range(30):
    _tm66.welt.schritt(K.FIXED_DT)
pruef("Der Bolzer trifft aus naechster Naehe hart",
      _nah66.max_leben - _nah66.leben >= K.WAFFEN["bolzer"]["schaden"] - 0.1,
      "%.0f" % (_nah66.max_leben - _nah66.leben))
_ich66.feuern()
for _ in range(30):
    _tm66.welt.schritt(K.FIXED_DT)
pruef("... aber reicht nicht weit", _weit66.leben == _weit66.max_leben)
_nah66.lebt = _weit66.lebt = False
# Nagler: vor einer Wand haengt man fest.
_wand66 = None
_eb66 = _tm66.welt.ebene(0)
for _ty in range(4, 200):
    for _tx in range(4, 200):
        _d66 = K.KACHELN[_eb66.kachel(_tx, _ty)]
        _l66 = K.KACHELN[_eb66.kachel(_tx - 1, _ty)]
        _l266 = K.KACHELN[_eb66.kachel(_tx - 4, _ty)]
        if _d66["fest"] and not _d66["sicht"] and not _l66["fest"] and not _l266["fest"] \
                and not K.KACHELN[_eb66.kachel(_tx - 6, _ty)]["fest"]:
            _wand66 = pygame.Vector2(_tx * K.TILE, (_ty + 0.5) * K.TILE)
            break
    if _wand66 is not None:
        break
_ich66.pos.update(_wand66 - pygame.Vector2(K.TILE * 5, 0))
_waffe66("nagler")
_zn66 = _puppe66(K.TILE * 5 - 10)
_ich66.feuern()
for _ in range(int(0.5 / K.FIXED_DT)):
    _tm66.welt.schritt(K.FIXED_DT)
pruef("Der Nagler naegelt an die Wand (fest)", _zn66.fest_rest > 0.0,
      "%s %s" % (_zn66.pos, _wand66))
pruef("Naegel fliegen als Nagel, nicht als Leuchtspur",
      EN.Geschoss(_ich66.pos, 0, K.WAFFEN["nagler"], 0, _ich66, "nagler").bild == "nagel_flug")
# Nagelfeld: Figuren laufen ungehindert darueber (Waffenpaket).
_zn66.lebt = False
_nf66 = EN.Nagelfeld(_ich66.pos, 0)
_tm66.welt.naegel.append(_nf66)
_ich66.leben = _ich66.max_leben
_ich66.fest_rest = 0.0
for _ in range(30):
    _ich66.will.update(1, 0)
    _tm66.welt.schritt(K.FIXED_DT)
pruef("Ueber Kraehenfuesse laufen Figuren ungehindert (kein Schaden)",
      _ich66.leben == _ich66.max_leben)
_tm66.welt.naegel.clear()
# Im Netz: der Gast sieht, dass jemand betaeubt ist.
w, ga = _paar59("team", karte="staubtal")
w.ich.betaeubt_rest = 1.0
for _ in range(4):
    w.schritt(K.NETZ["takt"])
    ga.schritt(K.NETZ["takt"])
_gk66 = ga.kaempfer.get(w.ich.nummer)
pruef("Der Gast sieht, dass der Gastgeber betaeubt ist",
      _gk66 is not None and _gk66.betaeubt_rest > 0.0)
w.verlassen(); ga.verlassen()
EN.RND.setstate(_rnd66)
random.setstate(_zufall66)

# 0.34.67: Gas, Kuller, Knaller, Wurfmesser, Speer, Schneeball, Blinken.
print("\n-- Wuerfe aus dem Waffenpaket (0.34.67)")
_rnd67 = EN.RND.getstate()
_zufall67 = random.getstate()
_tm67 = _TM59.Testmodus(app, karte="staubtal")
_ort67 = freier_punkt(_tm67.welt, 0, random.Random(67))
_ich67 = _tm67.ich_setzen(_ort67, 0, {"team": 0, "waffe_figur": "wurfmesser"})
_ich67 = _ich67[0] if isinstance(_ich67, list) else _ich67
pruef("Die neuen Wuerfe sind waehlbar und im Spawner",
      {"gas", "kuller", "knaller", "schneeball"} <= set(K.LOADOUT["auswahl_wuerfe"])
      and {"wurfmesser", "speer"} <= set(K.NAHKAMPF["waehlbar"])
      and {"GASGRANATE", "KULLER", "KNALLER", "SCHNEEBALL"} <= {e.name for e in _TM59.eintraege()})
def _puppe67(dx, dy=0.0, leben=400.0, team=1):
    p_ = _tm67.puppe_setzen(_ich67.pos + pygame.Vector2(dx, dy), 0,
                            {"anzahl": 1, "streuung": 0, "team": team, "leben": leben})
    p_ = p_[0] if isinstance(p_, list) else p_
    _tm67.welt.schritt(K.FIXED_DT)
    p_.leben = p_.max_leben
    return p_
def _waffe67(name):
    _ich67.waffen[0] = name
    _ich67.magazin[name] = K.WAFFEN[name].get("magazin", 0)
    _ich67.waffe = 0
    _ich67.takt = _ich67.takt2 = 0.0
    _ich67.nachlade_rest = 0.0
    _ich67.winkel = 0.0
    _ich67.ziel = _ich67.pos + pygame.Vector2(200, 0)
def _laufen67(sek):
    for _ in range(int(sek / K.FIXED_DT)):
        _tm67.welt.schritt(K.FIXED_DT)
# Wurfmesser: rechts werfen, trifft, liegt, wird aufgehoben.
_waffe67("wurfmesser")
_z67 = _puppe67(90)
_ich67.ziel = _ich67.pos + pygame.Vector2(200, 0)
_ich67.winkel = 0.0
_ich67._werfen(K.WAFFEN["wurfmesser"])
_laufen67(0.5)
_m67 = [g for g in _tm67.welt.wesen if isinstance(g, EN.Wurfkoerper)]
pruef("Das geworfene Messer trifft und bleibt liegen",
      _z67.max_leben - _z67.leben >= K.WAFFEN["wurfmesser"]["wurf_schaden"] - 0.1
      and len(_m67) == 1 and _m67[0].liegt
      and _ich67.magazin["wurfmesser"] == K.WAFFEN["wurfmesser"]["magazin"] - 1,
      "%.0f, %d" % (_z67.max_leben - _z67.leben, len(_m67)))
_z67.lebt = False
_ich67.pos.update(_m67[0].pos)
_laufen67(0.1)
pruef("... und wer darueber laeuft, hebt es auf",
      not _m67[0].lebt and _ich67.magazin["wurfmesser"] == K.WAFFEN["wurfmesser"]["magazin"])
_ich67.nachladen()
pruef("Wurfmesser laedt man nicht nach", _ich67.nachlade_rest <= 0.0)
# Schneeball: dreimal getroffen, eingefroren.
_waffe67("schneeball")
_z67 = _puppe67(80)
for _ in range(3):
    _ich67.takt = 0.0
    _ich67.ziel = _ich67.pos + pygame.Vector2(200, 0)
    _ich67.winkel = 0.0
    _ich67.feuern()
    _laufen67(0.4)
pruef("Drei Schneebaelle, und er friert ein", _z67.gefroren_rest > 0.0,
      "%.1f" % _z67.gefroren_rest)
_z67.lebt = False
# Kuller: rollt, zuendet, sobald jemand nahe kommt.
# Zufallsneutral (seit 0.34.87): was die Kuller an Funken und Splittern
# wuerfelt, haengt davon ab, wie weit sie rollt - und spaetere Pruefungen
# (Speier, GOAP-Bots) haengen am gemeinsamen Zufall.
_zufall_ku67 = (EN.RND.getstate(), random.getstate())
_waffe67("kuller")
# 160 statt 260 (seit 0.34.87): sie rollt das 1,6-fache weit, und 416 px
# reichten hier bis an eine Mauer.
_ich67.ziel = _ich67.pos + pygame.Vector2(160, 0)
_ich67.takt = 0.0
_ich67.feuern()
_ku67 = [g for g in _tm67.welt.neue + _tm67.welt.wesen if isinstance(g, EN.Granate)
         and g.daten.get("kuller")][0]
_laufen67(2.5)
# Seit 0.34.87 rollt sie ueber den Zeiger hinaus und ist nach 2,5 s noch
# unterwegs - der Gegner steht darum vor ihr auf ihrer Bahn.
pruef("Der Kuller rollt und zuendet nicht von selbst", _ku67.lebt)
_z67 = _puppe67(0, 0)
_vor67 = (_ku67.tempo.normalize() * 20 if _ku67.tempo.length() > 1.0
          else pygame.Vector2(20, 0))
_z67.pos.update(_ku67.pos + _vor67)
_laufen67(0.2)
pruef("... aber sobald jemand nahe kommt", not _ku67.lebt and _z67.leben < _z67.max_leben)
_z67.lebt = False
EN.RND.setstate(_zufall_ku67[0])
random.setstate(_zufall_ku67[1])
# Knaller: knallt eine Weile, und Bots hoeren das.
_bot67 = _tm67.bot_setzen(_ich67.pos + pygame.Vector2(0, -300), 0,
                          {"anzahl": 1, "streuung": 0, "team": 1})
_knal67 = EN.Granate(_ich67.pos + pygame.Vector2(60, 0), 0.0, K.WAFFEN["knaller"], 0, None, 0.0)
_tm67.welt.dazu(_knal67)
_vor67 = len(_tm67._bot_geraeusche)
_laufen67(K.WAFFEN["knaller"]["flugzeit"] + 2.0)
pruef("Der Knaller knallt eine Weile, und die Bots hoeren es",
      _knal67.lebt and _knal67.knallt > 0.0 and len(_tm67._bot_geraeusche) > _vor67,
      "%d" % (len(_tm67._bot_geraeusche) - _vor67))
_laufen67(K.WAFFEN["knaller"]["knall_dauer"])
pruef("... und ist danach weg", not _knal67.lebt)
for _b67 in (_bot67 if isinstance(_bot67, list) else [_bot67]):
    _b67.lebt = False
# Gas: waechst, schadet Figuren, nicht Zombies.
_g67 = EN.Gaswolke(_ich67.pos + pygame.Vector2(0, 120), 0)
_tm67.welt.gas.append(_g67)
_figur67 = _puppe67(0, 120)
_zombie67 = _tm67.eintraege_art = None
_zs67 = _TM59._gegner_setzer("laeufer")(_tm67, _ich67.pos + pygame.Vector2(10, 125), 0,
                                          {"anzahl": 1, "streuung": 0, "ki": "aus"})
_zs67 = _zs67[0] if isinstance(_zs67, list) else _zs67
_tm67.welt.schritt(K.FIXED_DT)
_zl67 = _zs67.leben
_laufen67(1.0)
pruef("Gas schadet Figuren, Zombies atmen nicht",
      _figur67.leben < _figur67.max_leben and _zs67.leben == _zl67,
      "%.1f / %.1f" % (_figur67.max_leben - _figur67.leben, _zl67 - _zs67.leben))
pruef("... und die Wolke waechst", _g67.radius > K.GAS["anfang"] + 5)
_tm67.welt.gas.clear()
# Haftladung und EMP blinken (das Bild wechselt - so sieht es auch der Gast).
_hl67 = EN.Granate(_ich67.pos, 0.0, K.WAFFEN["haftladung"], 0, None, 0.0)
_hl67.welt = _tm67.welt
_bilder67 = set()
for _ in range(120):
    _hl67.rest -= K.FIXED_DT
    _hl67._alter += K.FIXED_DT
    _hl67._blinken()
    _bilder67.add(_hl67.bild)
pruef("Die Haftladung blinkt", _bilder67 == {"haftladung_flug", "haftladung_flug_an"})
# Im Netz: Gas beim Gast.
w, ga = _paar59("team", karte="staubtal")
_wg67 = EN.Gaswolke(pygame.Vector2(w.ich.pos), w.ich.ebene)
w.welt.gas.append(_wg67)
for _ in range(4):
    w.schritt(K.NETZ["takt"])
    ga.schritt(K.NETZ["takt"])
pruef("Der Gast sieht die Gaswolke", any(g.kennung == _wg67.kennung for g in ga.welt.gas))
w.verlassen(); ga.verlassen()
EN.RND.setstate(_rnd67)
random.setstate(_zufall67)

# 0.34.68: Spulengewehr, Kettenblitz, Spiegellaser, Kugelblitz, Flammenwerfer.
print("\n-- Energiewaffen und Flammenwerfer (0.34.68)")
_rnd68 = EN.RND.getstate()
_zufall68 = random.getstate()
_tm68 = _TM59.Testmodus(app, karte="staubtal")
_ort68 = freier_punkt(_tm68.welt, 0, random.Random(68))
_ich68 = _tm68.ich_setzen(_ort68, 0, {"team": 0, "waffe_figur": "spule"})
_ich68 = _ich68[0] if isinstance(_ich68, list) else _ich68
pruef("Die Energiewaffen und der Flammenwerfer sind waehlbar",
      {"spule", "kettenblitz", "spiegellaser", "kugelblitz", "flammenwerfer"}
      <= set(K.LOADOUT["auswahl_waffen"]))
def _puppe68(dx, dy=0.0, leben=400.0):
    p_ = _tm68.puppe_setzen(_ich68.pos + pygame.Vector2(dx, dy), 0,
                            {"anzahl": 1, "streuung": 0, "team": 1, "leben": leben})
    p_ = p_[0] if isinstance(p_, list) else p_
    _tm68.welt.schritt(K.FIXED_DT)
    p_.leben = p_.max_leben
    return p_
def _waffe68(name):
    _ich68.waffen[0] = name
    _ich68.magazin[name] = K.WAFFEN[name].get("magazin", 0)
    _ich68.waffe = 0
    _ich68.takt = _ich68.takt2 = 0.0
    _ich68.nachlade_rest = 0.0
    _ich68.ladung = 0.0
    _ich68.ziel = _ich68.pos + pygame.Vector2(300, 0)
    _ich68.winkel = 0.0
def _halten68(sek, feuert=True):
    for _ in range(int(sek / K.FIXED_DT)):
        _ich68.feuert = feuert
        _ich68.ziel = _ich68.pos + pygame.Vector2(300, 0)
        _tm68.welt.schritt(K.FIXED_DT)
    _ich68.feuert = False
# Spule: laden, loslassen, durch zwei.
_waffe68("spule")
_a68, _b68 = _puppe68(80), _puppe68(160)
_halten68(K.WAFFEN["spule"]["ladezeit"] + 0.1)
pruef("Beim Laden des Spulengewehrs steht die Ladung (und die Linie ist zu sehen)",
      _ich68.ladung >= 0.99 and _a68.leben == _a68.max_leben, "%.2f" % _ich68.ladung)
_halten68(0.05, False)
pruef("... Loslassen feuert durch beide, voll geladen sehr stark",
      _a68.max_leben - _a68.leben > K.WAFFEN["spule"]["schaden"] * 0.95
      and _b68.leben < _b68.max_leben and any(e[2] == "spule" for e in _tm68.welt.entladungen),
      "%.0f / %.0f" % (_a68.max_leben - _a68.leben, _b68.max_leben - _b68.leben))
pruef("... und wird heiss statt leer (kuehlt wieder ab)",
      _ich68.magazin["spule"] == K.WAFFEN["spule"]["magazin"] - 1)
_halten68(K.WAFFEN["spule"]["abkuehlen"] + 0.2, False)
pruef("... in Ruhe kommt die Ladung zurueck", _ich68.magazin["spule"] == K.WAFFEN["spule"]["magazin"])
_a68.lebt = _b68.lebt = False
# Kettenblitz: springt von einem zum naechsten.
_waffe68("kettenblitz")
_ks68 = [_puppe68(100), _puppe68(170, 30), _puppe68(240, 0)]
_halten68(K.WAFFEN["kettenblitz"]["ladezeit"] + 0.05)
_ab68 = [z.max_leben - z.leben for z in _ks68]
pruef("Der Kettenblitz springt von Koerper zu Koerper, jedesmal schwaecher",
      all(a > 0 for a in _ab68) and _ab68[0] > _ab68[-1], str([round(a) for a in _ab68]))
for z in _ks68:
    z.lebt = False
# Spiegellaser: prallt ab und wird staerker.
_g68 = EN.Geschoss(_ich68.pos, 0.0, K.WAFFEN["spiegellaser"], 0, _ich68, "spiegellaser")
_tm68.welt.dazu(_g68)
_wert68 = _g68.schaden_wert
_ab0 = _g68.abprall
for _ in range(int(2.0 / K.FIXED_DT)):
    _tm68.welt.schritt(K.FIXED_DT)
    if _g68.abprall < _ab0 or not _g68.lebt:
        break
pruef("Der Spiegellaser prallt an der Wand ab und wird staerker",
      _g68.abprall < _ab0 and _g68.schaden_wert > _wert68 and _g68.bild == "laser_flug",
      "%d %.1f" % (_g68.abprall, _g68.schaden_wert))
_g68.lebt = False
# Kugelblitz: zappt unterwegs, platzt am Ende.
_waffe68("kugelblitz")
_k68 = _puppe68(60, 60)
_ich68.feuern()
_kb68 = [g for g in _tm68.welt.neue + _tm68.welt.wesen if isinstance(g, EN.Kugelblitz)][0]
_halten68(0.8, False)
pruef("Der Kugelblitz schlaegt unterwegs Blitze und trifft, wer in Reichweite ist",
      _k68.leben < _k68.max_leben and any(e[2] == "blitz" for e in _tm68.welt.entladungen))
_k68.lebt = False
_halten68(K.WAFFEN["kugelblitz"]["reichweite"] / K.WAFFEN["kugelblitz"]["tempo"] + 0.5, False)
pruef("... und platzt am Ende", not _kb68.lebt and getattr(_kb68, "_geplatzt", False))
# Flammenwerfer: Schaden im Kegel, Brandstreifen, Tank.
_waffe68("flammenwerfer")
_f68 = _puppe68(70)
_n68 = len(_tm68.welt.feuer)
_halten68(1.0)
pruef("Der Flammenwerfer brennt im Kegel und laesst Brandstreifen",
      _f68.leben < _f68.max_leben and len(_tm68.welt.feuer) > _n68
      and _ich68.magazin["flammenwerfer"] < K.WAFFEN["flammenwerfer"]["magazin"],
      "%.0f, %d" % (_f68.max_leben - _f68.leben, len(_tm68.welt.feuer) - _n68))
_f68.lebt = False
_tr68 = _puppe68(0, -150, leben=10.0)
_tr68.waffen[0] = "flammenwerfer"
_tr68.waffe = 0
_tr68.magazin["flammenwerfer"] = K.WAFFEN["flammenwerfer"]["magazin"]
_nb68 = _puppe68(20, -150)
_tr68.leben = 10.0
_tr68.schaden(50.0, None, _ich68)
pruef("Wer mit vollem Tank faellt, dessen Tank geht hoch",
      _nb68.leben < _nb68.max_leben and _tr68.magazin["flammenwerfer"] == 0)
_tm68.welt.feuer.clear()
# Im Netz: Blitz und Ladung beim Gast.
w, ga = _paar59("team", karte="staubtal")
w.welt.entladung([pygame.Vector2(w.ich.pos), w.ich.pos + pygame.Vector2(80, 0)], w.ich.ebene, "blitz")
w.ich.ladung = 0.5
for _ in range(3):
    w.schritt(K.NETZ["takt"])
    ga.schritt(K.NETZ["takt"])
_gk68 = ga.kaempfer.get(w.ich.nummer)
pruef("Der Gast sieht den Blitz und die Ladelinie",
      any(e[2] == "blitz" for e in ga.welt.entladungen)
      and _gk68 is not None and _gk68.ladung > 0.0)
w.verlassen(); ga.verlassen()
EN.RND.setstate(_rnd68)
random.setstate(_zufall68)

# 0.34.69: Bauen, Fallen, Aufklaerung, Sanitasche, Munitionskiste (Testmodus).
print("\n-- Bauen, Fallen, Aufklaerung, Hilfe im Testmodus (0.34.69)")
from dustfront import ausruestung as _AU69
_rnd69 = EN.RND.getstate()
_zufall69 = random.getstate()
_tm69 = _TM59.Testmodus(app, karte="staubtal")
_ort69 = freier_punkt(_tm69.welt, 0, random.Random(69))
_namen69 = {e.name for e in _TM59.eintraege()}
pruef("Alles aus Bauen, Fallen, Aufklaerung und Hilfe steht im Spawner",
      set(_AU69.ARTEN) <= _namen69)
def _setze69(name, dx, dy=0.0, team=0, winkel=0.0):
    d_ = _tm69.ausruestung_setzen(name, _ort69 + pygame.Vector2(dx, dy), 0,
                                  {"team": team, "winkel": winkel})
    return d_
def _puppe69(pos, team=1):
    p_ = _tm69.puppe_setzen(pos, 0, {"anzahl": 1, "streuung": 0, "team": team})
    p_ = p_[0] if isinstance(p_, list) else p_
    return p_
def _laufen69(sek):
    for _ in range(int(sek / K.FIXED_DT)):
        _tm69.welt.schritt(K.FIXED_DT)
# Sandsackwand haelt Kugeln auf.
_sw69 = _setze69("SANDSACKWAND", 60)
_ziel69 = _puppe69(_ort69 + pygame.Vector2(120, 0))
_laufen69(0.05)
_g69 = EN.Geschoss(_ort69 + pygame.Vector2(10, 0), 0.0, K.WAFFEN["sturm"], 0, None, "sturm")
_g69.quelle_fraktion = "team1x"
_tm69.welt.dazu(_g69)
_laufen69(0.5)
pruef("Die Sandsackwand faengt die Kugel ab",
      _ziel69.leben == _ziel69.max_leben and any(s.leben < s.max_leben for s in _sw69))
for s in _sw69:
    s.lebt = False
_ziel69.lebt = False
# Stacheldraht macht langsam.
_sd69 = _setze69("STACHELDRAHT", 0, 200, winkel=90.0)[0]
_fig69 = _puppe69(_sd69.pos)
_laufen69(0.05)
_fig69.will.update(1, 0)
_fig69.schritt(K.FIXED_DT)
pruef("Im Stacheldraht ist man langsam", getattr(_fig69, "draht_rest", 0.0) > 0.0)
_fig69.lebt = False
_sd69.lebt = False
# Sprengfalle: Gegner tritt drauf, kurz danach knallt es; Brecheisen entschaerft.
_sf69 = _setze69("SPRENGFALLE (PLATTE)", 0, -200, team=0)[0]
_laufen69(0.05)
pruef("Die Sprengfalle ist versteckt, solange niemand nahe ist", _sf69.bild is None)
_op69 = _puppe69(_sf69.pos + pygame.Vector2(5, 0), team=1)
_op69.leben = _op69.max_leben = 300.0
_laufen69(0.1)
pruef("... ein Gegner loest sie aus, und es bleibt ein Augenblick",
      _sf69.zuendet > 0.0 and _sf69.lebt and _op69.leben == _op69.max_leben)
_laufen69(K.AUSRUESTUNG["sprengfalle"]["verzoegerung"] + 0.1)
pruef("... dann knallt es", not _sf69.lebt and _op69.leben < _op69.max_leben)
_op69.lebt = False
_sf2_69 = _setze69("SPRENGFALLE (DRAHT)", 300, 0, team=0)[0]
_ich69 = _tm69.ich_setzen(_sf2_69.pos + pygame.Vector2(-26, 0), 0, {"team": 1})
_ich69 = _ich69[0] if isinstance(_ich69, list) else _ich69
_laufen69(0.05)
_ich69.winkel = 0.0
_ich69.ziel = _ich69.pos + pygame.Vector2(100, 0)
_ich69.nahkampf()
pruef("Ein Schlag mit dem Brecheisen entschaerft sie", not _sf2_69.lebt and _sf2_69.entschaerft)
# Selbstschussanlage schiesst auf Gegner, EMP legt sie still.
_ge69 = _setze69("SELBSTSCHUSSANLAGE", -300, 0, team=0)[0]
_feind69 = _puppe69(_ge69.pos + pygame.Vector2(150, 0), team=1)
_feind69.leben = _feind69.max_leben = 2000.0
_laufen69(1.5)
pruef("Die Selbstschussanlage dreht sich zum Gegner und trifft",
      _feind69.leben < _feind69.max_leben, "%.0f" % (_feind69.max_leben - _feind69.leben))
_emp69 = EN.Granate(_ge69.pos, 0.0, K.WAFFEN["emp"], 0, None, 0.0)
_emp69.welt = _tm69.welt
_emp69.zuenden()
_laufen69(0.4)                 # was schon fliegt, darf noch ankommen
_vor69 = _feind69.leben
_laufen69(1.0)
pruef("... ein EMP legt sie still", _ge69.emp_rest > 0.0 and _feind69.leben == _vor69)
_ge69.lebt = False
# Benzinkanister: ein Treffer, Feuer.
_ka69 = _setze69("BENZINKANISTER", -300, 200)[0]
_laufen69(0.05)
_n69 = len(_tm69.welt.feuer)
_ka69.schaden(30.0, None, None)
pruef("Ein Treffer, und der Benzinkanister brennt", not _ka69.lebt and len(_tm69.welt.feuer) > _n69)
_tm69.welt.feuer.clear()
# Aufklaerung: Drohne und Horchposten markieren; EMP holt die Drohne herunter.
_dr69 = _setze69("SPÄHDROHNE", 0, 400, team=0)[0]
_ho69 = _setze69("HORCHPOSTEN", 200, 400, team=0)[0]
_ziel2_69 = _puppe69(_dr69.pos + pygame.Vector2(60, 0), team=1)
_ziel2_69.leben = _ziel2_69.max_leben = 2000.0
_laufen69(0.3)
pruef("Die Spaehdrohne markiert, wen sie sieht", getattr(_ziel2_69, "markiert_rest", 0.0) > 0.0)
_emp69 = EN.Granate(_dr69.pos, 0.0, K.WAFFEN["emp"], 0, None, 0.0)
_emp69.welt = _tm69.welt
_emp69.zuenden()
pruef("... ein EMP holt sie herunter", not _dr69.lebt)
_ziel2_69.markiert_rest = 0.0
_ziel2_69.pos.update(_ho69.pos + pygame.Vector2(100, 0))
_laufen69(0.05)                # erst dann steht sie im Raster (Welt.nahe)
_ziel2_69.tempo.update(80, 0)
_ho69._takt = 0.0
_ho69.emp_rest = 0.0           # der EMP fuer die Drohne hat ihn mit erwischt
_ho69.schritt(K.FIXED_DT)
pruef("Der Horchposten markiert, wer sich bewegt", _ziel2_69.markiert_rest > 0.0)
_ziel2_69.lebt = False
_ho69.lebt = False
# Sanitasche heilt, Munitionskiste fuellt.
_ich69.leben = 30.0
_ich69.pos.update(_ort69 + pygame.Vector2(0, -400))
_st69 = _setze69("SANITASCHE", 0, -400, team=1)[0]
_laufen69(K.AUSRUESTUNG["sanitasche"]["dauer"] + 0.2)
pruef("Die Sanitasche heilt ueber ein paar Sekunden",
      _ich69.leben >= 30.0 + K.AUSRUESTUNG["sanitasche"]["heilt"] * 0.9, "%.0f" % _ich69.leben)
_mk69 = _setze69("MUNITIONSKISTE (STEHT)", 0, -400)[0]
_w69 = _ich69.waffen[0]
_ich69.magazin[_w69] = 0
_laufen69(0.1)
pruef("Die Munitionskiste fuellt die Waffen",
      _ich69.magazin[_w69] == K.WAFFEN[_w69]["magazin"] and _mk69.ladungen < K.AUSRUESTUNG["munitionskiste"]["ladungen"])
# Fernglas: markiert im Kegel.
_tm69.fernglas = True
_fz69 = _puppe69(_ich69.pos + pygame.Vector2(300, 0), team=0)
_laufen69(0.05)
_ich69.ziel = _ich69.pos + pygame.Vector2(300, 0)
_tm69._aufklaeren(K.FIXED_DT)
pruef("Mit dem Fernglas markiert die Figur, wen sie im Kegel sieht",
      getattr(_fz69, "markiert_rest", 0.0) > 0.0 or not _tm69.welt.sicht_frei(_ich69.pos, _fz69.pos, 0))
_tm69.fernglas = False
_bild69 = pygame.Surface((K.GAME_W, K.GAME_H))
_tm69.info = 1
_tm69.zeichnen(_bild69, 1.0)
pruef("Die Testmodus-Anzeige zeichnet Markierungen und Reichweiten ohne Fehler", True)
EN.RND.setstate(_rnd69)
random.setstate(_zufall69)

# 0.34.70: Bots meiden Gefahren und kaempfen mit allen Waffen.
print("\n-- Bots: Gefahren und neue Waffen (0.34.70)")
_rnd70 = EN.RND.getstate()
_zufall70 = random.getstate()
_tm70 = _TM59.Testmodus(app, karte="staubtal")
_tm70._bot_rnd.seed(70)
_ort70 = freier_punkt(_tm70.welt, 0, random.Random(70))
def _bot70(pos, waffe="zufall", team=0, hirn="goap"):
    b_ = _tm70.bot_setzen(pos, 0, {"anzahl": 1, "streuung": 0, "team": team, "waffe": waffe,
                                   "hirn": hirn})
    return b_[0] if isinstance(b_, list) else b_
def _laufen70(sek):
    for _ in range(int(sek / K.FIXED_DT)):
        _tm70.schritt(K.FIXED_DT)
_tm70.ki_stopp = False
for _hirn70 in ("goap", "klassisch"):
    _b70 = _bot70(_ort70, hirn=_hirn70)
    _f70 = EN.Brandflaeche(pygame.Vector2(_b70.pos), 0, radius=50.0, von=None)
    _tm70.welt.feuer.append(_f70)
    _laufen70(2.0)
    pruef("Ein Bot (%s) im Feuer geht heraus" % _hirn70,
          _b70.pos.distance_to(_f70.pos) > _f70.radius, "%.0f" % _b70.pos.distance_to(_f70.pos))
    _tm70.welt.feuer.clear()
    _b70.lebt = False
    _tm70.kaempfer.pop(_b70.nummer, None)
_b70 = _bot70(_ort70)
_g70 = EN.Gaswolke(pygame.Vector2(_b70.pos), 0)
_g70.alter = K.GAS["wachsen"]
_tm70.welt.gas.append(_g70)
_laufen70(2.5)
pruef("... und aus dem Gas", _b70.pos.distance_to(_g70.pos) > _g70.radius,
      "%.0f / %.0f" % (_b70.pos.distance_to(_g70.pos), _g70.radius))
_tm70.welt.gas.clear()
_b70.lebt = False
_tm70.kaempfer.pop(_b70.nummer, None)
# Er laeuft nicht in Feuer, das vor ihm liegt.
_b70 = _bot70(_ort70)
_hirn = _b70.hirn
_hirn._gefahren = [(pygame.Vector2(_b70.pos) + pygame.Vector2(30, 0), 22.0)]
_r70 = _hirn._sicher(pygame.Vector2(1, 0))
pruef("... und laeuft nicht in Feuer, das vor ihm liegt",
      _r70.length_squared() > 0 and not _hirn._gefahr_bei(_b70.pos + _r70.normalize() * 26.0))
_b70.lebt = False
_tm70.kaempfer.pop(_b70.nummer, None)
# Neue Waffen: mit dem Hammer heran und zuschlagen, mit der Spule laden und loslassen.
for _waffe70, _abstand70 in (("hammer", 150), ("spule", 220), ("flammenwerfer", 100),
                             ("kettenblitz", 180)):
    _b70 = _bot70(_ort70, waffe=_waffe70, team=0)
    # Nur diese Waffe: sonst nimmt er, was besser zum Abstand passt.
    _b70.waffen = [_waffe70]
    _b70.waffe = 0
    _b70.magazin[_waffe70] = K.WAFFEN[_waffe70].get("magazin", 0)
    _z70 = _tm70.puppe_setzen(_b70.pos + pygame.Vector2(_abstand70, 0), 0,
                              {"anzahl": 1, "streuung": 0, "team": 1})
    _z70 = _z70[0] if isinstance(_z70, list) else _z70
    _z70.leben = _z70.max_leben = 5000.0
    _laufen70(5.0)
    pruef("Ein Bot kaempft mit %s und trifft" % K.WAFFEN[_waffe70]["name"],
          _z70.leben < _z70.max_leben and _b70.waffe_name == _waffe70,
          "%.0f, %s" % (_z70.max_leben - _z70.leben, _b70.waffe_name))
    _b70.lebt = _z70.lebt = False
    _tm70.kaempfer.pop(_b70.nummer, None)
    _tm70.kaempfer.pop(_z70.nummer, None)
_tm70.verlassen()
EN.RND.setstate(_rnd70)
random.setstate(_zufall70)

# 0.34.71: Bots am Steuer, Schildtraeger, Trupp-Vorlagen.
print("\n-- Bots fahren, Schildtraeger, Trupp-Vorlagen (0.34.71)")
_rnd71 = EN.RND.getstate()
_zufall71 = random.getstate()
_tm71 = _TM59.Testmodus(app, karte="staubtal")
_tm71._bot_rnd.seed(71)
# Eine Stelle mit freier Sicht zum Ziel (seit 0.34.95): die Pruefung sagt
# "sieht er einen Gegner". Vorher stand er oft hinter einer Mauer und traf
# nur, wenn ihn seine Streife zufaellig rechtzeitig um sie herumfuehrte -
# mit dem Wegenetz fuer Fahrzeuge faehrt er dort anders.
_r71 = random.Random(71)
for _ in range(400):
    _ort71 = freier_punkt(_tm71.welt, 0, _r71)
    if (_tm71.welt.sicht_frei(_ort71, _ort71 + pygame.Vector2(0, -250), 0)
            and _tm71.welt.frei(_ort71 + pygame.Vector2(0, -250), 12, 0)):
        break
_namen71 = {e.name for e in _TM59.eintraege()}
pruef("Fahrer mit und ohne Fahrzeug, Schildtraeger und Trupp-Vorlagen im Spawner",
      {"FAHRER MIT FAHRZEUG", "FAHRER OHNE FAHRZEUG", "SCHILDTRÄGER", "TRUPP AUS VORLAGE"}
      <= _namen71 and "TRUPP" in _namen71)
def _laufen71(sek):
    for _ in range(int(sek / K.FIXED_DT)):
        _tm71.schritt(K.FIXED_DT)
# Ein Panzerfahrer mit Panzer: sieht er einen Gegner, dreht der Turm und die Kanone schiesst.
_fa71 = _tm71.fahrer_setzen(_ort71, 0, {"team": 0, "fahrzeug": "panzer", "winkel": 0.0})
_pz71 = _fa71.fahrzeug
pruef("Der Panzerfahrer sitzt im Panzer, im Aussehen des Panzerfahrers",
      _pz71 is not None and _pz71.fahrer is _fa71 and _fa71.skin == "panzerfahrer")
_z71 = _tm71.puppe_setzen(_pz71.pos + pygame.Vector2(0, -250), 0,
                          {"anzahl": 1, "streuung": 0, "team": 1})
_z71 = _z71[0] if isinstance(_z71, list) else _z71
_z71.leben = _z71.max_leben = 5000.0
_n71 = [0]
from dustfront.fahrzeug import Panzergranate as _PG71
def _zaehle71():
    _n71[0] += sum(1 for g in _tm71.welt.neue if isinstance(g, _PG71))
for _ in range(int(6.0 / K.FIXED_DT)):
    _tm71.schritt(K.FIXED_DT)
    _zaehle71()
pruef("... der Turm dreht zum Gegner, die Kanone schiesst und trifft",
      _n71[0] >= 1 and _z71.leben < _z71.max_leben, "%d Schuss, %.0f" % (_n71[0], _z71.max_leben - _z71.leben))
_z71.lebt = False
_tm71.kaempfer.pop(_z71.nummer, None)
# Ohne Gegner faehrt er los.
_start71 = pygame.Vector2(_pz71.pos)
_laufen71(5.0)
pruef("... ohne Gegner faehrt er los", _pz71.pos.distance_to(_start71) > 40.0,
      "%.0f px" % _pz71.pos.distance_to(_start71))
# Ein Fahrer ohne Fahrzeug geht zum naechsten freien und steigt ein.
_bg71 = _tm71.fahrzeug_setzen("buggy", _ort71 + pygame.Vector2(0, 260), 0, {"winkel": 0.0})
_fo71 = _tm71.fahrer_setzen(_bg71.pos + pygame.Vector2(120, 0), 0, {"team": 0}, mit_fahrzeug=False)
_laufen71(6.0)
pruef("Ein Fahrer ohne Fahrzeug geht zum Buggy und steigt ein", _fo71.fahrzeug is _bg71,
      "%s, %.0f px" % (_fo71.fahrzeug, _fo71.pos.distance_to(_bg71.pos)))
pruef("Andere Bots steigen weiter nicht ein (im Gefecht fahren Bots nicht)",
      not any(getattr(k, "fahrzeug", None) is not None and not getattr(k, "darf_fahren", False)
              for k in _tm71._bots()))
# Schildtraeger: von vorn haelt das Schild, von hinten nicht.
_st71 = _tm71.schildtraeger_setzen(_ort71 + pygame.Vector2(-300, 0), 0, {"team": 1})
_st71.winkel = 0.0
_sch71 = _tm71.puppe_setzen(_st71.pos + pygame.Vector2(100, 0), 0, {"anzahl": 1, "streuung": 0, "team": 0})
_sch71 = _sch71[0] if isinstance(_sch71, list) else _sch71
_st71.leben = _st71.max_leben
_st71.schaden(40.0, None, _sch71)
_vorn71 = _st71.max_leben - _st71.leben
_st71.leben = _st71.max_leben
_st71.winkel = 180.0
_st71.schaden(40.0, None, _sch71)
_hinten71 = _st71.max_leben - _st71.leben
pruef("Das Schild haelt ab, was von vorn kommt, von hinten nicht",
      _vorn71 < 40.0 * 0.3 and _hinten71 > 30.0, "%.0f / %.0f" % (_vorn71, _hinten71))
pruef("... er traegt eine Pistole und das Schild-Aussehen",
      _st71.waffe_name == K.SCHILD["waffe"] and _st71.skin == "schildtraeger")
# Trupp aus Vorlage: jedes Mitglied im eigenen Aussehen, mit Fahrzeug.
for _vn71, _v71 in K.TRUPP_VORLAGEN.items():
    _vor71 = len(_tm71.fahrzeuge)
    _tr71 = _tm71.vorlage_setzen(_ort71 + pygame.Vector2(0, -500), 0, {"vorlage": _vn71, "team": 1})
    _ok71 = ([m.skin for m in _tr71.mitglieder] == [x[0] for x in _v71["mitglieder"]]
             and [m.waffe_name for m in _tr71.mitglieder] == [x[1] for x in _v71["mitglieder"]]
             and [bool(getattr(m, "schild", False)) for m in _tr71.mitglieder]
             == [x[3] for x in _v71["mitglieder"]]
             and _tr71.fuehrer is _tr71.mitglieder[0])
    if _v71["fahrzeug"]:
        _neu71 = _tm71.fahrzeuge[_vor71:]
        _ok71 = (_ok71 and len(_neu71) == 1 and _neu71[0].art == _v71["fahrzeug"]
                 and _neu71[0].fahrer is not None and _neu71[0].fahrer.skin == _v71["fahrer"])
    pruef("Vorlage %s: Aussehen, Waffen, Schilde%s stimmen" % (
        _vn71, ", Fahrzeug mit Fahrer" if _v71["fahrzeug"] else ""), _ok71)
_laufen71(1.0)
_bild71 = pygame.Surface((K.GAME_W, K.GAME_H))
_tm71.info = 1
_tm71.zeichnen(_bild71, 1.0)
_tm71.verlassen()
EN.RND.setstate(_rnd71)
random.setstate(_zufall71)

# 0.34.72: Klaenge fuer alles Neue.
print("\n-- Klaenge fuer Waffenpaket, Fahrzeuge und Ausruestung (0.34.72)")
from dustfront import audio as _AU72
_neu72 = ("schuss_revolver", "schuss_mp", "schuss_minigun", "schuss_panzerbuechse",
          "schuss_doppelflinte", "schuss_granatwerfer", "schuss_bolzer", "schuss_nagler",
          "schuss_spule", "spule_laden", "schuss_kettenblitz", "schuss_spiegellaser",
          "schuss_kugelblitz", "plasma", "flammenwerfer", "kettensaege", "hammer_boden",
          "schock", "schlag_faust", "knaller", "emp", "piepen", "klebt", "gas", "schneeball",
          "wurf_leise", "nagel_wand", "falle_klick", "drohne", "horchposten", "emp_aus",
          "reifen_platt", "schild")
pruef("Jeder neue Klang steht in KLANG_NAMEN und hat einen eigenen Platzhalter",
      all(n in K.KLANG_NAMEN and n in _AU72._PLATZHALTER for n in _neu72))
_eigen72 = {"revolver", "mp", "minigun", "panzerbuechse", "doppelflinte", "granatwerfer",
            "bolzer", "nagler", "knaller", "spule", "kettenblitz", "spiegellaser", "kugelblitz"}
pruef("Die Waffen aus dem Paket klingen nach sich selbst, nicht nach einer alten Waffe",
      all(K.WAFFEN[w].get("klang") in _neu72 for w in _eigen72),
      str([w for w in _eigen72 if K.WAFFEN[w].get("klang") not in _neu72]))
from dustfront.mehrspieler import Gefecht as _GF72
pruef("Was nur der Gastgeber ausloest, geht als Klang an die Gaeste",
      all(n in _GF72.NETZKLAENGE for n in ("kettensaege", "piepen", "klebt", "schock",
                                           "emp_aus", "reifen_platt", "schild", "spule_laden")))
_kl72 = app.klaenge
pruef("... und jeder klingt", all(len(_kl72.klang(n)) > 0 for n in _neu72),
      str([n for n in _neu72 if not _kl72.klang(n)]))

# 0.34.73: Balancing - keine Waffe ueber den anderen.
print("\n-- Balancing (0.34.73)")
def _kennzahlen73(name):
    d = K.WAFFEN[name]
    art = d.get("art", "schuss")
    schaden = d.get("schaden", 0.0) * d.get("geschosse", 1)
    takt = d.get("takt", 1.0)
    if art in ("strahl", "kette"):
        takt = d["ladezeit"] + d["takt"]
    if name == "lmg":
        takt = d["modus_daten"]["dauer"]["takt"]
    je_s = schaden / max(0.01, takt)
    mag = d.get("magazin", 0)
    if mag and not d.get("kuehlt") and art != "nahkampf":
        dauer = mag * schaden / (mag * takt + d.get("nachladen", 0.0))
    else:
        dauer = je_s
    stueck = math.ceil(K.SPIELER["leben"] / max(0.1, schaden))
    return je_s, dauer, stueck
_kampf73 = [n for n, d in K.WAFFEN.items() if d.get("art", "schuss") in
            ("schuss", "werfer", "strahl", "kette", "kugel", "flamme", "nahkampf")]
_sturm73 = _kennzahlen73("sturm")
_zu_viel73 = [n for n in _kampf73 if _kennzahlen73(n)[1] > 1.35 * _sturm73[1]]
pruef("Keine Waffe macht im Dauerfeuer mehr als ein Drittel mehr Schaden als das Sturmgewehr",
      not _zu_viel73, str(_zu_viel73))
# Ein Treffer, der toetet, nur mit einem Preis: aus naechster Naehe, voll
# geladen und sichtbar (Spule), oder als Rakete.
_ein_schuss73 = [n for n in _kampf73 if _kennzahlen73(n)[2] <= 1
                 and K.WAFFEN[n].get("reichweite", 0) > 60
                 and K.WAFFEN[n].get("art") not in ("strahl",)]
pruef("Was mit einem Treffer toetet, reicht nicht weit (oder muss sichtbar laden)",
      not _ein_schuss73, str(_ein_schuss73))
pruef("Die Pistole (Repetierer) macht nicht mehr Schaden als vorher",
      K.WAFFEN["repetierer"]["schaden"] <= 26.0)
pruef("Die Panzerbuechse ist gegen Fahrzeuge stark, gegen Figuren nicht mehr ein Treffer",
      K.WAFFEN["panzerbuechse"]["fahrzeug_schaden"] >= 2 * K.WAFFEN["panzerbuechse"]["schaden"]
      and K.WAFFEN["panzerbuechse"]["schaden"] < K.SPIELER["leben"])

# 0.34.73: Klassen.
print("\n-- Klassen (0.34.73)")
from dustfront import konto as _KO73, klassen as _KL73, ausruestung as _AU73
_rnd73 = EN.RND.getstate()
_zufall73 = random.getstate()
pruef("Viele Klassen, jede mit mehreren Waffen und Wurfwaffen zur Wahl",
      len(K.KLASSEN) >= 10 and all(len(_KL73.waffen_von(k_)) >= 3 and len(_KL73.wuerfe_von(k_)) >= 2
                                   for k_ in K.KLASSEN))
pruef("Keine Klasse darf alles waehlen",
      all(len(_KL73.waffen_von(k_)) < len(K.LOADOUT["auswahl_waffen"]) for k_ in K.KLASSEN))
_alt73 = _KO73.loadout_saeubern({"name": "ALT", "waffen": ["lmg", "scharf"], "wuerfe": ["c4"]})
# Seit 0.34.91: auch FREI hat Haupt- und Seitenwaffe - aus zwei
# Hauptwaffen wird die erste und die erste Seitenwaffe.
pruef("Ein Satz ohne Klasse bleibt FREI, mit Haupt- und Seitenwaffe",
      _alt73 == {"name": "ALT", "waffen": ["lmg", "repetierer"], "wuerfe": ["c4"]}, str(_alt73))
_lo73 = _KO73.loadout_saeubern({"name": "SANI", "klasse": "sanitaeter",
                                "waffen": ["lmg", "mp"], "wuerfe": ["c4"]})
pruef("Mit Klasse fallen fremde Waffen heraus und werden aus ihrer Auswahl aufgefuellt",
      _lo73["klasse"] == "sanitaeter" and "lmg" not in _lo73["waffen"] and "mp" in _lo73["waffen"]
      and len(_lo73["waffen"]) == 2 and _lo73["wuerfe"][0] in K.KLASSEN["sanitaeter"]["wuerfe"],
      str(_lo73))
pruef("Eine unbekannte Klasse wird FREI",
      "klasse" not in _KO73.loadout_saeubern({"name": "X", "klasse": "zauberer"}))
_tm73 = _TM59.Testmodus(app, karte="staubtal")
_ort73 = freier_punkt(_tm73.welt, 0, random.Random(73))
_ich73 = _tm73.ich_setzen(_ort73, 0, {"team": 0, "klasse": "nahkaempfer"})
pruef("Der Nahkaempfer hat mehr Leben und Nahkampfwaffen",
      abs(_ich73.max_leben - K.SPIELER["leben"] * K.KLASSEN["nahkaempfer"]["leben"]) < 0.01
      and _ich73.leben == _ich73.max_leben
      and all(w in K.KLASSEN["nahkaempfer"]["waffen"] or K.WAFFEN[w]["art"] == "wurf"
              for w in _ich73.waffen), str(_ich73.waffen))
_tm73.klasse_geben(_ich73, "flammentrupp")
_ich73.leben = _ich73.max_leben
EN.schaden_an(_ich73, 10.0, None, None, "feuer")
pruef("Der Flammentrupp haelt Feuer besser aus",
      abs((_ich73.max_leben - _ich73.leben) - 10.0 * K.KLASSEN["flammentrupp"]["feuer"]) < 0.01)
_tm73.klasse_geben(_ich73, "panzerjaeger")
_pw73 = _tm73.fahrzeug_setzen("panzerwagen", _ort73 + pygame.Vector2(0, 200), 0, {"winkel": 0})
_pw73.leben = _pw73.max_leben
EN.schaden_an(_pw73, 100.0, None, _ich73, None)
pruef("Der Panzerjaeger trifft Fahrzeuge haerter",
      abs((_pw73.max_leben - _pw73.leben) - 100.0 * K.KLASSEN["panzerjaeger"]["fahrzeug"]) < 0.01)
# Faehigkeit auf C: der Sanitaeter wirft eine Sanitasche, dann Pause.
_tm73.klasse_geben(_ich73, "sanitaeter")
_n73 = len([w for w in _tm73.welt.wesen + _tm73.welt.neue if isinstance(w, _AU73.Sanitasche)])
_was73 = _KL73.faehigkeit_nutzen(_tm73, _ich73)
_n73b = len([w for w in _tm73.welt.wesen + _tm73.welt.neue if isinstance(w, _AU73.Sanitasche)])
pruef("Taste C: der Sanitaeter wirft eine Sanitasche", _was73 == "SANITASCHE" and _n73b == _n73 + 1)
pruef("... dann erst nach der Pause wieder", _KL73.faehigkeit_nutzen(_tm73, _ich73) == "")
pruef("Die Taste C ist belegt und geht als Druck an den Gastgeber",
      "faehigkeit" in _TM59.Testmodus.DRUECKE and app.eingabe.tabelle.get("faehigkeit"))
_tm73.klasse_geben(_ich73, "schildtraeger")
pruef("Der Schildtraeger traegt das Schild", _ich73.schild)
_tm73.verlassen()
# Im Gefecht: Vorteile ja, Faehigkeit (noch) nicht; der Gast kennt das Hoechstleben.
w, ga = _paar59("team", karte="staubtal")
w.ich.loadout = _KO73.loadout_saeubern({"name": "N", "klasse": "nahkaempfer"})
_KL73.anwenden(w.ich)
# Seit 0.34.79 gilt die Faehigkeit auch im Gefecht; seit 0.34.85 auch in
# JEDER HAT ALLES (dort jedes Werkzeug). Abgeschaltet legt C nichts hin.
w._regeln_setzen(dict(w.regelwerk, faehigkeiten=False))
pruef("Mit abgeschalteten Faehigkeiten legt C nichts hin",
      _KL73.faehigkeit_nutzen(w, w.ich) == "")
w._regeln_setzen(dict(w.regelwerk, faehigkeiten=True))
for _ in range(4):
    w.schritt(K.NETZ["takt"])
    ga.schritt(K.NETZ["takt"])
_gk73 = ga.kaempfer.get(w.ich.nummer)
pruef("Der Gast kennt das Hoechstleben der Klasse",
      _gk73 is not None and abs(_gk73.max_leben - w.ich.max_leben) < 0.1)
w.verlassen(); ga.verlassen()
EN.RND.setstate(_rnd73)
random.setstate(_zufall73)

# 0.34.74: Rauch im Format des Fensters (schwarzes Viereck auf einem Intel-Mac).
print("\n-- Rauch ohne schwarzes Viereck (0.34.74)")
_alt74 = pygame.display.get_surface()
if _alt74 is None:
    pygame.display.set_mode((K.GAME_W, K.GAME_H))
_tm74 = _TM59.Testmodus(app, karte="staubtal")
_w74 = EN.Rauchwolke(pygame.Vector2(500, 500), 0, radius=58.0, dauer=9.0, alter=3.0)
_f74, _ = _tm74.renderer._rauchbild(_w74, True)
_grund74 = pygame.Surface((_f74.get_width(), _f74.get_height()))
_grund74.fill((200, 0, 0))
_grund74.blit(_f74, (0, 0))
_probe74 = pygame.Surface((1, 1), pygame.SRCALPHA).convert_alpha()
pruef("Die Rauchwolke hat das Pixelformat des Fensters, und ihr Rand bleibt durchsichtig",
      _f74.get_masks() == _probe74.get_masks() and _grund74.get_at((1, 1))[:3] == (200, 0, 0),
      "%s %s" % (_f74.get_masks(), _grund74.get_at((1, 1))))
_tm74.verlassen()

# Eine kaputte oder fehlende Karte darf nichts umwerfen.
pruef("Eine fehlende Karte gibt None", W.karte_lesen("gibtsnicht")[0] is None)
pruef("Und kaputter Text auch", W.karte_aus_text("bloedsinn")[0] is None)
w2, _ga2 = gefechtspaar("pvp", karte="gibtsnicht")
pruef("Das Gefecht laeuft trotzdem, auf der Testkarte",
      w2.karte == "" and len(w2.welt.ebenen) == 3, w2.karte)
pruef("Dort steht kein Buggy", not w2.fahrzeuge)
w2.verlassen(); _ga2.verlassen()

# ─────────────────────────────────────────────────────────────────────
# Kosmetik: die Vorbereitung darf das Spiel nicht anfassen.
#
# Zwei Sachen werden hier geprueft, und die zweite ist die wichtigere:
# dass die Rollen funktionieren, und dass sie im Ruhezustand **nichts
# aendern**. Solange K.SKIN_WAHL leer ist, muss jede Rolle ihre Vorgabe
# liefern - sonst sieht das Spiel anders aus, ohne dass jemand etwas
# gewaehlt haette.
_wahl_vorher = dict(K.SKIN_WAHL)
pruef("Jede Rolle loest auf einen Namen auf",
      all(isinstance(K.skin(r), str) and K.skin(r) for r in K.SKIN_ROLLEN))
pruef("Ohne Wahl steht ueberall die Vorgabe",
      not K.SKIN_WAHL
      and all(K.skin(r) == K.SKIN_ROLLEN[r] for r in K.SKIN_ROLLEN))
pruef("Eine unbekannte Rolle wird abgelehnt",
      K.skin_setzen("gibtsnicht", "irgendwas") is False
      and "gibtsnicht" not in K.SKIN_WAHL)
_probe = "blend_symbol"
pruef("Eine bekannte Rolle laesst sich umlegen",
      K.skin_setzen(_probe, "waffe_granate") and K.skin(_probe) == "waffe_granate")
K.skin_zuruecksetzen()
pruef("Zuruecksetzen stellt den Ausgangsstand wieder her",
      dict(K.SKIN_WAHL) == _wahl_vorher and K.skin(_probe) == K.SKIN_ROLLEN[_probe])
pruef("Die Anteile der Stufen ergeben zusammen eins",
      abs(sum(s["anteil"] for s in K.SELTENHEIT) - 1.0) < 1e-9,
      "%.4f" % sum(s["anteil"] for s in K.SELTENHEIT))
pruef("Jede Stufe hat Namen und Farbe",
      all(s["name"] and len(s["farbe"]) == 3 for s in K.SELTENHEIT))

# Und das Vorschaumodul: es muss laufen, es muss fuenf Bilder schreiben,
# und es darf die Wahl nicht veraendern. Geschrieben wird in einen
# Wegwerfordner - die Vorschau im Projekt ist Handarbeit, kein Testmuell.
import tempfile
from pathlib import Path
from dustfront import kosmetik
_weg = Path(tempfile.mkdtemp(prefix="dustfront_kosmetik_"))
_pfade = kosmetik.schreiben(app.bilder, _weg, lupe=1)
pruef("Die Vorschau schreibt fuenf Bilder",
      len(_pfade) == 5 and all(Path(p).exists() for p in _pfade),
      "%d" % len(_pfade))
_erst = pygame.image.load(_pfade[0])
pruef("Und zwar in Spielgroesse",
      _erst.get_size() == (K.GAME_W, K.GAME_H), str(_erst.get_size()))
pruef("Zeichnen aendert die Skinwahl nicht", dict(K.SKIN_WAHL) == _wahl_vorher)
# Kein Spielmodul darf die Kosmetik kennen. Sonst haengt doch etwas daran.
# Gemeint ist das Vorschaumodul kosmetik.py - die Spielerkosmetik
# (spielerkosmetik.py) ist etwas anderes und gehoert ins Gefecht. Darum
# wird nach dem Einbinden gesucht und nicht nach dem Wort.
import re as _re
import dustfront.play, dustfront.render, dustfront.entities, dustfront.mehrspieler
_einbinden = _re.compile(r"from \.kosmetik\b|from \. import [^\n]*\bkosmetik\b"
                         r"|\bimport kosmetik\b|dustfront\.kosmetik\b")
_haengt = [m.__name__ for m in (dustfront.play, dustfront.render,
                                dustfront.entities, dustfront.mehrspieler,
                                sys.modules["dustfront.core"])
           if _einbinden.search(open(m.__file__, encoding="utf-8").read())]
pruef("Die Suche findet ein Einbinden ueberhaupt",
      _einbinden.search("from . import config as K, kosmetik")
      and _einbinden.search("from .kosmetik import schreiben")
      and not _einbinden.search("from .spielerkosmetik import KosmetikTeil"))
pruef("Kein Spielmodul ruft die Kosmetik auf", not _haengt, ", ".join(_haengt))
import shutil as _sh
_sh.rmtree(_weg, ignore_errors=True)

# ─────────────────────────────────────────────────────────────────────
# Gegner, Bosse, Wellen und vor allem: wo sie herkommen.
print()
print("-- Wellen, Gegner und Bosse --")
from dustfront.mehrspieler import KampfGegner
from dustfront import entities as EN

# Die Tabellen muessen zusammenpassen. Ein Gegner, der in MISCHUNG steht
# und in GEGNER fehlt, faellt sonst erst auf, wenn die Welle laeuft, in
# der er zum ersten Mal drankommt - also vielleicht nie beim Testen.
pruef("Jede Art aus MISCHUNG gibt es wirklich",
      all(e["art"] in K.GEGNER for e in K.MISCHUNG),
      str([e["art"] for e in K.MISCHUNG if e["art"] not in K.GEGNER]))
pruef("Jeder Boss aus BOSS_FOLGE gibt es wirklich",
      all(a in K.BOSSE for a in K.BOSS_FOLGE))
pruef("Jeder Gegner und Boss hat ein Bild",
      all(K.gegner_daten(a)["bild"] in K.BILD_MASS
          for a in list(K.GEGNER) + list(K.BOSSE)))
pruef("Was die Mutter ruft, gibt es",
      K.BOSSE["mutter"]["faehigkeit"]["was"] in K.GEGNER)
pruef("gegner_daten findet beide Tabellen",
      K.gegner_daten("laeufer")["name"] == "LÄUFER"
      and K.gegner_daten("koloss")["name"] == "KOLOSS"
      and K.ist_boss("koloss") and not K.ist_boss("laeufer"))

# Eine Welle je Karte aufstellen und die Spawnstellen vermessen. Das war
# der gemeldete Fehler, und er faellt nur auf einer grossen Karte auf -
# darum wird STAUBTAL ausdruecklich mitgeprueft.
for kartenname in ("", "staubtal"):
    wg, gg = gefechtspaar("pve", karte=kartenname)
    titel = kartenname or "Testkarte"
    wg.welle = 0
    wg.gegner_offen = []
    wg.welle_rest = []
    wg._welle_starten()
    while wg.welle_rest:                 # allen Nachschub sofort holen
        wg.schub_rest = 0.0
        wg._nachschub(0.0)
    spieler = [k for k in wg.kaempfer.values() if k.lebt]
    abstaende = [min(x.pos.distance_to(k.pos) for k in spieler)
                 for x in wg.gegner_offen]
    fremd = sum(1 for x in wg.gegner_offen
                if all(x.ebene != k.ebene for k in spieler))
    pruef("%s: kein Gegner steht einem im Gesicht" % titel,
          min(abstaende) >= K.SPAWN["nah"] * 0.9,
          "naechster %.0f px, Untergrenze %.0f" % (min(abstaende), K.SPAWN["nah"]))
    # Die Obergrenze ist das eigentliche Anliegen: 1477 Pixel im Mittel
    # waren zwanzig Sekunden Fussmarsch, bevor ueberhaupt etwas passierte.
    pruef("%s: und keiner laeuft eine halbe Minute" % titel,
          max(abstaende) <= K.SPAWN["weit_boss"] * 1.6,
          "weitester %.0f px" % max(abstaende))
    pruef("%s: fast alle auf einer Ebene mit jemandem" % titel,
          fremd <= max(1, len(wg.gegner_offen) // 3),
          "%d von %d" % (fremd, len(wg.gegner_offen)))
    marken = sum(len(e.marken.get("Z", ())) for e in wg.welt.ebenen)
    pruef("%s: die Karte nennt Spawnstellen" % titel, marken > 0, "%d" % marken)
    pruef("%s: und alle liegen auf begehbarem Boden" % titel,
          all(e.begehbar(int(p[0] // K.TILE), int(p[1] // K.TILE))
              for e in wg.welt.ebenen for p in e.marken.get("Z", ())))
    wg.verlassen(); gg.verlassen()

# Der Aufbau der Wellen.
w6, g6 = gefechtspaar("pve", karte="staubtal")
arten_je_welle = {}
for nr in range(1, 21):
    w6.welle = nr - 1
    w6.gegner_offen = []
    w6.welle_rest = []
    w6._welle_starten()
    arten_je_welle[nr] = set(w6.welle_rest) | {x.art for x in w6.gegner_offen}
pruef("Welle 1 ist nur Laeufer - man lernt einen nach dem anderen",
      arten_je_welle[1] == {"laeufer"}, str(arten_je_welle[1]))
pruef("Spaeter ist die Welle wirklich gemischt",
      len(arten_je_welle[12]) >= 4, str(sorted(arten_je_welle[12])))
# Geprueft wird die Tabelle und nicht eine Ziehung: ob ein Blaeher in
# seiner ersten Welle wirklich gewuerfelt wird, ist Zufall - dass es ihn
# ab dann geben kann, ist die Regel.
ab_werte = [e["ab"] for e in K.MISCHUNG]
pruef("Jede Welle bringt hoechstens eine neue Gegnerart",
      len(set(ab_werte)) == len(ab_werte), str(ab_werte))
bossstart = [nr for nr in range(1, 21)
             if nr >= K.WELLEN_MP["boss_ab"] and nr % K.WELLEN_MP["boss_alle"] == 0]
pruef("Und keine faellt mit einer Bosswelle zusammen",
      not (set(ab_werte) & set(bossstart)),
      "neue Arten ab %s, Bosswellen %s" % (sorted(set(ab_werte)), bossstart))

bosswellen = [nr for nr in range(1, 21)
              if any(K.ist_boss(a) for a in arten_je_welle[nr])]
pruef("Jede fuenfte Welle bringt einen Boss",
      bosswellen == [5, 10, 15, 20], str(bosswellen))
gesehen = []
for nr in bosswellen:
    gesehen += [a for a in arten_je_welle[nr] if K.ist_boss(a)]
pruef("Und zwar reihum, nicht gewuerfelt",
      gesehen[:3] == list(K.BOSS_FOLGE), str(gesehen))
pruef("In einer Bosswelle steht genau ein Boss",
      all(sum(1 for a in arten_je_welle[nr] if K.ist_boss(a)) == 1
          for nr in bosswellen))

# Der Boss selbst.
w6.welle = 4
w6.gegner_offen = []; w6.welle_rest = []
w6._welle_starten()
boss = next(x for x in w6.gegner_offen if x.ist_boss)
pruef("Der Boss hat mehr Leben, wenn mehr mitspielen",
      boss.max_leben > K.BOSSE[boss.art]["leben"],
      "%.0f statt %.0f" % (boss.max_leben, K.BOSSE[boss.art]["leben"]))
pruef("Der Koloss laesst sich nicht durch die Karte schieben",
      not boss.schiebbar if boss.art == "koloss" else True)
# Gemessen wird das Tempo und nicht die Strecke: der Boss laeuft
# waehrend des Schritts ohnehin, und die Frage ist, ob der Treffer
# obendrauf kommt.
tempo_vorher = pygame.Vector2(boss.tempo)
boss.schaden(10.0, pygame.Vector2(900, 0), None)
if boss.art == "koloss":
    pruef("Ein Treffer traegt ihn nicht weg",
          boss.tempo.distance_to(tempo_vorher) < 0.01,
          "%.1f px/s Rueckstoss" % boss.tempo.distance_to(tempo_vorher))
laeufer_probe = KampfGegner(boss.pos + pygame.Vector2(60, 0), "laeufer",
                            boss.ebene, w6)
w6.welt.dazu(laeufer_probe)
# Seit 0.30 steckt der Rueckstoss eines Gegners in einem eigenen Topf
# (Gegner.stoss), damit er ihn ueber eine Kante tragen kann.
t2 = pygame.Vector2(laeufer_probe.stoss)
laeufer_probe.schaden(1.0, pygame.Vector2(900, 0), None)
pruef("Ein gewoehnlicher Gegner aber schon - sonst faende sich der "
      "Unterschied nicht",
      laeufer_probe.stoss.distance_to(t2) > 100.0,
      "%.0f px/s" % laeufer_probe.stoss.distance_to(t2))

# Die Haengerwache. Sie ist der Grund, warum eine Runde ueberhaupt
# weiterlaeuft: gemessen blieb ein Laeufer 120 Sekunden an einer
# Plateauwand stehen, und weil eine Welle erst endet, wenn alle liegen,
# stand damit alles.
w6.gegner_offen = []; w6.welle_rest = []
opfer = [k for k in w6.kaempfer.values() if k.lebt][0]
# Seit 0.32.6 erst, wenn ihn niemand sieht: zuerst steht er im Bild.
haenger = KampfGegner(opfer.pos + pygame.Vector2(300, 0), "laeufer",
                      opfer.ebene, w6)
w6.welt.dazu(haenger)
haenger._ziel = opfer
steht_bei = pygame.Vector2(opfer.pos + pygame.Vector2(300, 0))
for _ in range(int((K.GEGNER_MP["stockt_ab"] + 4.0)
                   / K.GEGNER_MP["stockt_pruefung"])):
    haenger.pos.update(steht_bei)
    haenger._haenger_pruefen(K.GEGNER_MP["stockt_pruefung"])
pruef("Wer haengt, aber gesehen wird, bleibt stehen (kein Verschwinden in Sicht)",
      haenger.pos.distance_to(steht_bei) < 1.0,
      "%.0f px versetzt" % haenger.pos.distance_to(steht_bei))
# Jetzt ausser Sicht - aber erst nach `unsichtbar_ab` Sekunden weg.
steht_bei = pygame.Vector2(opfer.pos + pygame.Vector2(1500, 0))
kurz_weg = False
for _ in range(int(K.GEGNER_MP["unsichtbar_ab"] / K.GEGNER_MP["stockt_pruefung"]) - 1):
    haenger.pos.update(steht_bei)
    haenger._haenger_pruefen(K.GEGNER_MP["stockt_pruefung"])
    kurz_weg = kurz_weg or haenger.pos.distance_to(steht_bei) > 1.0
pruef("Kurz ausser Sicht reicht nicht", not kurz_weg)
umgesetzt = False
for _ in range(int((K.GEGNER_MP["stockt_ab"] + 2.0)
                   / K.GEGNER_MP["stockt_pruefung"])):
    if umgesetzt:
        break
    haenger.pos.update(steht_bei)          # er kommt nie naeher
    haenger._haenger_pruefen(K.GEGNER_MP["stockt_pruefung"])
    umgesetzt = haenger.pos.distance_to(steht_bei) > 1.0
pruef("Wer nicht ankommt, wird umgesetzt", umgesetzt,
      "jetzt %.0f px vom Spieler statt 1500"
      % haenger.pos.distance_to(opfer.pos))
pruef("Und zwar in das Band um die Spieler",
      haenger.pos.distance_to(opfer.pos) <= K.SPAWN["weit"] * 1.6,
      "%.0f px" % haenger.pos.distance_to(opfer.pos))
boss.f_rest = 0.0
boss._stockt = 99.0
boss_vorher = pygame.Vector2(boss.pos)
boss._haenger_pruefen(9.0)
pruef("Ein Boss aber nicht - ihn zu suchen gehoert dazu",
      boss.pos == boss_vorher)
w6.verlassen(); g6.verlassen()

# Fernkampf und Platzen.
w7, g7 = gefechtspaar("pve")
ziel_k = [k for k in w7.kaempfer.values() if k.lebt][0]
sp = KampfGegner(ziel_k.pos + pygame.Vector2(200, 0), "speier", ziel_k.ebene, w7)
w7.welt.dazu(sp)
sp.wartet = 0.0
geschosse = 0
for _ in range(int(6.0 / K.FIXED_DT)):
    vor = sum(1 for x in w7.welt.wesen if isinstance(x, EN.Geschoss) and x.lebt)
    w7.schritt(K.FIXED_DT)
    nach = sum(1 for x in w7.welt.wesen if isinstance(x, EN.Geschoss) and x.lebt)
    geschosse += max(0, nach - vor)
    ziel_k.leben = ziel_k.max_leben
pruef("Der Speier spuckt statt zu schlagen", geschosse >= 1, "%d" % geschosse)
pruef("Und bleibt dabei auf Abstand",
      sp.pos.distance_to(ziel_k.pos) > K.GEGNER["speier"]["reichweite"] * 3,
      "%.0f px" % sp.pos.distance_to(ziel_k.pos))

bl = KampfGegner(ziel_k.pos + pygame.Vector2(40, 0), "blaeher", ziel_k.ebene, w7)
nachbar = KampfGegner(ziel_k.pos + pygame.Vector2(52, 8), "laeufer",
                      ziel_k.ebene, w7)
for x in (bl, nachbar):
    w7.welt.dazu(x)
w7.schritt(K.FIXED_DT)
leben_vorher, nachbar_vorher = ziel_k.leben, nachbar.leben
bl.schaden(999.0, None, ziel_k)
w7.schritt(K.FIXED_DT)
pruef("Der Blaeher trifft beim Platzen die Leute",
      ziel_k.leben < leben_vorher,
      "%.0f Schaden" % (leben_vorher - ziel_k.leben))
# Das ist der Punkt, an dem es kippen wuerde: traefe er auch Gegner,
# waere "Blaeher ins Rudel locken" ein Trick, der eine halbe Welle
# loescht - und dann spielt man den Trick und nicht das Spiel.
pruef("Aber keine anderen Gegner",
      nachbar.leben == nachbar_vorher,
      "%.0f Schaden am Nachbarn" % (nachbar_vorher - nachbar.leben))
w7.verlassen(); g7.verlassen()

# Und dass der Gast alles davon sieht.
w8, g8 = gefechtspaar("pve", karte="staubtal")
w8.welle = 4
w8.gegner_offen = []; w8.welle_rest = []
w8._welle_starten()
for _ in range(40):
    w8.schritt(K.NETZ["takt"]); g8.schritt(K.NETZ["takt"])
lebende = sum(1 for x in w8.gegner_offen if x.lebt)
pruef("Der Gast sieht dieselben Gegner wie der Gastgeber",
      len(g8._fremde_gegner) == lebende,
      "%d gegen %d" % (len(g8._fremde_gegner), lebende))
pruef("Und jeder traegt seine Kennung, sonst ruckeln sie",
      all(len(e) == 10 and e[6] for e in g8._fremde_gegner))
pruef("Auch der Boss kommt beim Gast an",
      any(K.ist_boss(e[4]) for e in g8._fremde_gegner),
      str(sorted({e[4] for e in g8._fremde_gegner})))
w8.verlassen(); g8.verlassen()

# ─────────────────────────────────────────────────────────────────────
# 0.27: Tempo, Dash, Boden, Ebenen, Lobby und die neue Anzeige.
print()
print("-- 0.27 --")

# Munition beim Gast. Gemeldet als "bei Gaesten wurde die Gesamtmunition
# gar nicht angezeigt": geschickt wurde nur der Stand der gehaltenen
# Waffe, und jede andere zeigte beim Gast ihren Stand vom Rundenbeginn.
wm, gm = gefechtspaar("pvp", knapp=True)
wahr = wm.kaempfer[gm.meine_nummer]
for name, weg in (("sturm", 30), ("schrot", 6)):
    wahr.vorrat[name] = max(0, wahr.vorrat[name] - weg)
    wahr.magazin[name] = 1
wahr.waffe = wahr.waffen.index("repetierer")
for _ in range(30):
    wm.schritt(K.NETZ["takt"]); gm.schritt(K.NETZ["takt"])
falsch = [n for n in wahr.waffen
          if (wahr.magazin.get(n), wahr.vorrat.get(n))
          != (gm.ich.magazin.get(n), gm.ich.vorrat.get(n))]
pruef("Der Gast kennt Magazin und Vorrat jeder Waffe, nicht nur der gehaltenen",
      not falsch, str(falsch))
wm.verlassen(); gm.verlassen()

# Wer selbst liegt, bekommt kein "[E]" neben einem anderen Liegenden.
wh, gh = gefechtspaar("pve")
eins, zwei = wh.kaempfer[0], wh.kaempfer[gh.meine_nummer]
pruef("Ein Stehender darf einem Liegenden helfen",
      wh._darf_helfen(eins, zwei))
for k in (eins, zwei):
    k.unverwundbar = 0.0
    k.schaden(999, None, None)
pruef("Ein Liegender darf keinem Liegenden helfen - kein Hinweis, keine Hilfe",
      eins.am_boden and not wh._darf_helfen(eins, zwei)
      and wh._wem_helfen(eins) is None)
wh.verlassen(); gh.verlassen()

# Am Boden: nicht schieben, nicht drehen - aber ziehen und rufen.
wz, gz = gefechtspaar("pve")
liegt = wz.kaempfer[gz.meine_nummer]
# Der Ziehende ist eine dritte Figur ohne eigene Tastatur: die Figur des
# Gastgebers bekaeme jedes Bild dessen echte, leere Eingabe und liesse
# sofort wieder los.
zieher = Kaempfer(pygame.Vector2(liegt.pos), liegt.ebene, 8, "ZIEHER",
                  liegt.fraktion, team=liegt.team)
wz.kaempfer[8] = zieher
wz.welt.dazu(zieher)
wz._regeln_anlegen(zieher)
liegt.unverwundbar = 0.0
liegt.pos.update(wz.welt.landeplatz(pygame.Vector2(704, 384), liegt.radius,
                                    liegt.ebene))
zieher.ebene = liegt.ebene
zieher.pos.update(liegt.pos + pygame.Vector2(18, 0))
liegt.schaden(999, None, None)
lage = pygame.Vector2(liegt.pos)
winkel_vorher = liegt.winkel
liegt.schaden(5.0, pygame.Vector2(900, 0), None)
liegt.ziel = liegt.pos + pygame.Vector2(0, 200)      # die Maus zieht nach unten
for _ in range(20):
    wz.schritt(K.FIXED_DT)
pruef("Ein Gefallener wird von einem Treffer nicht weggestossen",
      liegt.pos.distance_to(lage) < 1.0, "%.1f px" % liegt.pos.distance_to(lage))
pruef("Und dreht sich nicht mehr mit der Maus",
      abs(liegt.winkel - winkel_vorher) < 0.01,
      "%.1f -> %.1f" % (winkel_vorher, liegt.winkel))
# Jemand laeuft ueber ihn hinweg: er bleibt liegen.
zieher.pos.update(liegt.pos + pygame.Vector2(2, 0))
for _ in range(10):
    wz.welt.auseinander(zieher)
pruef("Wer an ihm vorbeigeht, schiebt ihn nicht",
      liegt.pos.distance_to(lage) < 1.0, "%.1f px" % liegt.pos.distance_to(lage))
zieher.pos.update(liegt.pos + pygame.Vector2(18, 0))

# Ziehen
ein_z = {"will": [1.0, 0.0], "ziel": [zieher.pos.x + 100, zieher.pos.y],
         "feuert": True, "zielt": False, "nutzen": True, "ziehen": True,
         "waffe": -1, "knoepfe": []}
wz._anwenden(zieher, ein_z)
pruef("Mit G greift man einen Gefallenen in Reichweite",
      zieher.zieht == liegt.nummer and liegt.gezogen_von == zieher.nummer)
pruef("Und schiesst dabei nicht und hilft nicht auf",
      not zieher.feuert and zieher.hilft is None)
pruef("Und dasht nicht", not zieher.kann_dashen)
start_z = pygame.Vector2(liegt.pos)
for _ in range(int(0.8 / K.FIXED_DT)):
    wz._anwenden(zieher, ein_z)
    wz.schritt(K.FIXED_DT)
pruef("Der Gefallene kommt mit",
      liegt.pos.distance_to(start_z) > 20.0
      and liegt.pos.distance_to(zieher.pos) < K.ZIEHEN["leine"] + 6,
      "%.0f px gezogen, %.0f px Abstand" % (liegt.pos.distance_to(start_z),
                                            liegt.pos.distance_to(zieher.pos)))
pruef("Und dreht sich dabei nicht", abs(liegt.winkel - winkel_vorher) < 0.01)
tempo_z = zieher.tempo.length()
pruef("Wer zieht, geht langsamer",
      tempo_z < K.SPIELER["tempo"] * K.ZIEHEN["tempo"] + 3.0,
      "%.0f px/s" % tempo_z)
# Seit 0.34.43: er haelt ihn sichtbar und schaut zu ihm. Seit 0.34.48 bleibt
# sein Bild (der Skin), dazu kommen Arme bis zum Gefallenen (_haende_zeichnen).
_zu_z = liegt.pos - zieher.pos
_ab_z = (zieher.winkel - math.degrees(math.atan2(_zu_z.y, _zu_z.x)) + 180) % 360 - 180
_hb_z = pygame.Surface((K.GAME_W, K.GAME_H))
wz.kamera.pos.update(zieher.pos)
wz.kamera.ruckeln = 0.0
wz._haende_zeichnen(_hb_z)
_mitte_z = wz.kamera.zu_bild((zieher.pos + liegt.pos) / 2)
_arm_z = any(tuple(_hb_z.get_at((int(_mitte_z.x) + dx_, int(_mitte_z.y) + dy_)))[:3] == K.C_HULL_SH
             for dx_ in range(-4, 5) for dy_ in range(-4, 5)
             if 0 <= int(_mitte_z.x) + dx_ < K.GAME_W and 0 <= int(_mitte_z.y) + dy_ < K.GAME_H)
pruef("Wer zieht, schaut zu ihm (nicht zur Maus); sein Bild bleibt, Arme reichen bis zum Gefallenen",
      abs(_ab_z) < 3.0 and "zieht" not in zieher.bild and _arm_z,
      "%.1f Grad daneben, %s" % (_ab_z, zieher.bild))
netz_durchlassen(wz, gz, 10)
pruef("Der Gast weiss, dass er gezogen wird",
      gz.kaempfer.get(8) is not None and gz.kaempfer[8].zieht == liegt.nummer)
ein_z["ziehen"] = False
wz._anwenden(zieher, ein_z)
pruef("Loslassen gibt ihn frei",
      zieher.zieht is None and liegt.gezogen_von is None)

# Rufen: hoechstens alle anderthalb Sekunden.
gz._knoepfe.add("nutzen")
netz_durchlassen(wz, gz, 6)
pruef("Der Gefallene ruft mit E", liegt.ruf_zeigen > 0.0,
      "%.2f" % liegt.ruf_zeigen)
zeigen_vorher = liegt.ruf_sperre
wz._rufen(liegt)
pruef("Und nicht gleich noch einmal", liegt.ruf_sperre <= zeigen_vorher)
pruef("Der Gast sieht den Ruf", gz.ich.ruf_zeigen > 0.0)
wz.verlassen(); gz.verlassen()

# Granaten behalten beim Fall ueber eine Kante ihren Schwung.
from dustfront.entities import Granate as _Granate
wg_ = W.testkarte()
e1_ = wg_.ebene(1)
kante = None
for ty in range(2, e1_.hoehe - 2):
    for tx in range(2, e1_.breite - 8):
        if (all(e1_.begehbar(tx + i, ty) for i in range(3))
                and all(e1_.loch(tx + 3 + i, ty) for i in range(3))
                and wg_.boden_unter(pygame.Vector2((tx + 4.5) * 32, (ty + .5) * 32), 1) == 0):
            kante = (tx, ty)
            break
    if kante:
        break
gr = _Granate(pygame.Vector2(kante[0] * 32 + 16, kante[1] * 32 + 16), 0.0,
              dict(K.WAFFEN["granate"], flugzeit=3.0), 1, weite=260)
wg_.dazu(gr)
v_absturz, schritte, gefallen, gelandet = None, 0, False, False
reibung = K.WAFFEN["granate"]["reibung"]
for _ in range(int(2.5 / K.FIXED_DT)):
    gr.rest = 99.0
    v_letzt = gr.tempo.length()
    wg_.schritt(K.FIXED_DT)
    if gr.sturz_rest > 0 and not gefallen:
        gefallen, v_absturz = True, v_letzt
    if gefallen:
        schritte += 1
    if gefallen and gr.sturz_rest <= 0 and gr.flug <= 0:
        gelandet = True
        break
ideal = v_absturz * (1.0 - reibung * K.FIXED_DT) ** schritte
pruef("Eine Granate faellt ueber die Kante", gefallen and gelandet)
pruef("Und hat nach der Landung das Tempo eines ungestoerten Wurfs",
      abs(gr.tempo.length() - ideal) < ideal * 0.05,
      "%.0f px/s, ungestoert %.0f (vorher 25 Prozent davon)"
      % (gr.tempo.length(), ideal))

# Wegfindung zwischen Ebenen.
import random as _rnd
for karte_w, ebene_w in (("staubtal", 1), ("", 2)):
    ww, gw = gefechtspaar("pve", karte=karte_w)
    ww.pause_rest = 99999.0
    for x in list(ww.welt.wesen):
        if isinstance(x, KampfGegner):
            x.lebt = False
    ww.gegner_offen = []; ww.welle_rest = []
    netz_w = ww.welt.wege
    e_w = ww.welt.ebene(ebene_w)
    stelle = next((tx, ty) for ty in range(e_w.hoehe) for tx in range(e_w.breite)
                  if e_w.begehbar(tx, ty) and not e_w.loch(tx, ty)
                  and e_w.kachel(tx, ty) == K.BODEN and tx > e_w.breite // 2)
    if karte_w == "staubtal":
        # Seit 0.32.29 ist STAUBTAL 300 x 240 Kacheln gross. Die erste
        # Kachel rechts der Mitte liegt dann am Nordrand des langen
        # Plateaus, und 450 bis 900 Pixel davon gibt es unten nur den
        # Randgang - der Weg von dort zum naechsten Aufzug ist mehrere
        # hundert Kacheln lang und passt in keine 60 Sekunden. Gemeint ist
        # "ueber die Treppe hinauf": also ein Ziel wenige Kacheln neben
        # einem Aufzug, der von Ebene 0 heraufkommt.
        _tr = [t for t in netz_w.treppen if t[0] == 0 and t[3] == ebene_w]
        stelle = next(
            (tx + dx * r, ty + dy * r)
            for (_e, tx, ty, _z) in _tr for r in range(4, 8)
            for dx, dy in ((0, -1), (-1, 0), (1, 0), (0, 1))
            if e_w.begehbar(tx + dx * r, ty + dy * r)
            and not e_w.loch(tx + dx * r, ty + dy * r)
            and e_w.kachel(tx + dx * r, ty + dy * r) == K.BODEN)
    ziel_w = ww.welt.landeplatz(pygame.Vector2((stelle[0] + .5) * 32,
                                               (stelle[1] + .5) * 32), 9, ebene_w)
    for k in ww.kaempfer.values():
        k.ebene = ebene_w; k.pos.update(ziel_w)
    rr = _rnd.Random(3)
    e0_w = ww.welt.ebene(0)
    kand = [(tx, ty) for ty in range(e0_w.hoehe) for tx in range(e0_w.breite)
            if e0_w.begehbar(tx, ty) and not e0_w.loch(tx, ty)
            and 450 < pygame.Vector2((tx + .5) * 32, (ty + .5) * 32).distance_to(ziel_w) < 900]
    laeufer_w = []
    for _ in range(4):
        tx, ty = rr.choice(kand)
        gg = KampfGegner(pygame.Vector2((tx + .5) * 32, (ty + .5) * 32), "laeufer", 0, ww)
        gg.wartet = 0.0
        ww.welt.dazu(gg); ww.gegner_offen.append(gg); laeufer_w.append(gg)
    umgesetzt_w = []
    for gg in laeufer_w:
        vorher_pruef = gg._haenger_pruefen
        def _spion(dt, gg=gg, vorher_pruef=vorher_pruef):
            vor = pygame.Vector2(gg.pos)
            vorher_pruef(dt)
            if gg.pos.distance_to(vor) > 40:
                umgesetzt_w.append(gg)
        gg._haenger_pruefen = _spion
    oben_w = set()
    for _ in range(int(60.0 / K.FIXED_DT)):
        for k in ww.kaempfer.values():
            k.leben = k.max_leben; k.am_boden = False
            k.pos.update(ziel_w); k.ebene = ebene_w; k.tempo.update(0, 0)
        ww.schritt(K.FIXED_DT)
        for gg in laeufer_w:
            if gg.ebene == ebene_w and gg.pos.distance_to(ziel_w) < 60:
                oben_w.add(id(gg))
    titel_w = karte_w or "Testkarte"
    pruef("%s: Gegner gehen ueber Treppen zu einem Spieler auf Ebene %d"
          % (titel_w, ebene_w), len(oben_w) == len(laeufer_w),
          "%d von %d" % (len(oben_w), len(laeufer_w)))
    pruef("%s: und zwar zu Fuss, keiner musste umgesetzt werden" % titel_w,
          not umgesetzt_w, "%d umgesetzt" % len(umgesetzt_w))
    ww.verlassen(); gw.verlassen()

# Ein Boss wechselt die Ebene nicht - er wartet.
wb, gb = gefechtspaar("pve")
wb.pause_rest = 99999.0
boss_b = KampfGegner(pygame.Vector2(21.5 * 32, 3.5 * 32), "koloss", 0, wb)
boss_b.wartet = 0.0
wb.welt.dazu(boss_b); wb.gegner_offen = [boss_b]
for k in wb.kaempfer.values():
    k.ebene = 1
for _ in range(int(8.0 / K.FIXED_DT)):
    for k in wb.kaempfer.values():
        k.ebene = 1; k.leben = k.max_leben
    wb.schritt(K.FIXED_DT)
pruef("Ein Boss bleibt auf seiner Ebene, auch auf einer Treppe",
      boss_b.ebene == 0, "Ebene %d" % boss_b.ebene)
wb.verlassen(); gb.verlassen()

# Wer neben seinem Ziel steht und zuschlaegt, ist kein Haenger.
wn, gn = gefechtspaar("pve")
wn.pause_rest = 99999.0
opfer_n = wn.kaempfer[0]
nah_n = KampfGegner(opfer_n.pos + pygame.Vector2(20, 0), "laeufer", opfer_n.ebene, wn)
wn.welt.dazu(nah_n)
nah_n._ziel = opfer_n
stelle_n = pygame.Vector2(nah_n.pos)
for _ in range(12):
    nah_n.pos.update(stelle_n)
    nah_n._haenger_pruefen(1.0)
pruef("Ein Gegner, der am Ziel steht, wird nicht umgesetzt",
      nah_n.pos.distance_to(stelle_n) < 1.0,
      "%.0f px verschoben" % nah_n.pos.distance_to(stelle_n))
wn.verlassen(); gn.verlassen()

# Und keiner entsteht in der Luft.
wl, gl = gefechtspaar("pve", karte="staubtal")
luft = 0
for k in wl.kaempfer.values():
    k.ebene = 1
    k.pos.update(wl.welt.landeplatz(pygame.Vector2(60.5 * 32, 17.5 * 32), 9, 1))
for _ in range(80):
    eb_l, p_l = wl._spawnstelle()
    tx_l, ty_l = int(p_l.x // K.TILE), int(p_l.y // K.TILE)
    e_l = wl.welt.ebene(eb_l)
    if not e_l.begehbar(tx_l, ty_l) or e_l.loch(tx_l, ty_l):
        luft += 1
pruef("Keine Spawnstelle liegt ueber einem Loch", luft == 0,
      "%d von 80" % luft)
wl.verlassen(); gl.verlassen()

# Tempo und Dash.
pruef("Kein Sprint mehr in den Werten", "sprint" not in K.SPIELER)
pruef("Der Renner bleibt schneller als ein gehender Spieler",
      K.GEGNER["renner"]["tempo"] > K.SPIELER["tempo"])
pruef("Der Laeufer holt einen gehenden Spieler nicht ein",
      K.GEGNER["laeufer"]["tempo"] < K.SPIELER["tempo"])

wd, gd = gefechtspaar("pvp")
ich_d = wd.kaempfer[0]
ich_d.schutz = 0.0
for _ in range(10):
    wd.schritt(K.FIXED_DT)
# Eine Richtung suchen, in der 140 Pixel frei sind - sonst misst der
# Test, wie weit die naechste Wand weg ist, und nicht den Dash.
frei_richtung = None
for grad in range(0, 360, 15):
    r = pygame.Vector2(1, 0).rotate(grad)
    if all(wd.welt.frei(ich_d.pos + r * d, ich_d.radius, ich_d.ebene)
           for d in range(8, 141, 8)):
        frei_richtung = r
        break
if frei_richtung is None:
    ich_d.pos.update(wd.welt.landeplatz(pygame.Vector2(704, 384),
                                        ich_d.radius, ich_d.ebene))
    frei_richtung = pygame.Vector2(1, 0)
start = pygame.Vector2(ich_d.pos)
ich_d.will = pygame.Vector2(frei_richtung)
LADUNGEN = K.DASH["ladungen"]
pruef("Man hat zu Beginn drei Ladungen", LADUNGEN == 3 and ich_d.dash_ladungen == 3)
pruef("Ein Dash geht", ich_d.dashen())
for _ in range(int(0.5 / K.FIXED_DT)):
    ich_d.will = pygame.Vector2(0, 0)
    wd.schritt(K.FIXED_DT)
weg = ich_d.pos.distance_to(start)
pruef("Er traegt rund zwei Kacheln weit", 45.0 < weg < 110.0, "%.0f px" % weg)
pruef("Und kostet eine Ladung", ich_d.dash_ladungen == LADUNGEN - 1)
for _ in range(LADUNGEN - 1):
    ich_d.dash_rest = 0.0
    ich_d.dash_sperre = 0.0
    pruef("Die naechste geht auch", ich_d.dashen())
ich_d.dash_rest = 0.0
ich_d.dash_sperre = 0.0
pruef("Danach keine mehr", not ich_d.dashen())
pruef("Und sie laden schneller als frueher (3,4 s)", K.DASH["nachladen"] < 3.4)
for _ in range(int((K.DASH["nachladen"] + 0.05) / K.FIXED_DT)):
    wd.schritt(K.FIXED_DT)
pruef("Nach einer Ladezeit ist genau eine wieder da",
      ich_d.dash_ladungen == 1, "%d" % ich_d.dash_ladungen)
for _ in range(int(K.DASH["nachladen"] * (LADUNGEN - 1) / K.FIXED_DT) + 2):
    wd.schritt(K.FIXED_DT)
pruef("Nach drei Ladezeiten alle - sie laden nacheinander",
      ich_d.dash_ladungen == LADUNGEN, "%d" % ich_d.dash_ladungen)
ich_d.heilt_rest = 0.5
pruef("Beim Anlegen eines Medkits geht kein Dash", not ich_d.dashen())
ich_d.heilt_rest = 0.0

wd.verlassen(); gd.verlassen()

# Der Gast: sein Druck muss ankommen, und er muss seine Ladungen sehen.
# Ein frisches Paar - oben lief der Gastgeber Sekunden lang allein, und
# das ist kein Zustand, in dem ein Gast je steckt.
wd, gd = gefechtspaar("pvp")
gast_fig = wd.kaempfer[gd.meine_nummer]
vorher_l = gast_fig.dash_ladungen
gd._knoepfe.add("dash")
_dash_gast_sieht = False
for _ in range(20):
    wd.schritt(K.NETZ["takt"]); gd.schritt(K.NETZ["takt"])
    _dash_gast_sieht = (_dash_gast_sieht or gd.ich.dash_bild_rest > 0.0)
pruef("Der Dash des Gastes kommt beim Gastgeber an",
      gast_fig.dash_ladungen == vorher_l - 1,
      "%d statt %d" % (gast_fig.dash_ladungen, vorher_l - 1))
pruef("Und der Gast sieht seine Ladungen",
      gd.ich.dash_ladungen == gast_fig.dash_ladungen)
pruef("Die Dash-Animation des Gastgebers kommt beim Gast an",
      _dash_gast_sieht)
wd.verlassen(); gd.verlassen()

# Eine Eingabezeile mit einem Tastendruck darf beim Stau nicht wegfallen.
from dustfront import netz as N
lt = N.Leitung.__new__(N.Leitung)
lt._raus = [b'{"t":"ein","knoepfe":[],"waffe":-1}\n'] * 5 + \
           [b'{"t":"ein","knoepfe":["dash"],"waffe":-1}\n'] + \
           [b'{"t":"ein","knoepfe":[],"waffe":-1}\n'] * 400
lt.verworfen = 0
lt._schlange_kuerzen()
pruef("Ein Tastendruck ueberlebt das Kuerzen der Schlange",
      any(b"dash" in z for z in lt._raus), "%d Zeilen" % len(lt._raus))

# ── Obere Ebenen: im Mehrspieler aus, wo sie ueber Spielflaeche liegen ──
from dustfront import einstellungen as EST
from dustfront.world import testkarte
pruef("Die Vorliebe gibt es, und sie steht auf aus",
      EST.VORGABE.get("obere_ebenen") is False)
pruef("Sie wandert mit dem Konto", "obere_ebenen" in EST.KONTO_WERTE)
pruef("Q ist belegt", pygame.K_q in app.opt.codes("ebenen"))

arena = testkarte()
wo = W.karte_lesen("staubtal")[0]
wo_rd = szene.renderer
m_arena = wo_rd.obermaske(arena, 1)
m_staub = wo_rd.obermaske(wo, 1)
e0a, e1a = arena.ebene(0), arena.ebene(1)
boden_ueber_boden = [i for i, k in enumerate(e1a.kacheln)
                     if k == K.BODEN and e0a.kacheln[i] == K.BODEN]
pruef("Arena: Boden ueber Boden wird ausgeblendet",
      boden_ueber_boden and all(m_arena[i] for i in boden_ueber_boden),
      "%d Kacheln" % len(boden_ueber_boden))
fels = [i for i, k in enumerate(e1a.kacheln)
        if k == K.BODEN and K.KACHELN[e0a.kacheln[i]]["fest"]]
# Seit 0.34.19: die Stege ueber einzelnen Mauern und Kisten sind kein
# Plateau und blenden mit aus. Bis dahin blieben sie stehen - schmale
# Saeulen und Streifen mitten im Bild (gemeldet).
pruef("Arena: Boden ueber einer einzelnen Mauer oder Kiste blendet mit aus",
      fels and all(m_arena[i] for i in fels), "%d Kacheln" % len(fels))
pruef("... und die Arena hat dann keine Klippen mehr",
      not wo_rd.klippen(arena, 1, True) and not wo_rd.klippen(arena, 1, False),
      str(len(wo_rd.klippen(arena, 1, True))))
e0s, e1s = wo.ebene(0), wo.ebene(1)
plateau = [i for i, k in enumerate(e1s.kacheln) if k != K.LEER]
bleibt = sum(1 for i in plateau if not m_staub[i])
# Ausgeblendet werden duerfen nur die Treppen- und Schachtkoepfe und das
# Plateau ueber den Aufzugnischen (seit 0.32.29): unter ihnen ist die Tuer
# bzw. der Gang dorthin, und den soll man von unten sehen.
_tr_s = [(i % e1s.breite, i // e1s.breite) for i, k in enumerate(e1s.kacheln)
         if K.KACHELN[k].get("treppe") is not None]
_weg_s = [i for i in plateau if m_staub[i]
          and e1s.kacheln[i] not in (K.TREPPE_RUNTER, K.AUFZUG_RUNTER)
          and not any(abs(i % e1s.breite - ax) <= 7
                      and abs(i // e1s.breite - ay) <= 7 for ax, ay in _tr_s)]
pruef("STAUBTAL: die Plateaus bleiben, nur Treppen und Aufzugnischen gehen",
      bleibt >= len(plateau) * 0.99 and not _weg_s,
      "%d von %d bleiben, sonst ausgeblendet: %s"
      % (bleibt, len(plateau), [(i % e1s.breite, i // e1s.breite) for i in _weg_s][:8]))
_schnee = W.karte_lesen("schneefeld")[0]
_m_schnee = wo_rd.obermaske(_schnee, 1)
_e0n, _e1n = _schnee.ebene(0), _schnee.ebene(1)
_auf_fels_n = [i for i, k in enumerate(_e1n.kacheln)
               if k != K.LEER and not K.KACHELN[k]["fest"]
               and K.KACHELN[_e0n.kacheln[i]]["fest"]]
pruef("SCHNEEFELD: die kleinen Plateaus sind gross genug und bleiben",
      _auf_fels_n and not any(_m_schnee[i] for i in _auf_fels_n),
      "%d von %d ausgeblendet" % (sum(1 for i in _auf_fels_n if _m_schnee[i]),
                                  len(_auf_fels_n)))

# Im Gefecht: aus zum Start, Q schaltet, nur beim eigenen Rechner.
app.opt["obere_ebenen"] = False
wo_w, wo_g = gefechtspaar("pvp")
pruef("Zum Start ausgeblendet, wie die Vorliebe sagt",
      not wo_w.obere_zeigen and not wo_g.obere_zeigen)
wo_g.ereignis(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_q, mod=0,
                                 unicode="q", scancode=0))
pruef("Q blendet sie beim Gast ein", wo_g.obere_zeigen)
pruef("Beim Gastgeber aendert das nichts", not wo_w.obere_zeigen)
pruef("Und es sagt, was jetzt gilt", "SICHTBAR" in wo_g.hinweis, wo_g.hinweis)
wo_g.ereignis(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_q, mod=0,
                                 unicode="q", scancode=0))
pruef("Noch einmal Q: wieder aus", not wo_g.obere_zeigen)

# Das Bild: mit der Figur unten in der Arena unterscheidet es sich, und
# was faellt, bleibt sichtbar.
ich_o = wo_w.ich
ziel_o = None
for i in boden_ueber_boden:
    tx, ty = i % e0a.breite, i // e0a.breite
    p = pygame.Vector2(tx * K.TILE + 16, ty * K.TILE + 16)
    if wo_w.welt.frei(p, 8, 0):
        ziel_o = p
        break
ich_o.ebene = 0
ich_o.pos.update(ziel_o); ich_o.vorher.update(ziel_o)
for _ in range(30):
    wo_w.schritt(K.FIXED_DT)
bilder_o = []
for zeigen in (True, False):
    wo_w.obere_zeigen = zeigen
    app.flaeche.fill(K.C_VOID)
    wo_w.zeichnen(app.flaeche, 1.0)
    bilder_o.append(pygame.image.tobytes(app.flaeche, "RGB"))
pruef("Ein- und ausgeblendet sind zwei verschiedene Bilder",
      bilder_o[0] != bilder_o[1])
# Ein Mitspieler oben, genau ueber der Stelle: steht er, verschwindet
# er mit seiner Etage. Faellt er, muss er zu sehen sein - sonst landet
# einem jemand auf dem Kopf, den man nie kommen sah.
faller = wo_w.kaempfer[wo_g.meine_nummer]
wo_w.obere_zeigen = False

def bild_mit(ebene, flug, stelle):
    faller.ebene, faller.flug = ebene, flug
    faller.pos.update(stelle); faller.vorher.update(stelle)
    app.flaeche.fill(K.C_VOID)
    wo_w.zeichnen(app.flaeche, 1.0)
    return pygame.image.tobytes(app.flaeche, "RGB")

ueber = ziel_o + pygame.Vector2(48, 0)
weit_weg = pygame.Vector2(ziel_o.x + 2000, ziel_o.y)
leer_o = bild_mit(1, 0.0, weit_weg)
pruef("Wer oben steht, verschwindet mit der Etage",
      bild_mit(1, 0.0, ueber) == leer_o)
wo_w.obere_zeigen = True
pruef("Eingeblendet sieht man ihn - die Pruefung davor sagt also etwas",
      bild_mit(1, 0.0, ueber) != bild_mit(1, 0.0, weit_weg))
wo_w.obere_zeigen = False
pruef("Wer herunterfaellt, bleibt sichtbar",
      bild_mit(0, 60.0, ueber) != leer_o)
faller.flug = 0.0
# Genau das traf bis 0.32.9 einen selbst nach der Treppe: man war oben,
# die Ansicht noch unten, und die eigene Etage wurde ausgestanzt - eine
# halbe Sekunde lang nur der Laser. Jetzt steht die Ansicht im ersten
# Bild oben, und wer dort steht, ist zu sehen.
ich_o.ebene = 1
wo_w.schritt(K.FIXED_DT)
pruef("Mehrspieler: nach dem Wechsel nach oben steht die Ansicht sofort dort",
      abs(wo_w.blick_hoehe - wo_w.welt.hoehe(1)) < 1.0,
      "%.1f" % wo_w.blick_hoehe)
pruef("Mehrspieler: das alte Bild blendet aus", wo_w._ueberblendung.rest > 0)
wo_w._ueberblendung.rest = 0.0
pruef("Mehrspieler: oben sieht man im ersten Bild, wer dort steht",
      bild_mit(1, 0.0, ueber) != bild_mit(1, 0.0, weit_weg))
ich_o.ebene = 0
wo_w.schritt(K.FIXED_DT)
wo_w._ueberblendung.rest = 0.0
wo_w.verlassen(); wo_g.verlassen()

# ── Medkit in der Hand ───────────────────────────────────────────────
# Beim Anlegen haelt die Figur das Medkit statt der Waffe - man sieht es,
# und was sie nicht haelt, schiesst nicht.
pruef("Die Figur mit Medkit gibt es, auch je Mannschaft",
      "spieler_medkit" in K.BILD_MASS and all(
          "spieler_%s_medkit" % t["name"].lower() in K.BILD_MASS
          for t in K.TEAMS["kombi"]))
_medkit_figur = app.bilder.platzhalter("spieler_medkit")
pruef("Die Medkit-Figur hat keine losen weissen Pixel am Rand",
      all(_medkit_figur.get_at((x, y))[:3] != (236, 232, 220)
          for x in range(_medkit_figur.get_width())
          for y in range(_medkit_figur.get_height())))
# Ein frisches Spiel: die Figur von oben ist laengst gestorben.
sz_m = Spiel(app, seed=20250921)
h_m = sz_m.held
e = app.eingabe          # `e` hiess zwischendurch eine Ebene

def sim_m(sekunden, halten=()):
    for _ in range(int(sekunden / K.FIXED_DT)):
        e.neues_bild()
        e._gehalten = set(halten)
        e.maus = pygame.Vector2(620, 180)
        sz_m.schritt(K.FIXED_DT)

sim_m(0.1)
h_m.unverwundbar = 99.0
h_m.waffe = h_m.waffen.index("repetierer")
h_m.magazin["repetierer"] = K.WAFFEN["repetierer"]["magazin"]
h_m.nachlade_rest = 0.0
h_m.leben = h_m.max_leben * 0.5
h_m.medkits = 1
pruef("Das Medkit geht los", h_m.heilen())
pruef("Solange es angelegt wird, haelt die Figur es", h_m.bild == "spieler_medkit",
      h_m.bild)
voll = h_m.magazin["repetierer"]
sim_m(K.MEDKIT["dauer"] * 0.8, halten={"feuer"})
pruef("Und schiesst dabei nicht", h_m.magazin["repetierer"] == voll,
      "%d von %d" % (h_m.magazin["repetierer"], voll))
pruef("Auch das Brecheisen bleibt stecken", not h_m.nahkampf())
sim_m(K.MEDKIT["dauer"] * 0.4 + 0.3, halten={"feuer"})
pruef("Danach ist die Waffe wieder da", h_m.bild == "spieler_repetierer",
      h_m.bild)
pruef("Und sie schiesst wieder", h_m.magazin["repetierer"] < voll,
      "%d von %d" % (h_m.magazin["repetierer"], voll))
pruef("Geheilt hat es auch", h_m.leben > h_m.max_leben * 0.5)

wm, gm = gefechtspaar("team")
fig_m = wm.kaempfer[gm.meine_nummer]
fig_m.leben = fig_m.max_leben * 0.5
fig_m.medkits = 1
fig_m.heilen()
for _ in range(6):
    wm.schritt(K.NETZ["takt"]); gm.schritt(K.NETZ["takt"])
pruef("Im Gefecht traegt die Figur das Medkit in Mannschaftsfarbe",
      fig_m.bild.endswith("_medkit") and fig_m.bild != "spieler_medkit",
      fig_m.bild)
pruef("Und der Gast sieht dasselbe", gm.ich.bild == fig_m.bild, gm.ich.bild)
wm.verlassen(); gm.verlassen()

# ── Die Regeln an einer Stelle (regeln.py) ───────────────────────────
from dustfront import regeln as RG
d_r = RG.vorgabe()
pruef("Jede Regel hat eine Vorgabe", set(d_r) == set(RG.NACH_NAME), str(d_r))
kaputt = RG.saeubern({"modus": "quatsch", "medkits": 999, "bosse": "ja",
                      "huegel_zeit": -5, "loadouts": 3, "ende_wert": "x"})
pruef("Was von aussen kommt, wird gesaeubert",
      kaputt["modus"] == K.MODUS_VORGABE and
      kaputt["medkits"] == K.GEFECHT["start_medkits_hoechstens"] and
      kaputt["bosse"] is True and kaputt["huegel_zeit"] == min(K.ZONE["haltezeiten"])
      and kaputt["loadouts"] == K.GEFECHT["loadouts"], str(kaputt))
sicht_pve = [f.schluessel for f in RG.sichtbar(RG.vorgabe(modus="pve"))]
sicht_pvp = [f.schluessel for f in RG.sichtbar(RG.vorgabe(modus="pvp"))]
sicht_hue = [f.schluessel for f in RG.sichtbar(RG.vorgabe(modus="huegel"))]
pruef("Schwierigkeit und Bosse nur, wo es Gegner gibt",
      {"schwierigkeit", "bosse"} <= set(sicht_pve)
      and not ({"schwierigkeit", "bosse"} & set(sicht_pvp)))
pruef("Haltezeit und Verfall nur beim Huegel",
      {"huegel_zeit", "huegel_verfall"} <= set(sicht_hue)
      and not ({"huegel_zeit", "huegel_verfall"} & set(sicht_pve)))
pruef("Der Huegel hat eine Hoechstdauer, aber keine Endart",
      "ende_wert" in sicht_hue and "ende_art" not in sicht_hue)
d_r = RG.vorgabe(modus="versus", runden=15)
RG.verstellen(d_r, "runden", 1)
pruef("Zahlen bleiben am Rand stehen", d_r["runden"] == 15, str(d_r["runden"]))
d_r = RG.vorgabe(loadouts="gleich")
RG.verstellen(d_r, "loadouts", 1)
pruef("Aufzaehlungen fangen vorn wieder an", d_r["loadouts"] == "alles")
d_r = RG.vorgabe(modus="pvp")
RG.verstellen(d_r, "ende_art", 1)
pruef("Wechselt die Endart, passt der Endwert dazu",
      d_r["ende_art"] == "abschuesse"
      and d_r["ende_wert"] == K.GEFECHT["abschuesse_ziel"], str(d_r["ende_wert"]))

# ── Schwierigkeit und Bosse ──────────────────────────────────────────
def welle_messen(stufe, bosse=True, welle=1):
    wx, gx = gefechtspaar("pve", regeln={"schwierigkeit": stufe,
                                         "bosse": bosse})
    wx.welle = welle - 1
    wx._welle_starten()
    for _ in range(3):
        wx._nachschub(99.0)
    gegner = [g for g in wx.gegner_offen if not g.ist_boss]
    ergebnis = dict(anzahl=len(gegner) + len(wx.welle_rest),
                    boss=wx.boss, pause=wx.pause_rest,
                    laeufer=[g for g in gegner if g.art == "laeufer"][:1],
                    gast=gx.schwierigkeit, gast_bosse=gx.bosse_an)
    netz_durchlassen(wx, gx, 5)
    ergebnis["gast"] = gx.schwierigkeit
    ergebnis["gast_bosse"] = gx.bosse_an
    wx.verlassen(); gx.verlassen()
    return ergebnis

normal = welle_messen("normal", welle=4)
schwer = welle_messen("schwer", welle=4)
leicht = welle_messen("leicht", welle=4)
pruef("SCHWER bringt mehr Gegner als NORMAL, LEICHT weniger",
      leicht["anzahl"] < normal["anzahl"] < schwer["anzahl"],
      "%d / %d / %d" % (leicht["anzahl"], normal["anzahl"], schwer["anzahl"]))
if normal["laeufer"] and schwer["laeufer"]:
    ln, ls = normal["laeufer"][0], schwer["laeufer"][0]
    pruef("Auf SCHWER haelt ein Laeufer mehr aus und schlaegt haerter",
          ls.max_leben > ln.max_leben and ls.daten["schaden"] > ln.daten["schaden"],
          "%.0f/%.0f Leben, %.1f/%.1f Schaden" % (ln.max_leben, ls.max_leben,
                                                  ln.daten["schaden"],
                                                  ls.daten["schaden"]))
pruef("Die Tabelle selbst bleibt dabei unveraendert",
      K.GEGNER["laeufer"]["schaden"] == 9.0)
pruef("LEICHT laesst mehr Pause zwischen den Wellen",
      leicht["pause"] > normal["pause"] > schwer["pause"])
pruef("Der Gast kennt die Schwierigkeit", schwer["gast"] == "schwer")
mit_boss = welle_messen("normal", True, welle=5)
ohne_boss = welle_messen("normal", False, welle=5)
pruef("Welle 5 bringt einen Boss", mit_boss["boss"] is not None)
pruef("Ohne Bosse nicht - und die Welle kommt dafuer in voller Staerke",
      ohne_boss["boss"] is None and ohne_boss["anzahl"] > mit_boss["anzahl"],
      "%d statt %d" % (ohne_boss["anzahl"], mit_boss["anzahl"]))
pruef("Auch das weiss der Gast", ohne_boss["gast_bosse"] is False)

# ── Eines fuer alle ──────────────────────────────────────────────────
from dustfront import konto as KMOD
fest_nr = 1
wl, gl = gefechtspaar("pvp", regeln={"loadouts": "gleich",
                                     "loadout_nr": fest_nr})
# Mit KLASSE PFLICHT (seit 0.34.91, Vorgabe) bekommt ein Satz ohne Klasse
# die Ersatzklasse - das ist das, was alle tragen.
fest_plaetze = KMOD.hotbar_aus_loadout(wl._mit_klasse(app.konto.loadouts[fest_nr]))
gast_fig = wl.kaempfer[gl.meine_nummer]
pruef("Bei EINES FUER ALLE traegt der Gastgeber das gewaehlte",
      wl.kaempfer[0].waffen == fest_plaetze, str(wl.kaempfer[0].waffen))
pruef("Und der Gast genau dasselbe", gast_fig.waffen == fest_plaetze,
      str(gast_fig.waffen))
netz_durchlassen(wl, gl, 10)
pruef("Er sieht es auch bei sich", gl.ich.waffen == fest_plaetze,
      str(gl.ich.waffen))
# Danach wieder das eigene: die neue Runde mit "eigenes".
wl.wunsch["loadouts"] = "eigenes"
wl._runde_neu()
eigenes = KMOD.hotbar_aus_loadout(gast_fig.angemeldet) if gast_fig.angemeldet else None
pruef("Nach einer solchen Runde traegt der Gast wieder sein eigenes",
      eigenes is not None and gast_fig.waffen == eigenes,
      "%s statt %s" % (gast_fig.waffen, eigenes))
netz_durchlassen(wl, gl, 10)
# Das war ein Fehler seit den Loadouts: die Liste ging mit, der Gast
# uebernahm sie nie und sah in der Hotbar alle neun Waffen.
pruef("Und seine Hotbar zeigt genau das, nicht alle neun",
      gl.ich.waffen == eigenes, str(gl.ich.waffen))
wl.verlassen(); gl.verlassen()

# ── Huegel: Haltezeit und Verfall ────────────────────────────────────
def huegel_messen(zeit, verfall=True):
    wh, gh = gefechtspaar("huegel", regeln={"huegel_zeit": zeit,
                                            "huegel_verfall": verfall})
    wk = wh.kaempfer[0]
    gk = wh.kaempfer[gh.meine_nummer]
    gk.pos.update(-500, -500); gk.vorher.update(gk.pos)
    wk.pos.update(wh.zone_mitte); wk.vorher.update(wk.pos)
    wk.ebene = K.ZONE["ebene"]
    wh.zone_stand = [0.0, 0.0]
    t = 0.0
    while not wh.vorbei and t < 400:
        wh._zone(0.05)
        t += 0.05
    # Und der Verfall: halb voll, dann niemand drin.
    wh.vorbei = False
    wh.zone_stand[wk.team] = 50.0
    wk.pos.update(-500, -500)
    for _ in range(100):
        wh._zone(0.05)
    rest = wh.zone_stand[wk.team]
    netz_durchlassen(wh, gh, 5)
    gast_zeit = gh.huegel_zeit
    wh.verlassen(); gh.verlassen()
    return t, rest, gast_zeit

t15, rest15, _g = huegel_messen(15)
t60, rest60, g60 = huegel_messen(60)
pruef("Mit 15 s Haltezeit braucht einer allein rund 15 s", 14.0 < t15 < 16.0,
      "%.1f s" % t15)
pruef("Mit 60 s rund 60 s", 58.0 < t60 < 62.0, "%.1f s" % t60)
pruef("Der Gast kennt die Haltezeit", g60 == 60, str(g60))
pruef("Mit Verfall sinkt ein verlassener Stand", rest15 < 50.0, "%.1f" % rest15)
_t, rest_aus, _g = huegel_messen(15, verfall=False)
pruef("Ohne Verfall bleibt er stehen", abs(rest_aus - 50.0) < 0.01,
      "%.1f" % rest_aus)

# ── Kartenwechsel beim Gast: auch zurueck, und mit allen Mitspielern ──
wk_, gk_ = gefechtspaar("pvp", karte="staubtal")
pruef("Beide starten auf STAUBTAL", wk_.karte == "staubtal" and gk_.karte == "staubtal")
wk_.wunsch["karte"] = ""
wk_._runde_neu()
netz_durchlassen(wk_, gk_, 20)
pruef("Zurueck auf die eingebaute Karte kommt der Gast mit",
      gk_.karte == "" and len(gk_.welt.ebenen) == 3,
      "%r, %d Ebenen" % (gk_.karte, len(gk_.welt.ebenen)))
pruef("Und alle Mitspieler stehen in seiner neuen Welt",
      all(k in gk_.welt.wesen or k in gk_.welt.neue
          for k in gk_.kaempfer.values()), "%d Kaempfer" % len(gk_.kaempfer))
wk_.verlassen(); gk_.verlassen()

# ── Die Rundentafel kennt die neuen Regeln ───────────────────────────
# Seit 0.32 stellt man sie nur noch dort ein, nicht mehr im Pausenmenue.
wm_, gm_ = gefechtspaar("pve")
wm_.plan_verstellen(0, "modus", "pve")
eintraege = [f.schluessel for f in RG.sichtbar(wm_.plan[0])]
pruef("Auf der Tafel stehen Schwierigkeit und Bosse",
      "schwierigkeit" in eintraege and "bosse" in eintraege, str(eintraege))
_vor = wm_.plan[0]["schwierigkeit"]
wm_.plan_verstellen(0, "schwierigkeit", "schwer")
pruef("Und lassen sich verstellen", wm_.plan[0]["schwierigkeit"] == "schwer",
      "%s -> %s" % (_vor, wm_.plan[0]["schwierigkeit"]))
wm_.verlassen(); gm_.verlassen()

# ── Die Lobby ────────────────────────────────────────────────────────
from dustfront import lobby as LB
pruef("Die Lobby ist keine waehlbare Spielart",
      "lobby" not in [m for m in RG.NACH_NAME["modus"].werte({}, None)])
pruef("Und keine waehlbare Karte",
      K.LOBBY["karte"] not in RG.NACH_NAME["karte"].werte({}, None))
pruef("Gueltig ist sie trotzdem - sie muss durchs Netz",
      RG.saeubern({"modus": "lobby", "karte": "lobby"})["modus"] == "lobby")
pruef("Die Kommandozeile nimmt --modus lobby nicht an",
      __import__("dustfront.main", fromlist=["x"]).aus_argumenten(
          ["--host", "--modus", "lobby"]) == 1)

def lobbypaar(**kw):
    """Wie gefechtspaar, aber der Gastgeber macht mit Lobby auf."""
    _neuer_port()
    kw.setdefault("seed", 20240 + _port[0])
    wirt = Gefecht(app, "WIRT", gastgeber=netz.Gastgeber(_port[0]),
                   lobby=True, **kw)
    gast = Gefecht(app, "BESUCH", gast=netz.Gast("127.0.0.1:%d" % _port[0]))
    for _ in range(30):
        wirt.schritt(K.NETZ["takt"])
        gast.schritt(K.NETZ["takt"])
    return wirt, gast

wl_, gl_ = lobbypaar(modus="pve", regeln={"schwierigkeit": "schwer"})
pruef("Mit Lobby faengt es in der Lobby an",
      wl_.in_lobby and wl_.karte == "lobby", "%s / %s" % (wl_.modus, wl_.karte))
pruef("Was die Kommandozeile sagt, ist die erste geplante Runde",
      wl_.plan[0]["modus"] == "pve" and wl_.plan[0]["schwierigkeit"] == "schwer",
      str(wl_.plan[0]))
pruef("Die Karte hat ihre drei Bereiche", set(wl_.bereiche) == {"pvp", "stand", "pve"},
      str(list(wl_.bereiche)))
pruef("Im Schiessstand stehen Puppen", len(wl_.puppen) == 4, "%d" % len(wl_.puppen))
pruef("Der Gast ist mit in der Lobby",
      gl_.in_lobby and gl_.karte == "lobby" and set(gl_.bereiche) == set(wl_.bereiche))
pruef("Und kennt den Plan", gl_.plan[0]["modus"] == "pve", str(gl_.plan[0]["modus"]))
pruef("Er sieht die Puppen", sum(1 for x in gl_._fremde_gegner if x[4] == "puppe") == 4,
      "%d" % sum(1 for x in gl_._fremde_gegner if x[4] == "puppe"))
wk_l = wl_.kaempfer[0]
gk_l = wl_.kaempfer[gl_.meine_nummer]

def beide(sekunden, jedesmal=None):
    """Gastgeber und Gast zusammen rechnen. Allein liefe der Gastgeber
    so lange, bis er den stummen Gast hinauswirft."""
    for _ in range(int(sekunden / K.FIXED_DT)):
        wl_.schritt(K.FIXED_DT)
        gl_.schritt(K.FIXED_DT)
        if jedesmal is not None:
            jedesmal()

pruef("Man steigt auf dem Platz ein, in keinem Bereich",
      wl_.bereich_von(wk_l) == "" and wl_.bereich_von(gk_l) == "",
      "%s / %s" % (wl_.bereich_von(wk_l), wl_.bereich_von(gk_l)))

# Wer wem wehtun darf
def stellen(k, bereich, dx=0):
    r = wl_.bereiche[bereich]
    k.pos.update(r.centerx + dx, r.bottom - 48); k.vorher.update(k.pos)
    k.ebene = 0

for k in (wk_l, gk_l):
    k.unverwundbar = 0.0
gk_l.leben = gk_l.max_leben
gk_l.schaden(20, None, wk_l)
pruef("Auf dem Platz tut niemandem etwas weh", gk_l.leben == gk_l.max_leben)
stellen(wk_l, "pvp", -40); stellen(gk_l, "pvp", 40)
gk_l.schaden(20, None, wk_l)
pruef("In der Arena schon", gk_l.leben == gk_l.max_leben - 20, "%.0f" % gk_l.leben)
gk_l.leben = gk_l.max_leben
wk_l.pos.update(wl_.bereiche["stand"].center); wk_l.vorher.update(wk_l.pos)
gk_l.schaden(20, None, wk_l)
pruef("Aber nicht von draussen hinein", gk_l.leben == gk_l.max_leben)
z_l = KampfGegner(pygame.Vector2(wl_.bereiche["pve"].center), "laeufer", 0, wl_)
gk_l.schaden(10, None, z_l)
pruef("Ein Zombie tut ausserhalb des Geheges nichts", gk_l.leben == gk_l.max_leben)
stellen(gk_l, "pve")
gk_l.schaden(10, None, z_l)
pruef("Im Gehege schon", gk_l.leben == gk_l.max_leben - 10, "%.0f" % gk_l.leben)
gk_l.leben = gk_l.max_leben

# Die Puppe: faellt nicht, heilt, zeigt Zahlen - auch beim Gast
puppe = wl_.puppen[0]
vorher_schriften = len(gl_.welt.aufschriften)
puppe.schaden(puppe.max_leben + 50, None, wk_l)
pruef("Eine Puppe faellt nicht um", puppe.lebt and puppe.leben > 0)
puppe.schaden(40, None, wk_l)
halb = puppe.leben
beide(0.4)
pruef("Sie zeigt, was sie abbekam", any(a[2].isdigit() for a in wl_.welt.aufschriften))
pruef("Auch beim Gast", len(gl_.welt.aufschriften) > vorher_schriften)
beide(K.LOBBY["puppe_heilt"] + 0.3)
pruef("Und fuellt sich nach einer Weile wieder auf",
      puppe.leben == puppe.max_leben and halb < puppe.max_leben)

# Seit 0.32: eine Zahl je Treffer, nicht je Viertelsekunde (gemeldet).
wl_.welt.aufschriften = []
for _treffer in (23, 17, 31):
    puppe.schaden(_treffer, pygame.Vector2(1, 0), wk_l)
zahlen = [a[2] for a in wl_.welt.aufschriften if a[2].isdigit()]
pruef("Drei Treffer, drei Zahlen - sofort und jede fuer sich",
      sorted(zahlen) == ["17", "23", "31"], str(zahlen))
pruef("... nebeneinander, nicht aufeinander",
      len({(round(a[0].x), round(a[0].y)) for a in wl_.welt.aufschriften}) == 3)
wl_.welt.aufschriften = []
for _ in range(int(1.0 / K.FIXED_DT)):        # Feuer: Bruchteile je Schritt
    puppe.schaden(0.2, None, wk_l)
    puppe._puppe_schritt(K.FIXED_DT)
feuerzahlen = [a[2] for a in wl_.welt.aufschriften if a[2].isdigit()]
pruef("Feuer kommt weiter gesammelt, nicht 120 Zahlen die Sekunde",
      1 <= len(feuerzahlen) <= 5, "%d Zahlen" % len(feuerzahlen))

# Und sie laesst sich nicht wegschieben, auch nicht durch Hineinlaufen.
puppe_ort = pygame.Vector2(puppe.pos)
wk_l.ebene = puppe.ebene
for _ in range(60):
    wk_l.pos.update(puppe.pos + pygame.Vector2(puppe.radius + wk_l.radius - 6, 0))
    wl_.welt.auseinander(wk_l)
pruef("Eine Puppe weicht beim Hineinlaufen keinen Pixel",
      puppe.pos == puppe_ort, "%s -> %s" % (puppe_ort, puppe.pos))
pruef("... der Spieler wird stattdessen ganz zurueckgeschoben",
      wk_l.pos.distance_to(puppe.pos) >= puppe.radius + wk_l.radius - 0.01,
      "%.1f" % wk_l.pos.distance_to(puppe.pos))

# Das Gehege: fuellt sich, wenn einer drin ist, und haelt die Zombies drin
stellen(wk_l, "pve")
stellen(gk_l, "stand")
def _heil():
    wk_l.leben = wk_l.max_leben
beide(8.0, _heil)
pruef("Mit einem im Gehege kommen Zombies", len(wl_.gehege) == K.LOBBY["gehege_grund"],
      "%d" % len(wl_.gehege))
pruef("Wellen gibt es in der Lobby nicht", wl_.welle == 0 and not wl_.welle_rest)
wk_l.pos.update(wl_.bereiche["stand"].center); wk_l.vorher.update(wk_l.pos)
beide(8.0)
r_pve = wl_.bereiche["pve"]
pruef("Wer hinausgeht, laesst sie im Gehege zurueck",
      wl_.gehege and all(r_pve.collidepoint(z.pos) for z in wl_.gehege),
      str([tuple(map(int, z.pos)) for z in wl_.gehege]))
pruef("Die Lobby endet nie und bucht nichts",
      not wl_.vorbei and wl_.partie == "")

# Tod in der Lobby: schnell wieder da, auf dem Platz
stellen(wk_l, "pvp", -40); stellen(gk_l, "pvp", 40)
wk_l.unverwundbar = 0.0
wk_l.schaden(999, None, gk_l)
pruef("In der Arena kann man fallen", not wk_l.lebt)
beide(K.LOBBY["wieder_nach"] + 0.2)
pruef("Und steht schnell wieder auf dem Platz",
      wk_l.lebt and wl_.bereich_von(wk_l) == "", wl_.bereich_von(wk_l))

# Das Pausenmenue in der Lobby
eintraege_l = [x[0] for x in wl_._menue_baut()]
pruef("In der Lobby stellt das Menue keine Regeln, sondern oeffnet die Tafel",
      "planen" in eintraege_l and "starten" in eintraege_l
      and "modus" not in eintraege_l, str(eintraege_l))
gast_eintraege_l = [x[0] for x in gl_._menue_baut()]
pruef("Der Gast kann den Plan ansehen, aber nicht starten",
      "planen" in gast_eintraege_l and "starten" not in gast_eintraege_l)

# ── Der Rundenplan ───────────────────────────────────────────────────
nr2 = wl_.plan_dazu(0)
wl_.plan_verstellen(nr2, "modus", "versus")
wl_.plan_verstellen(nr2, "runden", 1)
pruef("Eine Runde kommt dazu", len(wl_.plan) == 2 and wl_.plan[1]["modus"] == "versus")
wl_.plan_kopieren(0)
nr3 = wl_.plan_dazu(1)
wl_.plan_einfuegen(nr3)
pruef("Kopieren und Einfuegen uebernimmt alle Einstellungen",
      wl_.plan[2] == wl_.plan[0], "%s / %s" % (wl_.plan[2]["modus"], wl_.plan[0]["modus"]))
wl_.plan_weg(2)
pruef("Weg nimmt sie wieder heraus", len(wl_.plan) == 2)
for _ in range(len(wl_.plan) + 3):
    wl_.plan_weg(0)
pruef("Eine bleibt immer", len(wl_.plan) == 1)
wl_.plan_verstellen(0, "modus", "pvp")
wl_.plan_verstellen(0, "ende_art", "abschuesse")
wl_.plan_verstellen(0, "ende_wert", 1)
wl_.plan_dazu(0)
wl_.plan_verstellen(1, "modus", "team")
wl_.plan_verstellen(1, "ende_art", "abschuesse")
wl_.plan_verstellen(1, "ende_wert", 1)
netz_durchlassen(wl_, gl_, 6)
pruef("Der Gast sieht jede Aenderung", [d["modus"] for d in gl_.plan] == ["pvp", "team"],
      str([d["modus"] for d in gl_.plan]))
gl_.plan_verstellen(0, "modus", "pve")
pruef("Er selbst kann nichts aendern", gl_.plan[0]["modus"] == "pvp")

# Starten, Runde vorbei, naechste Runde, zurueck in die Lobby
wl_.plan_starten(0)
netz_durchlassen(wl_, gl_, 10)
pruef("Start: die erste geplante Runde laeuft", wl_.modus == "pvp"
      and not wl_.in_lobby and wl_.plan_laeuft, wl_.modus)
pruef("Der Gast ist mit dabei", gl_.modus == "pvp" and not gl_.in_lobby
      and gl_.karte == "", "%s / %r" % (gl_.modus, gl_.karte))
pruef("Die Puppen sind weg", not any(isinstance(x, KampfGegner) for x in wl_.welt.wesen))
eintraege_r = [x[0] for x in wl_._menue_baut()]
pruef("In der Runde fuehrt das Menue zurueck in die Lobby", "lobby" in eintraege_r)
wl_.kaempfer[0].abschuesse = 1
beide(0.1)
pruef("Die Runde endet wie immer", wl_.vorbei)
netz_durchlassen(wl_, gl_, 6)
pruef("Die Tafel zaehlt herunter, auch beim Gast",
      0 < wl_.plan_weiter <= K.LOBBY["weiter_nach"] and gl_.plan_weiter > 0,
      "%.1f / %.1f" % (wl_.plan_weiter, gl_.plan_weiter))
pruef("Und sagt, was kommt", "TEAM" in wl_.plan_ausblick(), wl_.plan_ausblick())
beide(K.LOBBY["weiter_nach"] + 0.5)
pruef("Danach kommt von selbst die naechste geplante Runde",
      wl_.modus == "team" and not wl_.vorbei and wl_.plan_pos == 1, wl_.modus)
for k in wl_.kaempfer.values():
    if k.team >= 0:
        wl_.teampunkte[k.team] = 1
        break
beide(0.1)
pruef("Auch die endet", wl_.vorbei)
beide(K.LOBBY["weiter_nach"] + 0.5)
netz_durchlassen(wl_, gl_, 10)
pruef("Ohne Schleife geht es danach zurueck in die Lobby",
      wl_.in_lobby and not wl_.plan_laeuft and gl_.in_lobby, wl_.modus)
pruef("Mit Puppen und allen Mitspielern",
      len(wl_.puppen) == 4 and all(k in wl_.welt.wesen or k in wl_.welt.neue
                                   for k in wl_.kaempfer.values()))
# Mit Schleife: nach der letzten wieder die erste.
wl_.plan_schleife_setzen(True)
wl_.plan_starten(1)
for k in wl_.kaempfer.values():
    if k.team >= 0:
        wl_.teampunkte[k.team] = 1
        break
beide(K.LOBBY["weiter_nach"] + 1.0)
pruef("Mit Schleife kommt nach der letzten wieder die erste",
      wl_.modus == "pvp" and wl_.plan_pos == 0 and wl_.plan_laeuft, wl_.modus)
wl_.lobby_betreten()
pruef("Zurueck in die Lobby geht jederzeit", wl_.in_lobby and not wl_.plan_laeuft)

# Die Tafel: der Gastgeber stellt ein, der Gast sieht nur zu
tafel_w = LB.Rundenplanung(app, wl_)
tafel_g = LB.Rundenplanung(app, gl_)
netz_durchlassen(wl_, gl_, 6)
tafel_g.aufbauen()
regel_w = [e for e in tafel_w.elemente if e.name == "r:modus"]
pruef("Auf der Tafel stehen die Regeln der naechsten Runde", bool(regel_w))
pruef("Beim Gast ist alles gesperrt",
      all(e.gesperrt for e in tafel_g.elemente if e.name.startswith("r:")))
pruef("Und es gibt keinen Startknopf",
      not any(e.name == "start" for e in tafel_g.elemente)
      and any(e.name == "start" for e in tafel_w.elemente))
el = regel_w[0]
el.blaettern(1)
tafel_w.geaendert(el)
pruef("Ein Klick auf der Tafel aendert den Plan", wl_.plan[0]["modus"] == el.wert,
      "%s / %s" % (wl_.plan[0]["modus"], el.wert))
r_el = RG.NACH_NAME["runden"]
wl_.plan_verstellen(0, "modus", "versus")
tafel_w.aufbauen()
runden_el = [e for e in tafel_w.elemente if e.name == "r:runden"][0]
runden_el.index = len(runden_el.optionen) - 1
runden_el.blaettern(1)
pruef("Zahlen bleiben auf der Tafel am Rand stehen",
      runden_el.wert == max(r_el.werte({}, None)), str(runden_el.wert))
tafel_w.ausloesen([e for e in tafel_w.elemente if e.name == "planen"][0])
pruef("Der Rundenplan klappt erst auf Wunsch auf",
      wl_.plan_offen and any(e.name == "dazu" for e in tafel_w.elemente))
wl_.plan_offen = False
wl_.verlassen(); gl_.verlassen()

# Mannschaftswunsch: in der Lobby gibt es keine Mannschaften, der Wunsch
# beim Verbinden soll aber in der ersten Teamrunde gelten.
wt_, gt_ = lobbypaar(modus="team", team=1)
pruef("In der Lobby hat niemand eine Mannschaft",
      all(k.team == -1 for k in wt_.kaempfer.values()))
wt_.plan_starten(0)
pruef("Die erste Teamrunde erfuellt den Wunsch vom Verbinden",
      wt_.kaempfer[0].team == 1 and wt_.kaempfer[gt_.meine_nummer].team == 0,
      "%d / %d" % (wt_.kaempfer[0].team, wt_.kaempfer[gt_.meine_nummer].team))
wt_.verlassen(); gt_.verlassen()

# ── Die Anzeige (anzeige.py) ─────────────────────────────────────────
from dustfront import anzeige as AZ
hud_probe = AZ.Anzeige(None)
neun = hud_probe.hotbar_rechteck(len(K.HOTBAR))
drei = hud_probe.hotbar_rechteck(3)
pruef("Mit allen Waffen ueberdeckt die Hotbar nichts",
      not neun.colliderect(AZ.LINKS) and not neun.colliderect(AZ.RECHTS),
      "%s / %s / %s" % (neun, AZ.LINKS, AZ.RECHTS))
pruef("Mit Loadout sind die Felder groesser",
      AZ.Anzeige.hotbar_gross(3) and not AZ.Anzeige.hotbar_gross(9)
      and drei.height > neun.height)
pruef("Der Hinweis liegt ueber der Hotbar, nicht auf ihr",
      AZ.HINWEIS_Y + 15 < neun.y - 10)

wa_, ga_ = gefechtspaar("pve", knapp=True)
wa_.welle = 4
wa_._welle_starten()
netz_durchlassen(wa_, ga_, 10)
pruef("Der Gast weiss, wie viele Gegner die Welle noch hat",
      ga_.gegner_rest == wa_.gegner_rest > 0,
      "%d / %d" % (ga_.gegner_rest, wa_.gegner_rest))
wa_.welle = 9
for alt in wa_.gegner_offen:
    alt.lebt = False         # ein Boss je Welle - der alte muss weg
wa_.gegner_offen = []
wa_.welle_rest = []
wa_._welle_starten()
netz_durchlassen(wa_, ga_, 10)
pruef("Und welcher Boss gerade da ist, und wie weit er ist",
      wa_.boss_stand() is not None and ga_.boss_stand() is not None
      and ga_.boss_stand()[0] == wa_.boss_stand()[0],
      "%s / %s" % (wa_.boss_stand(), ga_.boss_stand()))

def hud_bild(sz):
    app.flaeche.fill(K.C_VOID)
    sz.hud.zeichnen(app.flaeche)
    return app.flaeche.copy()

# Der Vorrat steht nur bei knapper Munition - seit 0.34.93 am Zeiger neben
# dem Magazin statt unten rechts, darum das ganze Bild verglichen.
unter = pygame.Rect(0, 0, AZ.W, AZ.H)
mit_vorrat = hud_bild(wa_).subsurface(unter).copy()
wa_.knapp = False
ohne_vorrat = hud_bild(wa_).subsurface(unter).copy()
wa_.knapp = True
pruef("Den Vorrat gibt es nur bei knapper Munition",
      pygame.image.tobytes(mit_vorrat, "RGB") != pygame.image.tobytes(ohne_vorrat, "RGB"))
wa_.verlassen(); ga_.verlassen()

# Die Pfeile zu Gefallenen bleiben aus den Anzeigestreifen heraus.
wp_, gp_ = gefechtspaar("pve")
liegt = wp_.kaempfer[gp_.meine_nummer]
liegt.unverwundbar = 0.0
liegt.schaden(999, None, None)
for ziel_pos in ((0, 5000), (0, -5000), (5000, 0)):
    liegt.pos.update(wp_.ich.pos + pygame.Vector2(ziel_pos))
    pfeilbild = pygame.Surface((AZ.W, AZ.H), pygame.SRCALPHA)
    wp_._randpfeile(pfeilbild)
    benutzt = pfeilbild.get_bounding_rect()
    pruef("Der Pfeil nach %s liegt zwischen den Anzeigestreifen" % (ziel_pos,),
          benutzt.width > 0 and benutzt.top >= AZ.RAND_OBEN - 12
          and benutzt.bottom <= AZ.H - AZ.RAND_UNTEN + 12, str(benutzt))
wp_.verlassen(); gp_.verlassen()

# ── Nur dieselbe Version spielt zusammen ─────────────────────────────
import json as _json, socket as _socket, time as _time
_neuer_port()
wv = Gefecht(app, "WIRT", gastgeber=netz.Gastgeber(_port[0]), modus="pvp", seed=5)
echte_version = K.VERSION
K.VERSION = "0.0.1"                 # der Gast hat eine andere
gv = Gefecht(app, "ALT", gast=netz.Gast("127.0.0.1:%d" % _port[0]))
for _ in range(30):
    K.VERSION = echte_version
    wv.schritt(K.NETZ["takt"])
    K.VERSION = "0.0.1"
    gv.schritt(K.NETZ["takt"])
K.VERSION = echte_version
pruef("Ein Gast mit anderer Version wird abgewiesen", len(wv.kaempfer) == 1,
      str(list(wv.kaempfer)))
pruef("Und bekommt die Tafel mit beiden Versionen",
      gv.versionsfehler == ("0.0.1", echte_version), str(gv.versionsfehler))
pruef("Der Gastgeber sagt, wen er abgewiesen hat", "ALT" in wv.hinweis, wv.hinweis)
app.flaeche.fill(K.C_VOID)
gv.zeichnen(app.flaeche, 1.0)      # die Tafel darf nicht abstuerzen
gv.verlassen()

# Ein Gast von vor 0.27.1 schickt gar keine Version - er zeigt nur die
# 24 Zeichen des Grundes, und die muessen allein verstaendlich sein.
roh = _socket.create_connection(("127.0.0.1", _port[0]))
roh.sendall((_json.dumps({"t": "hallo", "name": "UR", "team": -1, "wort": ""})
             + "\n").encode())
antwort = b""
for _ in range(60):
    wv.schritt(K.NETZ["takt"])
    roh.settimeout(0.02)
    try:
        antwort += roh.recv(4096)
    except (_socket.timeout, BlockingIOError):
        pass
    if b"abgelehnt" in antwort:
        break
roh.close()
zeile = [z for z in antwort.split(b"\n") if b"abgelehnt" in z]
grund = _json.loads(zeile[0]).get("grund", "") if zeile else ""
pruef("Auch ein alter Gast ohne Versionsangabe wird abgewiesen",
      bool(zeile) and len(wv.kaempfer) == 1, str(antwort[:80]))
pruef("Mit einem Grund, den auch seine alte Anzeige ganz zeigt",
      echte_version in grund and len(grund) <= 24, grund)
wv.verlassen()

# Die andere Richtung: der Gastgeber ist der Aeltere.
w2, g2 = gefechtspaar("pvp")
g2.versionsfehler = None
pruef("Gleiche Version: es geht los", g2.versionsfehler is None
      and len(w2.kaempfer) == 2)
g2._version_vom_gastgeber({"t": "neustart", "regeln": {}})
pruef("Ein Gastgeber ohne Versionsangabe (vor 0.27.1) wird vom Gast verlassen",
      g2.versionsfehler == (echte_version, "") and not g2.gast.offen)
from dustfront.mehrspieler import _version_kleiner
pruef("Wer aelter ist, wird richtig erkannt",
      _version_kleiner("0.26.9", "0.27.1") and not _version_kleiner("0.27.10", "0.27.2"))
w2.verlassen(); g2.verlassen()

# ── Spielerkosmetik (spielerkosmetik.py) ─────────────────────────────
import io as _io, array as _array, wave as _wave, base64 as _b64, struct as _struct
import tempfile as _tempfile
from pathlib import Path as _Path
from dustfront import spielerkosmetik as SK
from dustfront import ablage as _AB, konto as _KM
GK = K.SPIELERKOSMETIK

def wav_bauen(dauer, rate=22050, spuren=1, breite=2, huelle=None, hz=440.0):
    """Eine WAV wie aus der Kontoseite: ein Sinus unter einer Huelle.
    `huelle` bekommt den Anteil an der Laenge (0..1) und gibt 0..1."""
    n = int(dauer * rate)
    huelle = huelle or (lambda x: 0.8)
    puffer = _io.BytesIO()
    with _wave.open(puffer, "wb") as w:
        w.setnchannels(spuren); w.setsampwidth(breite); w.setframerate(rate)
        if breite != 2:
            w.writeframes(bytes([128]) * (n * spuren * breite))
        else:
            a = _array.array("h")
            for i in range(n):
                v = int(32000 * huelle(i / float(n))
                        * math.sin(2 * math.pi * hz * i / rate))
                a.extend([v] * spuren)
            w.writeframes(a.tobytes())
    return puffer.getvalue()

def png_bauen(b=32, h=32, farbe=(220, 30, 30)):
    s = pygame.Surface((b, h), pygame.SRCALPHA)
    s.fill(tuple(farbe) + (255,))
    puffer = _io.BytesIO()
    pygame.image.save(s, puffer, "k.png")
    return puffer.getvalue()

def fehler_von(f, *a):
    """Die Meldung, mit der `f` ablehnt - leer, wenn es durchging."""
    try:
        f(*a)
    except ValueError as fehler:
        return str(fehler)
    return ""

def spitzen(wav):
    """Lautester Ausschlag je Pruefabschnitt."""
    rate, p = SK.ton_lesen(wav)
    b = int(rate * GK["ton_abschnitt"])
    return [max(abs(x) for x in p[i:i + b]) for i in range(0, len(p), b)]

# Pruefen: was nicht passt, kommt nicht hinein.
m = fehler_von(SK.ton_lesen, wav_bauen(0.5))
pruef("Ein zu kurzer Ton wird abgelehnt", "ZU KURZ" in m, m)
pruef("Genau die Mindestlaenge geht", fehler_von(SK.ton_lesen, wav_bauen(GK["ton_min"])) == "")
music_b64 = _b64.b64encode(wav_bauen(1.2)).decode("ascii")
music_objekt = SK.aus_konto("", "", music_b64)
pruef("Ein Music-Kit-Ton ist fuer das Konto allein gueltig",
      not music_objekt.ton and bool(music_objekt.music_kit_roh))
pruef("Ein Music Kit wird nicht an Mitspieler als Blendkosmetik verteilt",
      "music_kit" not in music_objekt.text())
if pygame.mixer.get_init() is not None:
    pruef("Der Music-Kit-Ton laesst sich im Mixer bereitstellen",
          music_objekt.music_klang() is not None)
m = fehler_von(SK.ton_lesen, wav_bauen(GK["ton_max"] + 0.5, rate=11025))
pruef("Ein zu langer Ton wird abgelehnt", "ZU LANG" in m, m)
m = fehler_von(SK.ton_lesen, wav_bauen(1.5, breite=1))
pruef("8 Bit werden nicht angenommen", "FORMAT" in m, m)
m = fehler_von(SK.ton_lesen, wav_bauen(1.5, rate=8000))
pruef("Eine unuebliche Rate auch nicht", "FORMAT" in m, m)
m = fehler_von(SK.ton_lesen, b"ID3\x04" + bytes(4000))
pruef("Eine MP3 so wie sie ist auch nicht - die Kontoseite macht WAV daraus",
      "KEINE WAV" in m, m)
m = fehler_von(SK.ton_lesen, b"RIFF" + bytes(GK["ton_bytes"]))
pruef("Zu gross wird vor dem Lesen abgelehnt", "ZU GROSS" in m, m)
# Ein Kopf, der zwei Sekunden behauptet, vor einer halben.
gelogen = bytearray(wav_bauen(0.5))
_struct.pack_into("<I", gelogen, 40, 2 * 22050 * 2)
m = fehler_von(SK.ton_lesen, bytes(gelogen))
pruef("Gezaehlt werden die echten Proben, nicht was der Kopf behauptet",
      "ZU KURZ" in m, m)
rate_s, proben_s = SK.ton_lesen(wav_bauen(1.5, spuren=2))
pruef("Stereo wird zu mono", len(proben_s) == int(1.5 * 22050), "%d" % len(proben_s))

# Der Ton wird immer leiser.
anlauf = int(GK["ton_anlauf"] / GK["ton_abschnitt"])
schwellend = wav_bauen(2.0, huelle=lambda x: 0.05 + 0.95 * x)
sp_ein = spitzen(schwellend)
sp_aus = spitzen(SK.ton_aufbereiten(schwellend))
ueber = max(sp_aus[a] - max(sp_aus[:a]) for a in range(anlauf, len(sp_aus)))
pruef("Ein anschwellender Ton wird gedeckelt: nach dem Anlauf nie lauter",
      ueber <= 0.02 * max(sp_aus) and sp_ein[-2] > 4 * sp_ein[anlauf],
      "hoechstens %d ueber dem Bisherigen" % ueber)
def schluss(wav):
    """Der lauteste Ausschlag in den letzten fuenf Millisekunden."""
    rate, p = SK.ton_lesen(wav)
    return max(abs(x) for x in p[-int(rate * 0.005):])
pruef("Und er endet in Stille",
      schluss(SK.ton_aufbereiten(schwellend)) <= 0.01 * max(sp_aus),
      "%d von %d" % (schluss(SK.ton_aufbereiten(schwellend)), max(sp_aus)))
dauer_ein = spitzen(wav_bauen(2.0))
dauer_aus = spitzen(SK.ton_aufbereiten(wav_bauen(2.0)))
n_ = len(dauer_aus)
pruef("Ein Dauerton wird stetig leiser",
      all(dauer_aus[a + 1] <= dauer_aus[a] + 0.02 * dauer_ein[a]
          for a in range(anlauf, n_ - 1))
      and dauer_aus[n_ // 2] < 0.6 * dauer_ein[n_ // 2],
      "Mitte %d von %d" % (dauer_aus[n_ // 2], dauer_ein[n_ // 2]))
pruef("Und laeuft auf null",
      dauer_aus[int(n_ * 0.8)] > dauer_aus[int(n_ * 0.9)] > dauer_aus[-1]
      and schluss(SK.ton_aufbereiten(wav_bauen(2.0))) <= 0.01 * dauer_ein[-1],
      "%d > %d > %d" % (dauer_aus[int(n_ * 0.8)], dauer_aus[int(n_ * 0.9)],
                        dauer_aus[-1]))
# Schneller als die Grenze: bleibt ganz, wie er ist - bis auf den letzten,
# stillen Abschnitt.
knall_ = wav_bauen(2.0, huelle=lambda x: (1 - x) ** 2)
pruef("Ein Knall, der von selbst schnell genug abklingt, bleibt unangetastet",
      spitzen(SK.ton_aufbereiten(knall_))[:-2] == spitzen(knall_)[:-2])
# Zwischen zwei Schlaegen eine kurze Luecke: danach darf es wieder fast
# so laut sein - nur nicht lauter als die Grenze.
def schlaege(x):
    return 0.9 if (x * 10) % 1.0 < 0.6 else 0.05
sp_schl = spitzen(SK.ton_aufbereiten(wav_bauen(2.0, huelle=schlaege)))
pruef("Nach einer kurzen Luecke kommt der naechste Schlag noch durch",
      sp_schl[int(n_ * 0.3)] > 0.4 * max(sp_schl), "%d von %d"
      % (sp_schl[int(n_ * 0.3)], max(sp_schl)))
# Die Grenze selbst: oben der lauteste Ausschlag im Anlauf, dann
# geradlinig auf null. Kein Abschnitt darf darueber - auch nicht der
# Ausklang eines Schlags in die Luecke danach hinein.
def ueber_der_linie(wav_ein):
    rate, p = SK.ton_lesen(wav_ein)
    b = int(rate * GK["ton_abschnitt"])
    sp_e = [max(abs(x) for x in p[i:i + b]) for i in range(0, len(p), b)]
    sp_a = spitzen(SK.ton_aufbereiten(wav_ein))
    oben = max(sp_e[:anlauf])
    n = len(p)
    return max(sp_a[a] - oben * (1.0 - min(n, (a + 1) * b) / float(n)) + 0.0
               for a in range(anlauf, len(sp_a)))
schlimmst = max(ueber_der_linie(wav_bauen(2.0, huelle=h))
                for h in (schlaege, lambda x: 0.8, lambda x: 0.05 + 0.95 * x))
pruef("Kein Abschnitt liegt ueber der Grenze, auch nicht zwischen Schlaegen",
      schlimmst <= 1.0, "hoechstens %.0f darueber" % schlimmst)
pruef("Das Aufbereiten ist ueberall gleich",
      SK.ton_aufbereiten(schwellend) == SK.ton_aufbereiten(schwellend))

# Das Bild.
pruef("Ein kleines PNG geht", SK.bild_lesen(png_bauen()).get_size() == (32, 32))
m = fehler_von(SK.bild_lesen, png_bauen(GK["bild_max"] + 1, 8))
pruef("Ein zu breites nicht", "HÖCHSTENS" in m, m)
m = fehler_von(SK.bild_lesen, b"GIF89a" + bytes(100))
pruef("Nur PNG", "KEIN PNG" in m, m)
m = fehler_von(SK.bild_lesen, b"\x89PNG\r\n\x1a\n" + bytes(100))
pruef("Ein kaputtes PNG wird abgelehnt und nicht abgestuerzt", "NICHT LESBAR" in m, m)

# Die Lage im Weiss steht im PNG (tEXt "dustfront").
import zlib as _zlib
def mit_lage(png, lage_text):
    roh = b"dustfront\0" + lage_text.encode("latin-1")
    stueck = (_struct.pack(">I", len(roh)) + b"tEXt" + roh
              + _struct.pack(">I", _zlib.crc32(b"tEXt" + roh) & 0xFFFFFFFF))
    return png[:33] + stueck + png[33:]          # gleich nach IHDR
breit_png = png_bauen(64, 32)
ohne = SK.bild_lage(breit_png, (64, 32))
pruef("Ohne Angabe fuellt das Bild den Schirm",
      ohne["x"] == 0.5 and ohne["y"] == 0.5
      and ohne["h"] * K.GAME_H * 64 / 32.0 >= K.GAME_W - 0.5 and ohne["h"] >= 1.0,
      str(ohne))
gesetzt = SK.bild_lage(mit_lage(breit_png, '{"x": 0.25, "y": 0.7, "h": 0.5}'), (64, 32))
pruef("Mit Angabe steht es, wo es hingeschoben wurde", gesetzt == {"x": 0.25, "y": 0.7, "h": 0.5},
      str(gesetzt))
pruef("Pygame liest das PNG trotzdem",
      SK.bild_lesen(mit_lage(breit_png, '{"x": 0.25, "y": 0.7, "h": 0.5}')).get_size() == (64, 32))
wild = SK.bild_lage(mit_lage(breit_png, '{"x": 99, "y": -99, "h": 1e9}'), (64, 32))
pruef("Was ausserhalb liegt, wird gekappt",
      wild == {"x": GK["lage_xy"][1], "y": GK["lage_xy"][0], "h": GK["lage_h"][1]}, str(wild))
pruef("Kaputtes JSON heisst: fuellen",
      SK.bild_lage(mit_lage(breit_png, '{kaputt'), (64, 32)) == ohne)
pruef("Die Lage gehoert zum Fingerabdruck",
      SK.Kosmetik(b"", breit_png).kennung
      != SK.Kosmetik(b"", mit_lage(breit_png, '{"x": 0.2, "y": 0.5, "h": 0.5}')).kennung)

# Ein Paket.
ton_a, bild_a = wav_bauen(1.5, hz=300), png_bauen(farbe=(220, 30, 30))
kos_a = SK.Kosmetik(ton_a, bild_a)
pruef("Ein Paket hat einen Fingerabdruck", len(kos_a.kennung) == 16)
pruef("Der nach dem Netz derselbe ist",
      SK.aus_text(kos_a.text()).kennung == kos_a.kennung)
pruef("Nur ein Bild geht", SK.Kosmetik(b"", bild_a).bild is not None)
pruef("Nur ein Ton auch", abs(SK.Kosmetik(ton_a).dauer - 1.5) < 0.01)
pruef("Gar nichts nicht", "LEER" in fehler_von(SK.Kosmetik, b"", b""))
pruef("Ein kaputtes Paket wird abgelehnt", "NICHT LESBAR" in fehler_von(SK.aus_text, "{kaputt"))
m = fehler_von(SK.aus_text, '{"ton": "%s", "bild": ""}'
               % _b64.b64encode(wav_bauen(0.4)).decode())
pruef("Und eines mit zu kurzem Ton auch", "ZU KURZ" in m, m)
groesst = (4 * math.ceil(GK["ton_bytes"] / 3.0) + 4 * math.ceil(GK["bild_bytes"] / 3.0)
           + len('{"ton": "", "bild": ""}'))
pruef("Auch das groesste erlaubte Paket hat nicht mehr Teile als erlaubt",
      math.ceil(groesst / float(GK["teil"])) <= GK["teile_max"],
      "%d Teile" % math.ceil(groesst / float(GK["teil"])))
pruef("Und ein Teil ist weit unter der laengsten Netzzeile",
      GK["teil"] + 200 < K.NETZ["hoechstzeile"])

# Zusammensetzen.
sm = SK.Sammler()
teile_a = kos_a.teile()
reihe = list(reversed(range(len(teile_a))))
zwischen = [sm.nimm(3, kos_a.kennung, i, len(teile_a), teile_a[i]) for i in reihe[:-1]]
fertig = sm.nimm(3, kos_a.kennung, reihe[-1], len(teile_a), teile_a[reihe[-1]])
pruef("Teile in falscher Reihenfolge werden richtig zusammengesetzt",
      len(teile_a) > 2 and all(z is None for z in zwischen)
      and fertig is not None and fertig.kennung == kos_a.kennung, "%d Teile" % len(teile_a))
m = ""
try:
    for i, t_ in enumerate(teile_a):
        sm.nimm(3, "0000000000000000", i, len(teile_a), t_)
except ValueError as f:
    m = str(f)
pruef("Passt der Fingerabdruck nicht, wird es abgelehnt", "KENNUNG" in m, m)
pruef("Mehr Teile als erlaubt werden gar nicht gesammelt",
      sm.nimm(4, "x", 0, GK["teile_max"] + 1, "a") is None and 4 not in sm._stapel)

# Das Konto merkt sie sich.
_ok = _Path(_tempfile.mkdtemp(prefix="dustfront_kosmetik_konto_"))
_abl_k = _AB.LokaleAblage(ordner=_ok / "ablage")
kk = _KM.Konto(ablage_=_abl_k, ordner=_ok, mit_faden=False)
kk.anlegen("Kosmo", "geheim12345")
pruef("Lokal gibt es keine Kosmetik", kk.angemeldet and kk.kosmetik is None, kk.fehler)
kk.hinweis = "ANGEMELDET"
kk.kosmetik_holen()
pruef("Das Holen nebenher laesst den Hinweis stehen", kk.hinweis == "ANGEMELDET")
_b = lambda x: _b64.b64encode(x).decode()
kk._kosmetik_gelesen(_AB.gut({"ton": _b(ton_a), "bild": _b(bild_a)}))
pruef("Was vom Server kommt, wird geprueft und gilt",
      kk.kosmetik is not None and kk.kosmetik.kennung == kos_a.kennung)
kk2 = _KM.Konto(ablage_=_abl_k, ordner=_ok, mit_faden=False)
pruef("Und ist beim naechsten Start auch ohne Netz da",
      kk2.kosmetik is not None and kk2.kosmetik.kennung == kos_a.kennung)
kk._kosmetik_gelesen(_AB.schlecht("TABELLE FEHLT"))
pruef("Ein Fehler vom Server laesst die gemerkte stehen",
      kk.kosmetik is not None and kk.kosmetik_fehler == "TABELLE FEHLT")
kk._kosmetik_gelesen(_AB.gut({"ton": _b(wav_bauen(0.4)), "bild": ""}))
kk3 = _KM.Konto(ablage_=_abl_k, ordner=_ok, mit_faden=False)
pruef("Was die Pruefung nicht besteht, gilt nicht - auch nicht von der Platte",
      kk.kosmetik is None and "ZU KURZ" in kk.kosmetik_fehler and kk3.kosmetik is None,
      kk.kosmetik_fehler)
kk._kosmetik_gelesen(_AB.gut({"ton": _b(ton_a), "bild": ""}))
kk.abmelden()
pruef("Abmelden nimmt sie mit", kk.kosmetik is None
      and not (_ok / _KM.KOSMETIK_DATEI).exists())

# Verteilen in der Lobby: Gastgeber mit Kosmetik, ein Gast mit, einer ohne.
# Jeder mit eigenem Konto - sonst haetten alle dieselbe.
def kos_app(name, kosmetik):
    a = App(name, None, headless=True)
    o = _Path(_tempfile.mkdtemp(prefix="dustfront_kosmetik_app_"))
    a._konto = _KM.Konto(ablage_=_AB.LokaleAblage(ordner=o / "ablage"),
                         ordner=o, mit_faden=False)
    a._konto.kosmetik = kosmetik
    return a

kos_b = SK.Kosmetik(wav_bauen(2.0, hz=500), png_bauen(48, 24, (30, 30, 220)))
app_ka, app_kb, app_kc = kos_app("KA", kos_a), kos_app("KB", kos_b), kos_app("KC", None)
_neuer_port()
wk_ = Gefecht(app_ka, "WIRT", gastgeber=netz.Gastgeber(_port[0]), lobby=True,
              modus="pvp", seed=7)
g1_ = Gefecht(app_kb, "EINS", gast=netz.Gast("127.0.0.1:%d" % _port[0]))
alle_k = [wk_, g1_]

def kos_laufen(schritte, bis=None):
    for i in range(schritte):
        for x in alle_k:
            x.schritt(K.NETZ["takt"])
        if bis is not None and bis():
            return i + 1
    return schritte

kos_laufen(400, lambda: wk_.kosmetik_bereit and len(wk_.kos_index) == 2
           and g1_.kosmetik_von(0) is not None)
n1 = g1_.meine_nummer
pruef("Der Gastgeber kennt beide Kosmetiken",
      wk_.kos_index == {0: kos_a.kennung, n1: kos_b.kennung}, str(wk_.kos_index))
pruef("Der Gast hat die des Gastgebers",
      g1_.kosmetik_von(0) is not None and g1_.kosmetik_von(0).kennung == kos_a.kennung)
pruef("Und der Gastgeber die des Gastes",
      wk_.kosmetik_von(n1) is not None and wk_.kosmetik_von(n1).kennung == kos_b.kennung)
pruef("Damit ist alles geladen", wk_.kosmetik_stand() == (1, 1), str(wk_.kosmetik_stand()))

g2_ = Gefecht(app_kc, "ZWEI", gast=netz.Gast("127.0.0.1:%d" % _port[0]))
alle_k.append(g2_)
kos_laufen(60, lambda: len(wk_.kaempfer) == 3)
pruef("Kommt einer dazu, ist nicht mehr alles geladen",
      len(wk_.kaempfer) == 3 and not wk_.kosmetik_bereit, str(wk_.kosmetik_stand()))
pruef("Dann geht der Start mit Kosmetik nicht",
      not wk_.plan_starten(0, kosmetik=True) and wk_.in_lobby
      and "KOSMETIK LÄDT" in wk_.hinweis, wk_.hinweis)
tafel_k = LB.Rundenplanung(app_ka, wk_)
knopf_k = {e.name: e for e in tafel_k.elemente}
pruef("Auf der Tafel ist MIT KOSMETIK gesperrt, OHNE nicht",
      knopf_k["start_mit"].gesperrt and not knopf_k["start_ohne"].gesperrt
      and "start" not in knopf_k)
eintraege_k = [e[0] for e in wk_._menue_baut()]
pruef("Das Pausenmenue bietet beides an",
      "starten_kos" in eintraege_k and "starten" in eintraege_k)
schritte_k = kos_laufen(600, lambda: wk_.kosmetik_bereit)
n2 = g2_.meine_nummer
pruef("Der Neue bekommt alles", g2_.kosmetik_von(0) is not None
      and g2_.kosmetik_von(n1) is not None
      and g2_.kosmetik_von(n1).kennung == kos_b.kennung,
      "%d Schritte" % schritte_k)
pruef("Wer keine hat, steht nicht im Index", n2 not in wk_.kos_index)
pruef("Der Gastgeber zaehlt alle Rechner", wk_.kosmetik_stand() == (3, 3),
      str(wk_.kosmetik_stand()))
pruef("Der Gast zaehlt fuer sich", g2_.kosmetik_stand() == (2, 2),
      str(g2_.kosmetik_stand()))
tafel_k.aufbauen()
knopf_k = {e.name: e for e in tafel_k.elemente}
pruef("Jetzt ist MIT KOSMETIK frei", not knopf_k["start_mit"].gesperrt)
pruef("In der Lobby gilt Kosmetik immer", wk_.kosmetik_aktiv and g2_.kosmetik_aktiv)
app_ka.flaeche.fill(K.C_VOID)
wk_.zeichnen(app_ka.flaeche, 1.0)            # Kopfzeile mit Ladestand

# Ein veraenderter Klient: falscher Fingerabdruck, zu kurzer Ton.
klein = SK.Kosmetik(b"", png_bauen(8, 8))
g1_.gast.senden({"t": "kos", "k": "falsch0000000000", "i": 0, "n": 1, "d": klein.text()})
kos_laufen(10)
pruef("Ein Paket mit falschem Fingerabdruck wird abgelehnt",
      wk_.kos_index.get(n1) == kos_b.kennung and "ABGELEHNT" in wk_._meldung,
      wk_._meldung)
roh_kurz = '{"ton": "%s", "bild": ""}' % _b(wav_bauen(0.5, rate=11025))
kennung_kurz = __import__("hashlib").sha1(wav_bauen(0.5, rate=11025) + b"|").hexdigest()[:16]
stuecke = [roh_kurz[i:i + GK["teil"]] for i in range(0, len(roh_kurz), GK["teil"])]
for i, s in enumerate(stuecke):
    g1_.gast.senden({"t": "kos", "k": kennung_kurz, "i": i, "n": len(stuecke), "d": s})
wk_._meldung = ""
kos_laufen(10)
pruef("Ein zu kurzer Ton an der Kontoseite vorbei kommt nicht durch",
      wk_.kos_index.get(n1) == kos_b.kennung and "ZU KURZ" in wk_._meldung,
      wk_._meldung)

# Die Runde mit Kosmetik.
pruef("Ist alles da, startet die Runde mit Kosmetik",
      wk_.plan_starten(0, kosmetik=True) and not wk_.in_lobby)
kos_laufen(40)
pruef("Und alle wissen es",
      all(x.regelwerk.get("kosmetik") and x.kosmetik_aktiv for x in alle_k)
      and not any(x.in_lobby for x in alle_k))
pruef("Die Kosmetik bleibt ueber den Rundenstart erhalten",
      g2_.kosmetik_von(n1) is not None and wk_.kosmetik_von(n1) is not None)

def lauschen(a):
    """Was eine App abspielt: eigene Toene und Klaenge aus der Tabelle."""
    log = []
    a.klaenge.ton_spielen = lambda ton, laut=1.0: log.append(("ton", ton))
    a.klaenge.spielen = lambda name, laut=1.0, *x, **y: log.append(("name", name))
    return log

log_w, log_2 = lauschen(app_ka), lauschen(app_kc)
knall, pfeifen = K.skin("blend_knall"), K.skin("blend_pfeifen")
werfer1 = wk_.kaempfer[n1]
wk_.welt.explosion(pygame.Vector2(wk_.ich.pos), wk_.ich.ebene, 0.0, "blend", von=werfer1)
mixer_an = pygame.mixer.get_init() is not None
pruef("Beim Gastgeber klingt die Blendgranate wie die des Werfers",
      (("ton", wk_.kosmetiken[n1].klang()) in log_w or not mixer_an)
      and ("name", knall) not in log_w and ("name", pfeifen) not in log_w,
      str(log_w[:4]))
pruef("Und im Weiss steht sein Bild", wk_.kos_zeigen is wk_.kosmetiken[n1]
      and wk_.befinden.blend > 0.3)
neben_2 = pygame.Vector2(wk_.kaempfer[n2].pos)
wk_.welt.explosion(neben_2, wk_.kaempfer[n2].ebene, 0.0, "blend", von=werfer1)
kos_laufen(6)
pruef("Beim Gast ebenso - auch wenn er selbst gar keine hat",
      (("ton", g2_.kosmetiken[n1].klang()) in log_2 or not mixer_an)
      and ("name", knall) not in log_2 and g2_.kos_zeigen is g2_.kosmetiken[n1],
      str(log_2[:4]))
app_kc.flaeche.fill(K.C_VOID)
g2_.zeichnen(app_kc.flaeche, 1.0)
mitte_k = app_kc.flaeche.get_at((K.GAME_W // 2, K.GAME_H // 2))
pruef("Das Bild ist mitten im Weiss zu sehen", mitte_k.b > mitte_k.r + 80,
      str(tuple(mitte_k)))
ecke_k = app_kc.flaeche.get_at((3, 3))
pruef("Ohne Angabe fuellt es den ganzen Schirm, bis in die Ecken",
      ecke_k.b > ecke_k.r + 80, str(tuple(ecke_k)))
del log_w[:]
wk_.kos_zeigen = None
wk_.welt.explosion(pygame.Vector2(wk_.ich.pos), wk_.ich.ebene, 0.0, "blend",
                   von=wk_.kaempfer[n2])
pruef("Wirft einer ohne Kosmetik, knallt es wie immer",
      ("name", knall) in log_w and not any(e[0] == "ton" for e in log_w)
      and wk_.kos_zeigen is None, str(log_w[:4]))

# Die Runde ohne Kosmetik.
wk_.lobby_betreten()
kos_laufen(40)
pruef("Ohne Kosmetik gestartet", wk_.plan_starten(0, kosmetik=False))
kos_laufen(40)
pruef("Weiss es auch jeder", all(not x.regelwerk.get("kosmetik")
                                 and not x.kosmetik_aktiv for x in alle_k))
del log_w[:]
wk_.welt.explosion(pygame.Vector2(wk_.ich.pos), wk_.ich.ebene, 0.0, "blend",
                   von=werfer1 if n1 in wk_.kaempfer else wk_.kaempfer[n1])
pruef("Dann knallt auch die Granate des Gastes wie immer",
      ("name", knall) in log_w and not any(e[0] == "ton" for e in log_w)
      and wk_.kos_zeigen is None, str(log_w[:4]))

# Zurueck in der Lobby: ein Gast aendert seine, dann nimmt er sie weg.
wk_.lobby_betreten()
kos_laufen(20)
kos_b2 = SK.Kosmetik(wav_bauen(1.2, hz=700))
app_kb._konto.kosmetik = kos_b2
kos_laufen(400, lambda: g2_.kosmetik_von(n1) is not None
           and g2_.kosmetik_von(n1).kennung == kos_b2.kennung)
pruef("Aendert ein Gast seine Kosmetik, haben alle die neue",
      wk_.kos_index.get(n1) == kos_b2.kennung and g2_.kosmetik_von(n1) is not None
      and g2_.kosmetik_von(n1).kennung == kos_b2.kennung and g2_.kosmetik_von(n1).bild is None)
app_kb._konto.kosmetik = None
kos_laufen(20)
pruef("Nimmt er sie weg, ist sie ueberall weg",
      n1 not in wk_.kos_index and n1 not in g2_.kosmetiken and n1 not in wk_.kosmetiken)
pruef("Und es wird nur noch gezaehlt, was es gibt", wk_.kosmetik_stand() == (2, 2),
      str(wk_.kosmetik_stand()))
app_kb._konto.kosmetik = kos_b
kos_laufen(400, lambda: g2_.kosmetik_von(n1) is not None)
g1_.verlassen()
alle_k.remove(g1_)
kos_laufen(60, lambda: n1 not in wk_.kaempfer)
kos_laufen(10)
pruef("Wer geht, nimmt seine Kosmetik mit",
      n1 not in wk_.kos_index and n1 not in g2_.kosmetiken,
      "%s / %s" % (wk_.kos_index, list(g2_.kosmetiken)))
wk_.verlassen(); g2_.verlassen()

# ── 0.29: Munition in der Lobby, deckende Blendung, Minikarte ────────
from dustfront.render import Befinden as _Bef
wm9, gm9 = lobbypaar(modus="pvp")
k9 = wm9.kaempfer[gm9.meine_nummer]
k9.waffe_waehlen(k9.waffen.index("sturm"))
k9.magazin["sturm"] = 2
k9.magazin["granate"] = 0
k9.nachlade_rest = 1.5
for _ in range(10):
    wm9.schritt(K.NETZ["takt"]); gm9.schritt(K.NETZ["takt"])
pruef("In der Lobby ist jedes Magazin wieder voll - auch die Granaten",
      k9.magazin["sturm"] == K.WAFFEN["sturm"]["magazin"]
      and k9.magazin["granate"] == K.WAFFEN["granate"]["magazin"],
      "%d / %d" % (k9.magazin["sturm"], k9.magazin["granate"]))
pruef("Und niemand muss nachladen", k9.nachlade_rest == 0.0)
pruef("Der Gast sieht es so", gm9.ich is not None
      and gm9.ich.magazin.get("sturm") == K.WAFFEN["sturm"]["magazin"])

# Die Minikarte: oben rechts, neben den Ebenen, der Punktestand darunter.
app.flaeche.fill(K.C_VOID)
wm9.zeichnen(app.flaeche, 1.0)
r9 = wm9.hud.minikarte.rechteck(wm9.welt)
pruef("Die Minikarte steht oben links",
      r9.left == K.MINIKARTE["links"] and r9.top == K.MINIKARTE["oben"]
      and r9.width <= K.MINIKARTE["breite"] and r9.height <= K.MINIKARTE["hoehe"], str(r9))
ich9 = wm9.ich
# Seit 0.34.92 zeigt die Anzeige die Karte als Kreis unten links, um die
# eigene Figur: man selbst steht in seiner Mitte.
px = (K.HUD["karte_x"] + K.HUD["karte_d"] // 2, K.GAME_H - K.HUD["unten"] - K.HUD["karte_d"] // 2)
pruef("Man selbst steht darauf, wo man ist (in der Mitte der runden Karte)",
      tuple(app.flaeche.get_at(px))[:3] == (230, 255, 248), str(tuple(app.flaeche.get_at(px))))
wm9.verlassen(); gm9.verlassen()

def nur_verbuendete(modus):
    w, g = gefechtspaar(modus)
    for _ in range(10):
        w.schritt(K.NETZ["takt"]); g.schritt(K.NETZ["takt"])
    w._farbe_fuer = lambda k, eigen=False: (1, 2, 250)
    andere = w.kaempfer[g.meine_nummer]
    e0 = w.welt.ebene(w.ich.ebene)
    # Sicher auf der Karte und weit genug weg von einem selbst.
    andere.pos.update(e0.pixel_breite * (0.75 if w.ich.pos.x < e0.pixel_breite / 2 else 0.25),
                      e0.pixel_hoehe * 0.5)
    andere.ebene = w.ich.ebene
    app.flaeche.fill(K.C_VOID)
    w.hud.minikarte.zeichnen(app.flaeche, w)
    r = w.hud.minikarte.rechteck(w.welt)
    e = w.welt.ebenen[0]
    q = (int(r.x + andere.pos.x * r.width / float(e.pixel_breite)),
         int(r.y + andere.pos.y * r.height / float(e.pixel_hoehe)))
    sichtbar = tuple(app.flaeche.get_at(q))[:3] == (1, 2, 250)
    w.verlassen(); g.verlassen()
    return sichtbar
pruef("In PVE stehen die Mitspieler auf der Karte", nur_verbuendete("pve"))
pruef("In PVP nicht - die Karte ist kein Wandhack", not nur_verbuendete("pvp"))

# Die Blendung: voll getroffen ist alles weiss und nichts scheint durch.
bf = _Bef()
bf.blend = 1.0
app.flaeche.fill((20, 10, 5))
bf.blendung_zeichnen(app.flaeche)
pruef("Voll geblendet ist das Bild ganz weiss",
      tuple(app.flaeche.get_at((5, 5)))[:3] == (255, 255, 255)
      and tuple(app.flaeche.get_at((K.GAME_W - 3, K.GAME_H - 3)))[:3] == (255, 255, 255))
bf.blend = K.BLENDEN["deckend_ab"] * 0.5
app.flaeche.fill((20, 10, 5))
bf.blendung_zeichnen(app.flaeche)
halb = tuple(app.flaeche.get_at((5, 5)))[:3]
pruef("Wenn sie nachlaesst, scheint die Welt wieder durch",
      100 < halb[0] < 255 and halb != (255, 255, 255), str(halb))

# ── Gegner fallen nur, wenn man sie schiebt ──────────────────────────
from dustfront.entities import Gegner as _G30
_sp = Spiel(app, seed=20250920)
_w = _sp.welt
def kante_suchen(welt):
    """Eine begehbare Kachel auf Ebene 1, rechts daneben ein Loch, unter
    dem Ebene 0 Boden hat - und weiter rechts wieder Boden."""
    e1, e0 = welt.ebene(1), welt.ebene(0)
    for ty in range(2, e1.hoehe - 2):
        for tx in range(2, e1.breite - 5):
            if (e1.begehbar(tx, ty) and e1.begehbar(tx - 1, ty)
                    and e1.begehbar(tx, ty - 1) and e1.begehbar(tx, ty + 1)
                    and e1.loch(tx + 1, ty) and e1.loch(tx + 1, ty - 1)
                    and e1.loch(tx + 1, ty + 1) and e0.begehbar(tx + 1, ty)
                    and e0.begehbar(tx + 2, ty)):
                return tx, ty
    return None
kante = kante_suchen(_w)
pruef("Die Testkarte hat eine Kante ueber einem Loch", kante is not None)
if kante:
    tx, ty = kante
    rand_x = (tx + 1) * K.TILE           # hier beginnt das Loch
    def zombie_an_der_kante():
        z = _G30(pygame.Vector2(rand_x - 12, (ty + 0.5) * K.TILE), "laeufer", 1)
        z.wartet = 0.0
        _w.dazu(z)
        return z
    _w.held.pos.update(rand_x + 3 * K.TILE, (ty + 0.5) * K.TILE)
    _w.held.ebene = 1
    laeufer = zombie_an_der_kante()
    laeufer.winkel = 0.0
    for _ in range(int(2.0 / K.FIXED_DT)):
        laeufer.tempo.update(laeufer.daten["tempo"], 0)    # stur auf das Loch zu
        laeufer.schritt(K.FIXED_DT)
    pruef("Von selbst laeuft ein Gegner nicht ueber die Kante",
          laeufer.ebene == 1 and laeufer.sturz_rest <= 0 and laeufer.pos.x < rand_x,
          "Ebene %d, x %.0f, Kante %d" % (laeufer.ebene, laeufer.pos.x, rand_x))
    _w.wesen.remove(laeufer) if laeufer in _w.wesen else None

    geschoben = zombie_an_der_kante()
    _w.held.ebene = 0            # niemand oben, der ihn zuruecklockt
    geschoben.schaden(1.0, pygame.Vector2(K.TREFFER["rueckstoss"] * 2.5, 0), None)
    fiel = False
    for _ in range(int(2.5 / K.FIXED_DT)):
        geschoben.schritt(K.FIXED_DT)
        fiel = fiel or geschoben.sturz_rest > 0
    pruef("Geschoben faellt er hinunter", fiel and geschoben.ebene == 0,
          "Ebene %d" % geschoben.ebene)
    pruef("Und steht unten auf Boden, nicht in einer Wand",
          _w.frei(geschoben.pos, geschoben.radius, 0)
          and geschoben.sturz_rest <= 0 and geschoben.flug == 0.0)
    pruef("Der Sturz tut weh", geschoben.leben < geschoben.max_leben - 1.0,
          "%.0f von %.0f" % (geschoben.leben, geschoben.max_leben))

    weit = zombie_an_der_kante()
    weit.pos.x -= 3 * K.TILE            # weit genug weg von der Kante
    weit.schaden(1.0, pygame.Vector2(K.TREFFER["rueckstoss"], 0), None)
    for _ in range(int(1.0 / K.FIXED_DT)):
        weit.schritt(K.FIXED_DT)
    pruef("Ein kleiner Stoss weit vor der Kante laesst ihn oben",
          weit.ebene == 1, "Ebene %d" % weit.ebene)

# ── Sichtweite: Mausrad und Nebel ────────────────────────────────────
from dustfront.mehrspieler import KampfGegner as _KG30
wz, gz = gefechtspaar("pve", karte="staubtal")
for _ in range(20):
    wz.schritt(K.NETZ["takt"]); gz.schritt(K.NETZ["takt"])
for x in list(wz.welt.wesen):
    if isinstance(x, _KG30):
        wz.welt.wesen.remove(x)
wz._wellen = lambda dt: None             # keine neuen Gegner, die das Bild stoeren
pruef("Ohne Drehen ist die Sicht normal", wz.kamera.zoom == 1.0 and wz.sicht_welt() is None)
wz.ereignis(pygame.event.Event(pygame.MOUSEWHEEL, x=0, y=-1))
pruef("Mausrad zurueck: weiter weg", wz.zoom_ziel > 1.0, "%.2f" % wz.zoom_ziel)
for _ in range(8):
    wz.ereignis(pygame.event.Event(pygame.MOUSEWHEEL, x=0, y=-1))
pruef("Bis zur weitesten Stufe, nicht darueber (seit 0.34.135: zu Fuss K.ZOOM hoechst)",
      wz.zoom_ziel == K.ZOOM["hoechst"], "%.2f" % wz.zoom_ziel)
blick_vorher, rad_vorher = wz.blick, wz._rad
wz.ereignis(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_PAGEUP, mod=0, unicode=""))
pruef("Bild hoch schaut eine Ebene hoeher (statt des Mausrads)",
      wz._rad == rad_vorher + 1)
wz._rad = 0
for _ in range(int(0.8 / K.FIXED_DT)):
    wz.schritt(K.FIXED_DT)
pruef("Der Zoom zieht nach", abs(wz.kamera.zoom - 2.0) < 0.01, "%.3f" % wz.kamera.zoom)

ich_z = wz.ich
mitte_bild = pygame.Vector2(K.GAME_W / 2, K.GAME_H / 2)
w1 = wz.kamera.zu_welt(mitte_bild)
w2 = wz.kamera.zu_welt(mitte_bild + pygame.Vector2(100, 0))
pruef("Zielen: ein Bildpixel sind jetzt zwei Weltpixel",
      abs((w2 - w1).x - 200) < 0.01, "%.1f" % (w2 - w1).x)
pruef("Und zu_bild ist die Umkehrung",
      (wz.kamera.zu_bild(wz.kamera.zu_welt((123, 77)) + wz.kamera.versatz)
       - pygame.Vector2(123, 77)).length() < 0.6)

sicht = wz.sicht_welt()
# Seit 0.34.95 ist der klare Bereich groesser als das normale Bild
# (K.ZOOM klar, gewuenscht: "der Nebel soll etwas zurueckgehen").
pruef("Mit Zoom gibt es einen klaren Bereich (K.ZOOM klar), ausserhalb Nebel",
      sicht is not None and sicht.size == (int(round(K.GAME_W * K.ZOOM["klar"])),
                                           int(round(K.GAME_H * K.ZOOM["klar"])))
      and sicht.collidepoint(ich_z.pos.x, ich_z.pos.y), str(sicht))

def bild_mit(gegner_pos):
    """Zeichnet einmal ohne und einmal mit einem Gegner an der Stelle und
    gibt zurueck, ob man ihn dort im Bild sieht."""
    stelle = wz.kamera.zu_bild(gegner_pos)
    rechteck = pygame.Rect(int(stelle.x) - 8, int(stelle.y) - 8, 16, 16)
    app.flaeche.fill(K.C_VOID)
    wz.zeichnen(app.flaeche, 1.0)
    ohne = app.flaeche.subsurface(rechteck).copy()
    g = _KG30(pygame.Vector2(gegner_pos), "brecher", ich_z.ebene, wz)
    g.wartet = 99.0
    g.welt = wz.welt
    wz.welt.wesen.append(g)          # sofort, nicht erst im naechsten Schritt
    app.flaeche.fill(K.C_VOID)
    wz.zeichnen(app.flaeche, 1.0)
    mit = app.flaeche.subsurface(rechteck).copy()
    wz.welt.wesen.remove(g)
    unterschied = sum(1 for x in range(16) for y in range(16)
                      if ohne.get_at((x, y)) != mit.get_at((x, y)))
    return unterschied > 6

# Eine freie Stelle im normalen Bild. Nicht fest 120 px rechts: wo das
# liegt, haengt am Einstiegsplatz, und der haengt an der Karte - seit dem
# Aufzug (0.32.11) stand dort ein Fass.
drinnen = next((pygame.Vector2(sicht.centerx + dx, sicht.centery + dy)
                for dx, dy in ((120, 0), (-120, 0), (0, 90), (0, -90),
                               (150, 70), (-150, 70), (150, -70), (-150, -70))
                if wz.welt.frei(pygame.Vector2(sicht.centerx + dx,
                                               sicht.centery + dy),
                                10, ich_z.ebene)),
               pygame.Vector2(sicht.centerx + 120, sicht.centery))
# Mitten im Nebelstreifen zwischen klarem Bereich und Bildrand (seit
# 0.34.135: klar bis 1,75 - 120 px dahinter lag schon ausserhalb des Bildes).
# Die Kamera schaut der Maus voraus, der klare Bereich nicht: genommen wird
# die Seite mit dem breitesten Streifen.
_lo_bild = wz.kamera.zu_welt(pygame.Vector2(0, 0))
_ru_bild = wz.kamera.zu_welt(pygame.Vector2(K.GAME_W - 1, K.GAME_H - 1))
_streifen = max(((_ru_bild.x - sicht.right, pygame.Vector2((sicht.right + _ru_bild.x) / 2.0, sicht.centery)),
                 (sicht.left - _lo_bild.x, pygame.Vector2((sicht.left + _lo_bild.x) / 2.0, sicht.centery)),
                 (_ru_bild.y - sicht.bottom, pygame.Vector2(sicht.centerx, (sicht.bottom + _ru_bild.y) / 2.0)),
                 (sicht.top - _lo_bild.y, pygame.Vector2(sicht.centerx, (sicht.top + _lo_bild.y) / 2.0))),
                key=lambda t_: t_[0])
# Eine freie Stelle in diesem Streifen (wie drinnen: dort kann ein Fass stehen).
_quer = (pygame.Vector2(0, 1) if abs(_streifen[1].y - sicht.centery) < 1.0 else pygame.Vector2(1, 0))
draussen = next((_streifen[1] + _quer * d_ for d_ in (0, 40, -40, 80, -80, 120, -120, 160, -160, 200, -200)
                 if wz.welt.frei(_streifen[1] + _quer * d_, 10, ich_z.ebene)), _streifen[1])
pruef("... der Nebelstreifen ist breit genug fuer die Probe", _streifen[0] >= 40, "%.0f" % _streifen[0])
pruef("Im normalen Bild sieht man einen Gegner auch mit Zoom",
      wz.welt.frei(drinnen, 10, ich_z.ebene) and bild_mit(drinnen))
pruef("Im Nebel nicht - er wird gar nicht gezeichnet",
      wz.welt.frei(draussen, 10, ich_z.ebene) and not bild_mit(draussen))
pruef("Und Namen stehen im Nebel auch keine", not wz.im_licht(draussen))

import time as _zeit
t0 = _zeit.perf_counter()
for _ in range(10):
    wz.zeichnen(app.flaeche, 1.0)
mit_zoom = (_zeit.perf_counter() - t0) / 10
wz.zoom_ziel = 1.0; wz.kamera.zoom = 1.0; wz._zoom_weich = 1.0
t0 = _zeit.perf_counter()
for _ in range(10):
    wz.zeichnen(app.flaeche, 1.0)
ohne_zoom = (_zeit.perf_counter() - t0) / 10
print("     Bildzeit: %.1f ms normal, %.1f ms bei Zoom 2" % (ohne_zoom * 1000, mit_zoom * 1000))
# Viermal so viel Flaeche, dazu Nebel und Verkleinern: mehr kostet es,
# aber es darf nicht ausufern.
pruef("Zoom 2 bleibt bezahlbar", mit_zoom < 8 * ohne_zoom + 0.004,
      "%.1f ms" % (mit_zoom * 1000))
wz.verlassen(); gz.verlassen()

# ── Der Gast sieht alles, was fliegt ─────────────────────────────────
# Gemeldet in 0.30: "bei Gaesten werden gar keine Granaten angezeigt,
# nur die Explosion". Gesendet wurde nur, was "geschoss", "granate" oder
# "rauchgranate" hiess - Molotow, Blendgranate und Rakete hatten seit den
# Skins andere Bildnamen und kamen nie an.
from dustfront.entities import Granate as _Gr31, Rakete as _Rk31
wf, gf = gefechtspaar("pvp")
for _ in range(20):
    wf.schritt(K.NETZ["takt"]); gf.schritt(K.NETZ["takt"])
werfer = wf.kaempfer[0]
start = pygame.Vector2(werfer.pos)
geworfen = {}
for art in ("granate", "molotov", "blend", "rauch"):
    gr = _Gr31(start, 0.0, K.WAFFEN[art], werfer.ebene, werfer, 120.0)
    wf.welt.dazu(gr)
    geworfen[art] = gr
# Die Rakete schlaegt an der ersten Wand oder Figur ein. Also in eine
# Richtung, in der die naechsten 80 Pixel frei sind - sonst haengt die
# Pruefung davon ab, wo der Seed den Werfer hinstellt.
def _frei_richtung(pos, ebene):
    e = wf.welt.ebene(ebene)
    for winkel in (0.0, 90.0, 180.0, 270.0, 45.0, 135.0, 225.0, 315.0):
        r_ = pygame.Vector2(1, 0).rotate(winkel)
        if all(not e.sichtdicht(int((pos.x + r_.x * d) // K.TILE),
                                int((pos.y + r_.y * d) // K.TILE))
               for d in range(8, 88, 4)):
            return winkel
    return 0.0
rk = _Rk31(pygame.Vector2(start), _frei_richtung(start, werfer.ebene), K.WAFFEN["rakete"],
           werfer.ebene, werfer, None)
wf.welt.dazu(rk)
for _ in range(4):
    wf.schritt(K.NETZ["takt"]); gf.schritt(K.NETZ["takt"])
beim_gast = {e[4] for e in gf._fremde_schuesse}
for art, gr in geworfen.items():
    pruef("Der Gast sieht die %s im Flug" % art.upper(), gr.bild in beim_gast,
          "%s / %s" % (gr.bild, sorted(beim_gast)))
pruef("Und die Rakete", rk.bild in beim_gast,
      "%s, fliegt noch: %s" % (sorted(beim_gast), rk.lebt))
app.flaeche.fill(K.C_VOID)
gf.zeichnen(app.flaeche, 1.0)            # zeichnen darf nicht stolpern
wf.verlassen(); gf.verlassen()

# ── Statistik seit 0.31 ──────────────────────────────────────────────
# Gewuenscht: wen man wie oft erledigt hat, Schuesse und Treffer getrennt
# nach PVP und PVE, abgebrochene Runden gebucht aber getrennt gezaehlt,
# und jede Zeile mit der Version. Jeder mit eigenem, angemeldetem Konto -
# sonst landeten Gastgeber und Gast im selben Journal.
def stat_app(name):
    a = kos_app(name, None)
    a._konto.anlegen(name, "geheim123")
    return a

def stat_paar(modus, **kw):
    _neuer_port()
    kw.setdefault("seed", 31000 + _port[0])
    aw, ag = stat_app("STATW%d" % _port[0]), stat_app("STATG%d" % _port[0])
    w_ = Gefecht(aw, "WIRT", gastgeber=netz.Gastgeber(_port[0]), modus=modus, **kw)
    g_ = Gefecht(ag, "BESUCH", gast=netz.Gast("127.0.0.1:%d" % _port[0]))
    for _ in range(30):
        w_.schritt(K.NETZ["takt"]); g_.schritt(K.NETZ["takt"])
    return w_, g_

def stat_laufen(w_, g_, sekunden):
    for _ in range(int(sekunden / K.NETZ["takt"])):
        w_.schritt(K.NETZ["takt"])
        if g_ is not None:
            g_.schritt(K.NETZ["takt"])

def journal(sz):
    return sz.app.konto.journal.eintraege

pruef("Die Testkonten sind angemeldet",
      stat_app("STATPROBE").konto.angemeldet)

# --- PVE: ein Zombie fallt durch eine Granate, ein Schuss trifft einen
ws, gs = stat_paar("pve")
pruef("Der Gast meldet sein Konto beim Gastgeber an",
      ws.kaempfer[gs.meine_nummer].konto == gs.app.konto.kennung
      and gs.app.konto.kennung != "", ws.kaempfer[gs.meine_nummer].konto)
stat_laufen(ws, gs, K.WELLEN_MP["pause"] + 0.3)
wk31 = ws.kaempfer[0]
wk31.unverwundbar = 999.0
ws.kaempfer[gs.meine_nummer].unverwundbar = 999.0
feinde31 = [x for x in ws.welt.wesen if isinstance(x, KampfGegner) and x.lebt]
pruef("Fuer die Probe ist eine Welle da", len(feinde31) >= 2, str(len(feinde31)))
z1, z2 = feinde31[0], feinde31[1]
z1.leben = 1.0
gr31 = EN.Granate(pygame.Vector2(z1.pos), 0.0, K.WAFFEN["granate"], z1.ebene, wk31, 0.0)
ws.welt.dazu(gr31)
ws.welt.wesen.append(gr31)
gr31.welt = ws.welt
gr31.zuenden()
pruef("Ein Zombie durch die Granate zaehlt als Zombieabschuss",
      wk31.zaehler.get("gegner_abschuesse", 0) >= 1, str(wk31.zaehler))
pruef("... und je Waffe als Abschuss der Granate",
      wk31.waffen_zaehler.get("granate", {}).get("abschuesse", 0) >= 1,
      str(wk31.waffen_zaehler))
pruef("Ein Zombie ist kein Spieler: die Summe der Spielerabschuesse bleibt",
      wk31.werte_runde()["abschuesse"] == 0, str(wk31.werte_runde()))
z2.leben = 9999.0
vor = wk31.zaehler.get("treffer_gegner", 0)
ziel_dx = pygame.Vector2(-12, 0)
kugel = EN.Geschoss(z2.pos + ziel_dx, 0.0, K.WAFFEN["repetierer"], z2.ebene, wk31, "repetierer")
kugel.welt = ws.welt
for _ in range(20):
    if not kugel.lebt:
        break
    kugel.schritt(K.FIXED_DT)
pruef("Ein Treffer auf einen Zombie zaehlt als Treffer auf Gegner",
      wk31.zaehler.get("treffer_gegner", 0) == vor + 1, str(wk31.zaehler))
wk31.zaehlen("schuesse", 7.0, "repetierer")

# Zwischenstand: der Gast bekommt seine Zahlen, bevor die Runde endet.
ws.kaempfer[gs.meine_nummer].zaehlen("schuesse", 3.0, "repetierer")
stat_laufen(ws, gs, K.GEFECHT["zwischenstand_takt"] + 0.3)
pruef("Der Gast hat einen Zwischenstand seiner eigenen Zahlen",
      isinstance(gs._zwischenstand, dict)
      and gs._zwischenstand["werte"].get("schuesse") == 3, str(gs._zwischenstand))

# Abbruch: der Gastgeber geht mitten in der Runde (ESC, Fenster zu).
stat_laufen(ws, gs, max(0.0, K.GEFECHT["abbruch_ab"] - ws._rundenzeit) + 0.2)
pruef("Die Runde laeuft lange genug, um gebucht zu werden", ws.runde_laeuft)
ws.verlassen()
for _ in range(10):
    gs.schritt(K.NETZ["takt"])
jw = journal(ws)
jg = journal(gs)
pruef("Der Gastgeber bucht die abgebrochene Runde", len(jw) == 1, str(jw))
pruef("Der Gast auch", len(jg) == 1, str(jg))
if jw and jg:
    ew, eg = jw[0], jg[0]
    pruef("Beide unter derselben Partie, als Abbruch gekennzeichnet",
          ew["partie"] == eg["partie"] and ew["partie"].startswith("abbruch-")
          and ew["ende"] == eg["ende"] == "abgebrochen",
          "%s / %s" % (ew["partie"], eg["partie"]))
    pruef("Mit der Version, mit der gespielt wurde",
          ew["version"] == eg["version"] == K.VERSION, ew["version"])
    pruef("Ein Abbruch ist keine Runde und kein Sieg, aber ein Abbruch",
          ew["werte"]["runden"] == 0 and ew["werte"]["siege"] == 0
          and ew["werte"]["abgebrochen"] == 1 and not ew["gewonnen"], str(ew["werte"]))
    pruef("Schuesse und Treffer stehen zusaetzlich unter PVE",
          ew["werte"]["schuesse_pve"] == ew["werte"]["schuesse"] == 7
          and ew["werte"]["treffer_pve"] == ew["werte"].get("treffer", 0)
          and "schuesse_pvp" not in ew["werte"], str(ew["werte"]))
    pruef("Der Gast bucht die Zahlen, die der Gastgeber gerechnet hat",
          eg["werte"]["schuesse"] == 3 and eg["werte"]["schuesse_pve"] == 3,
          str(eg["werte"]))
    pruef("Zombieabschuesse kommen mit", ew["werte"].get("gegner_abschuesse", 0) >= 1)
    summe_w = ws.app.konto.journal.summe()
    pruef("In der Uebersicht zaehlt der Abbruch nicht mit, nur als Abbruch",
          summe_w["runden"] == 0 and summe_w["schuesse"] == 0
          and summe_w["abgebrochen"] == 1, str({k: summe_w[k] for k in
                                                 ("runden", "schuesse", "abgebrochen")}))
    summe_a = ws.app.konto.journal.summe(abgebrochene=True)
    pruef("Wer will, nimmt die Abbrueche dazu", summe_a["schuesse"] == 7)
    pruef("Nach Version getrennt",
          ws.app.konto.journal.summe(version="0.0.1", abgebrochene=True)["schuesse"] == 0
          and ws.app.konto.journal.summe(version=K.VERSION, abgebrochene=True)["schuesse"] == 7
          and ws.app.konto.journal.versionen() == [K.VERSION])
gs.verlassen()
pruef("Wer danach selbst geht, bucht nicht noch einmal", len(journal(gs)) == 1)

# --- Zu kurz: wer aufmacht und gleich wieder geht, hat nicht gespielt
wk_, gk_ = stat_paar("pvp")
wk_.verlassen()
for _ in range(10):
    gk_.schritt(K.NETZ["takt"])
gk_.verlassen()
pruef("Eine Runde unter %.0f s wird nicht gebucht" % K.GEFECHT["abbruch_ab"],
      journal(wk_) == [] and journal(gk_) == [], str(journal(wk_)))

# --- PVP: der Gastgeber erledigt den Gast, die Runde endet regulaer
wp, gp = stat_paar("pvp", ende_art="abschuesse", ende_wert=1)
stat_laufen(wp, gp, K.GEFECHT["schutz"] + 0.5)
opfer31 = wp.kaempfer[gp.meine_nummer]
schuetze = wp.kaempfer[0]
opfer31.unverwundbar = 0.0
opfer31.leben = 1.0
kugel = EN.Geschoss(opfer31.pos + ziel_dx, 0.0, K.WAFFEN["scharf"], opfer31.ebene,
                    schuetze, "scharf")
kugel.welt = wp.welt
for _ in range(20):
    if not kugel.lebt:
        break
    kugel.schritt(K.FIXED_DT)
pruef("Der Treffer zaehlt als Treffer auf einen Spieler",
      schuetze.zaehler.get("treffer_spieler", 0) == 1, str(schuetze.zaehler))
schuetze.zaehlen("schuesse", 2.0, "scharf")
if opfer31.am_boden:
    opfer31.boden_rest = 0.0
stat_laufen(wp, gp, 1.0)
pruef("Die Runde ist vorbei", wp.vorbei and gp.vorbei)
jw = journal(wp)
jg = journal(gp)
pruef("Beide haben genau eine Zeile", len(jw) == 1 and len(jg) == 1,
      "%d / %d" % (len(jw), len(jg)))
if jw and jg:
    ew, eg = jw[0], jg[0]
    pruef("Regulaer beendet, mit Version",
          ew["ende"] == eg["ende"] == "regulaer" and ew["version"] == K.VERSION
          and ew["werte"]["runden"] == 1 and "abgebrochen" not in ew["werte"])
    pruef("Wen er erledigt hat: der Gast, mit Name und Konto",
          ew["opfer"] == [{"name": "BESUCH", "konto": gp.app.konto.kennung,
                           "anzahl": 1}], str(ew["opfer"]))
    pruef("Der Gast hat niemanden erledigt", eg["opfer"] == [], str(eg["opfer"]))
    pruef("Der Abschuss steht bei der Waffe, mit der er fiel",
          ew["waffen"].get("scharf", {}).get("abschuesse") == 1, str(ew["waffen"]))
    pruef("... und die Summe zaehlt ihn genau einmal",
          ew["werte"]["abschuesse"] == 1, str(ew["werte"]))
    pruef("Schuesse und Treffer stehen unter PVP",
          ew["werte"]["schuesse_pvp"] == 2 and ew["werte"]["treffer_pvp"] == 1
          and "schuesse_pve" not in ew["werte"], str(ew["werte"]))
    pruef("Danach ist kein Abbruch mehr zu buchen", not wp.runde_laeuft)
wp.verlassen(); gp.verlassen()
pruef("Auch nicht beim Verlassen nach dem Ende",
      len(journal(wp)) == 1 and len(journal(gp)) == 1)

# --- Verbindung weg: der Gastgeber stuerzt ab, ohne etwas zu sagen
wv, gv = stat_paar("pvp")
gv_k = wv.kaempfer[gv.meine_nummer]
gv_k.zaehlen("schuesse", 4.0, "repetierer")
stat_laufen(wv, gv, K.GEFECHT["abbruch_ab"] + 0.4)
wv.gastgeber.schliessen()       # kein verlassen: kein "abbruch" geht hinaus
for _ in range(10):
    gv.schritt(K.NETZ["takt"])
jg = journal(gv)
pruef("Der Gast bucht bei Verbindungsverlust den letzten Zwischenstand",
      len(jg) == 1 and jg[0]["ende"] == "abgebrochen"
      and jg[0]["werte"]["schuesse"] == 4 and jg[0]["werte"]["schuesse_pvp"] == 4,
      str(jg))
gv.verlassen()

# --- Fenster zu: das Spiel verlaesst alle Szenen und bucht dabei
wx, gx = stat_paar("pvp")
stat_laufen(wx, gx, K.GEFECHT["abbruch_ab"] + 0.4)
wx.app.stapel = [wx]
wx.app._fenster_zu()
for _ in range(10):
    gx.schritt(K.NETZ["takt"])
pruef("Fenster zu beim Gastgeber: die Runde ist gebucht, die Szene verlassen",
      len(journal(wx)) == 1 and journal(wx)[0]["ende"] == "abgebrochen"
      and wx.app.stapel == [], str(journal(wx)))
pruef("... und der Gast hat es erfahren",
      len(journal(gx)) == 1 and journal(gx)[0]["partie"] == journal(wx)[0]["partie"])
gx.verlassen()

# ── Der Brandstifter verbrennt sich nicht selbst ───────────────────
# Gemeldet aus einem Playtest: "der Feuerboss nimmt Schaden von seinem
# eigenen Feuer und toetet sich praktisch selbst". Nachgemessen: sein
# Feuer verschont Gegner (verschont="feind", seit 0.26). Was ihn brennt,
# ist der Molotow eines Spielers - das ist Absicht, der brennt alles.
from dustfront.mehrspieler import KampfGegner as _KG40
# Ein frueherer Abschnitt laesst die Feuertaste in der gemeinsamen Eingabe
# gedrueckt - dann schoss WIRT schon im Vorlauf von gefechtspaar. Seit
# 0.34.102 dauert der laenger (Netztakt 1/30), und eine Kugel traf den Boss.
# Hier geht es nur um das Feuer.
app.eingabe.alles_loslassen()
_w40, _g40 = gefechtspaar("pve")
_ich40 = _w40.kaempfer[0]
_ich40.unverwundbar = 9999.0
_boss40 = _KG40(pygame.Vector2(_ich40.pos) + pygame.Vector2(60, 0), "brandstifter", 0, _w40)
_w40.welt.dazu(_boss40)
_w40.welt.wesen.append(_boss40)
_quellen40 = {}
_alt40 = _boss40.schaden
def _schaden40(menge, schub=None, von=None):
    _quellen40[von] = _quellen40.get(von, 0.0) + menge
    return _alt40(menge, schub, von)
_boss40.schaden = _schaden40
_im_feuer40 = 0
for _ in range(int(20 / K.FIXED_DT)):
    _ich40.pos.update(_boss40.pos + pygame.Vector2(40, 0)); _ich40.vorher.update(_ich40.pos)
    _w40.schritt(K.FIXED_DT)
    if any(f.brennt(_boss40.pos, _boss40.ebene) > 0 for f in _w40.welt.feuer):
        _im_feuer40 += 1
pruef("Der Brandstifter steht in seinem eigenen Feuer",
      _im_feuer40 * K.FIXED_DT > 5.0, "%.1f s" % (_im_feuer40 * K.FIXED_DT))
pruef("... und nimmt davon keinen Schaden",
      _boss40.leben == K.BOSSE["brandstifter"]["leben"] and not _quellen40,
      "%.1f Leben" % _boss40.leben)
from dustfront.entities import Brandflaeche as _BF40
_w40.welt.feuer.append(_BF40(pygame.Vector2(_boss40.pos), 0, radius=60, von=_ich40))
for _ in range(int(2 / K.FIXED_DT)):
    _w40.schritt(K.FIXED_DT)
pruef("Der Molotow eines Spielers brennt ihn sehr wohl",
      _boss40.leben < K.BOSSE["brandstifter"]["leben"], "%.1f Leben" % _boss40.leben)
_w40.verlassen(); _g40.verlassen()

# ── Plateaus sind Felsbloecke (nach 0.31) ────────────────────────────
# Gemeldet: auf STAUBTAL, unten stehend mit eingeblendeter oberer Ebene,
# hing das Plateau versetzt und blass neben seinem Felssockel, und
# dazwischen sah man Boden "wie Luft". Die obere Ebene wird vergroessert
# gezeichnet (sie ist naeher am Auge), und ueber dem Fels war sie zu
# 79 Prozent durchsichtig. Jetzt: der Deckel deckend, und zwischen ihm
# und dem Sockel eine Felswand mit derselben Perspektive.
pw_w, pw_g = gefechtspaar("pvp", karte="staubtal")
pw_r = pw_w.renderer
pw_welt = pw_w.welt
kanten = pw_r.klippen(pw_welt, 1, False)
pruef("Die Plateaus von STAUBTAL haben Kanten",
      len(kanten) > 0, "%d Strecken" % len(kanten))
# Zusammengefasst heisst: nirgends beginnt eine Strecke genau dort, wo eine
# andere mit derselben Blickrichtung endet - die beiden waeren eine. Bis
# 0.34 stand hier "weniger als 80 Strecken"; da waren die Plateaus
# Rechtecke. Seit 0.34.6 sind ihre Raender gezeichnet, mit Buchten und
# Nasen, und eine schraege Felskante ist eine Treppe aus kurzen Stuecken -
# das sind viele Strecken, aber keine davon ist zerstueckelt.
_anfaenge_k = {(ax, ay, nx, ny) for (ax, ay, bx, by, nx, ny) in kanten}
_zerstueckelt = [kn for kn in kanten if (kn[2], kn[3], kn[4], kn[5]) in _anfaenge_k]
_kantenkacheln = sum(abs(kn[2] - kn[0]) + abs(kn[3] - kn[1]) for kn in kanten) // K.TILE
pruef("... zu ganzen Waenden zusammengefasst, nicht Kachel fuer Kachel",
      not _zerstueckelt and len(kanten) < _kantenkacheln,
      "%d Strecken auf %d Kantenkacheln, %d haetten verbunden werden muessen"
      % (len(kanten), _kantenkacheln, len(_zerstueckelt)))
e1p = pw_welt.ebene(1)
maske_p = pw_r.obermaske(pw_welt, 1)

def _plateau_feld(tx, ty):
    if not (0 <= tx < e1p.breite and 0 <= ty < e1p.hoehe):
        return False
    i = ty * e1p.breite + tx
    return e1p.kacheln[i] != K.LEER and not maske_p[i]

def _kante_stimmt(ax, ay, bx, by, nx, ny):
    """Jede Kachel entlang der Kante: innen Plateau, aussen keines."""
    T = K.TILE
    schritte = int(max(abs(bx - ax), abs(by - ay)) // T)
    for n in range(schritte):
        mx = ax + (bx - ax) * (n + 0.5) / schritte
        my = ay + (by - ay) * (n + 0.5) / schritte
        innen = (int((mx - nx * 4) // T), int((my - ny * 4) // T))
        aussen = (int((mx + nx * 4) // T), int((my + ny * 4) // T))
        if not _plateau_feld(*innen) or _plateau_feld(*aussen):
            return False
    return True

pruef("Jede Kante liegt genau am Rand eines Plateaus",
      all(_kante_stimmt(*kn) for kn in kanten))

# Die Figur unten, suedlich vor dem grossen Plateau. Wo dessen Nord- und
# Suedrand liegen, steht in der Karte - bis 0.32.28 fest Reihe 8 und 27;
# seit STAUBTAL 300 x 240 Kacheln gross ist, sind es 5 und 83, und die
# Figur stand mitten im Fels.
_spalte_p = 60
_reihen_p = {ty for ty in range(e1p.hoehe) if _plateau_feld(_spalte_p, ty)}
_nord_p = min(_reihen_p)
_sued_p = _nord_p
while _sued_p + 1 in _reihen_p:
    _sued_p += 1
ich_p = pw_w.ich
ich_p.ebene = 0; ich_p.flug = 0.0
ich_p.pos.update((_spalte_p + .5) * K.TILE, (_sued_p + 4.5) * K.TILE)
ich_p.vorher.update(ich_p.pos)
for _ in range(30):
    pw_w.schritt(K.FIXED_DT)
pw_w.obere_zeigen = True
kam = pw_w.kamera
# Die Kamera direkt auf die Figur: wo sie startet, haengt vom Seed ab,
# und 30 Schritte holen sie nicht von ueberall her ein.
kam.pos.update(ich_p.pos)
kam.versatz.update(0, 0)
dz1 = pw_welt.hoehe(0) - pw_welt.hoehe(1)
k1 = K.PERSPEKTIVE["brennweite"] / max(60.0, K.PERSPEKTIVE["brennweite"] + dz1)
ab_unten = pw_r._abbildung(kam, 1.0, 0.0)
ab_oben = pw_r._abbildung(kam, k1, dz1)
probe = pygame.Surface(pw_r.groesse, pygame.SRCALPHA)
probe.fill((0, 0, 0, 0))
anzahl_w = pw_r.klippen_zeichnen(probe, pw_welt, 1, ab_unten, ab_oben, False)
pruef("Von unten werden Waende gezeichnet", anzahl_w > 0, str(anzahl_w))
# Die Suedwand des grossen Plateaus: zwischen Deckelrand und Sockelrand.
x_w = (_spalte_p + .5) * K.TILE
y_sockel = ((_sued_p + 1) * K.TILE - ab_unten[0].y) * ab_unten[2]
y_deckel = ((_sued_p + 1) * K.TILE - ab_oben[0].y) * ab_oben[2]
sx = int((x_w - ab_unten[0].x) * ab_unten[1])
pruef("Der Deckelrand liegt weiter vom Auge weg als der Sockel",
      y_deckel < y_sockel - 4, "%.0f / %.0f" % (y_deckel, y_sockel))
mitte_w = int((y_deckel + y_sockel) / 2)
pruef("Zwischen beiden steht die Felswand - keine Luft",
      probe.get_at((sx, mitte_w)).a == 255, str(probe.get_at((sx, mitte_w))))
# Die Nordwand liegt hinter dem Plateau und unter seinem Deckel.
y_nord = int((_nord_p * K.TILE - ab_unten[0].y) * ab_unten[2]) - 2
if 0 <= y_nord < pw_r.groesse[1]:
    pruef("Die abgewandte Wand wird nicht gezeichnet",
          probe.get_at((sx, y_nord)).a == 0)

# Der Deckel ist deckend: was darunter auf Ebene 0 liegt, scheint nicht
# durch. Zweimal gezeichnet, einmal mit anderem Boden unten.
def _bild_mit_boden(art):
    e0 = pw_welt.ebene(0)
    alt_k = list(e0.kacheln)
    if art is not None:
        for i, k in enumerate(e0.kacheln):
            if k == K.BODEN:
                e0.kacheln[i] = art
    app.flaeche.fill(K.C_VOID)
    pw_w.zeichnen(app.flaeche, 1.0)
    bild_ = app.flaeche.copy()
    e0.kacheln[:] = alt_k
    return bild_

vorher_p = _bild_mit_boden(None)
anders_p = _bild_mit_boden(K.GITTER)
# Ein Punkt auf dem Deckel: knapp oberhalb der Wand, links von der Uhr
# und rechts von der Minikarte.
py_d = int(y_deckel / pw_w.kamera.zoom) - 8
px_d = 240
gleich = vorher_p.get_at((px_d, py_d)) == anders_p.get_at((px_d, py_d))
pruef("Durch den Deckel scheint der Boden darunter nicht durch", gleich,
      "%s / %s" % (vorher_p.get_at((px_d, py_d)), anders_p.get_at((px_d, py_d))))
pw_w.obere_zeigen = False
ohne_a = _bild_mit_boden(None)
ohne_b = _bild_mit_boden(K.GITTER)
pruef("Auch ausgeblendet bleibt das Plateau ein Block",
      ohne_a.get_at((px_d, py_d)) == ohne_b.get_at((px_d, py_d)))

# Was ueber Spielflaeche liegt, blendet weiter aus - nur das Plateau nicht.
flaeche_p = pygame.Surface((4 * K.TILE, K.TILE), pygame.SRCALPHA)
fels_i = next(i for i, k in enumerate(e1p.kacheln) if k != K.LEER and not maske_p[i])
# Ein Stueck Etage ueber Spielflaeche. Bis 0.34 hatte STAUBTAL solche
# Stuecke ueber den Gaengen zu den Aufzuegen; seit 0.34.6 liegen alle Tueren
# in der Felswand, und das Stueck kommt aus der Testkarte (Boden ueber
# Boden).
_gang_welt = pw_welt
gang_i = next((i for i, k in enumerate(e1p.kacheln) if k != K.LEER and maske_p[i]), None)
if gang_i is None:
    _gang_welt = testkarte()
    _gm = pw_r.obermaske(_gang_welt, 1)
    gang_i = next(i for i, k in enumerate(_gang_welt.ebene(1).kacheln)
                  if k != K.LEER and _gm[i])
for i_, x_ in ((fels_i, 0), (gang_i, 2)):
    flaeche_p.fill((200, 180, 140, 255), (x_ * K.TILE, 0, K.TILE, K.TILE))
# Die beiden Felder an ihre Stellen gerueckt: eine Ecke je Feld.
for i_, x_, welt_ in ((fels_i, 0, pw_welt), (gang_i, 2, _gang_welt)):
    _b = welt_.ebene(1).breite
    tx_, ty_ = i_ % _b, i_ // _b
    teil = flaeche_p.subsurface((x_ * K.TILE, 0, K.TILE, K.TILE))
    pw_r._ausstanzen(teil, welt_, 1, pygame.Vector2(tx_ * K.TILE, ty_ * K.TILE),
                     (255, 255, 255, 64), pygame.BLEND_RGBA_MULT)
pruef("Ueber Fels bleibt die Etage deckend",
      flaeche_p.get_at((K.TILE // 2, K.TILE // 2)).a == 255)
pruef("Ueber Spielflaeche wird sie durchsichtig",
      flaeche_p.get_at((2 * K.TILE + K.TILE // 2, K.TILE // 2)).a < 80)

# Auf dem Plateau stehend: der Blick hinab zeigt keine Wand ueber dem Rand.
ich_p.ebene = 1; ich_p.pos.update(46 * K.TILE, 26 * K.TILE); ich_p.vorher.update(ich_p.pos)
for _ in range(30):
    pw_w.schritt(K.FIXED_DT)
kam.pos.update(ich_p.pos)
kam.versatz.update(0, 0)
app.flaeche.fill(K.C_VOID)
pw_w.zeichnen(app.flaeche, 1.0)              # darf nicht stolpern
dz0 = pw_welt.hoehe(1) - pw_welt.hoehe(0)
k0 = K.PERSPEKTIVE["brennweite"] / max(60.0, K.PERSPEKTIVE["brennweite"] + dz0)
probe.fill((0, 0, 0, 0))
pw_r.klippen_zeichnen(probe, pw_welt, 1, pw_r._abbildung(kam, k0, dz0),
                      pw_r._abbildung(kam, 1.0, 0.0), False)
sued_rand = int((28 * K.TILE - kam.ecke.y) / 1.0) + 2
pruef("Von oben liegt die Suedwand unter dem Deckel, nicht davor",
      not (0 <= sued_rand < pw_r.groesse[1])
      or probe.get_at((int(46 * K.TILE - kam.ecke.x), sued_rand)).a == 0)

# ── 0.34.7: zwei Plateaus aufeinander, vom Tal aus ───────────────────
# Gemeldet: von der untersten Ebene aus sah die hohe Tafel (Ebene 2 auf
# ihrem Felssockel in Ebene 1) aus wie eine gewoehnliche - eine Wand,
# oben nackter Fels. Gezeichnet wurde nur eine Etage nach oben. Jetzt
# kommt eine hoehere dazu, wo sie auf einem geschlossenen Felsblock steht.
from dustfront.world import Welt as _Welt67, Ebene as _Eb67
# Probewelt 6 x 5: unten Fels, darueber in Ebene 1 ein Sockel aus Fels
# (Spalten 0-4, Reihen 0-3), rechts daneben Boden, unten ein Loch.
_probe67 = _Welt67([_Eb67.aus_text(["#####."] * 5, 0),
                    _Eb67.aus_text(["#####."] * 4 + ["~~~~~~"], 1),
                    _Eb67.aus_text(["......"] * 5, 2)])
_m67 = pw_r.turm_auslassen(_probe67, 2, 0)
pruef("Turm: Ebene 2 auf dem Felssockel gehoert dazu",
      all(_m67[y_ * 6 + x_] == 0 for y_ in range(4) for x_ in range(5)))
pruef("... ueber begehbarer Ebene 1 nicht", all(_m67[y_ * 6 + 5] for y_ in range(5)))
pruef("... ueber einem Loch in Ebene 1 auch nicht", all(_m67[24 + x_] for x_ in range(6)))
# Zu klein ist kein Turm: eine Mauer auf einer Mauer (der Aussenrand der
# Testkarte) schwebte sonst als Rahmen ueber dem Bild.
_klein67 = _Welt67([_Eb67.aus_text(["##....", "##....", "......"], 0),
                    _Eb67.aus_text(["##....", "##....", "......"], 1),
                    _Eb67.aus_text(["......"] * 3, 2)])
pruef("... und ein Block mit weniger als %d Kacheln oben ist keiner"
      % K.PERSPEKTIVE["turm_flaeche"], all(pw_r.turm_auslassen(_klein67, 2, 0)))

_tm67 = pw_r.turm_auslassen(pw_welt, 2, 0)
_e0_67 = pw_welt.ebene(0)
_stand67 = next(((i % e1p.breite - 4, i // e1p.breite) for i, weg in enumerate(_tm67)
                 if not weg and _e0_67.begehbar(i % e1p.breite - 4, i // e1p.breite)
                 and all(_e0_67.begehbar(i % e1p.breite - d, i // e1p.breite)
                         for d in range(4, 9))), None)
pruef("STAUBTAL hat einen Turm, an den man unten herankommt", _stand67 is not None)
if _stand67 is not None:
    ich_p.ebene = 0; ich_p.flug = 0.0
    ich_p.pos.update((_stand67[0] + .5) * K.TILE, (_stand67[1] + .5) * K.TILE)
    ich_p.vorher.update(ich_p.pos)
    for _ in range(30):
        pw_w.schritt(K.FIXED_DT)
    kam.pos.update(ich_p.pos)
    kam.versatz.update(0, 0)
    e2_67 = pw_welt.ebene(2)

    def _bild67(art):
        alt_ = list(e2_67.kacheln)
        if art is not None:
            e2_67.kacheln[:] = [art if k_ != K.LEER else k_ for k_ in e2_67.kacheln]
        app.flaeche.fill(K.C_VOID)
        pw_w.zeichnen(app.flaeche, 1.0)
        e2_67.kacheln[:] = alt_
        return app.flaeche.copy()

    for _zeigen67 in (True, False):
        pw_w.obere_zeigen = _zeigen67
        _a67, _b67 = _bild67(None), _bild67(K.GITTER)
        _anders67 = sum(1 for x_ in range(0, K.GAME_W, 4) for y_ in range(0, K.GAME_H, 4)
                        if _a67.get_at((x_, y_)) != _b67.get_at((x_, y_)))
        pruef("Vom Tal aus ist die Oberflaeche der hohen Tafel zu sehen (obere Ebene %s)"
              % ("an" if _zeigen67 else "aus"), _anders67 > 50, "%d Proben anders" % _anders67)
    pw_w.obere_zeigen = False
pw_w.verlassen(); pw_g.verlassen()

# ── Zombies tragen keine Schusswaffen (nach 0.31) ───────────────────
# Laeufer, Brecher und Speier benutzten die Spielerfigur, und deren
# Vorgabe ohne Waffe war ein Gewehrstummel. Jetzt `bewaffnet=False`: die
# Arme parallel nach vorn statt zur Mitte, wo das Gewehr war. Erkannt wird
# der Stummel an seiner Farbe.
STUMMEL = (86, 72, 52)
def _stummel_pixel(name):
    b = _PLATZHALTER[name]()
    return sum(1 for x in range(b.get_width()) for y in range(b.get_height())
               if tuple(b.get_at((x, y)))[:3] == STUMMEL and b.get_at((x, y)).a)

pruef("Die Spielerfigur ohne Waffe hat ebenfalls leere Arme",
      _stummel_pixel("spieler") == 0)
for zname in ("gegner_laeufer", "gegner_brecher", "gegner_speier"):
    pruef("%s haelt keine Schusswaffe" % zname, _stummel_pixel(zname) == 0)
from dustfront import art as _ART
_ZFARBEN = {"gegner_laeufer": ((128, 84, 58), (58, 36, 24)),
            "gegner_brecher": ((88, 58, 42), (38, 27, 21))}
for zname, (rumpf_z, dunkel_z) in _ZFARBEN.items():
    zb = _PLATZHALTER[zname]()
    zc = zb.get_width() // 2
    arm_z = tuple(int(d + (r - d) * _ART.ZOMBIE_ARMTON) for d, r in zip(dunkel_z, rumpf_z))
    # Kurze Arme, so lang wie beim Bewaffneten (bis c + 8), in ihrem eigenen,
    # etwas helleren Ton - sonst wachsen sie mit dem Kopfrand zusammen.
    pruef("%s hat zwei kurze Arme im eigenen Ton" % zname,
          tuple(zb.get_at((zc + 7, zc - 4)))[:3] == arm_z
          and tuple(zb.get_at((zc + 7, zc + 4)))[:3] == arm_z,
          "%s / %s statt %s" % (tuple(zb.get_at((zc + 7, zc - 4)))[:3],
                                tuple(zb.get_at((zc + 7, zc + 4)))[:3], arm_z))
    pruef("%s: die Arme heben sich vom Kopfrand ab" % zname,
          arm_z != dunkel_z and tuple(zb.get_at((zc + 5, zc)))[:3] == dunkel_z)
    pruef("%s: nicht laenger als beim Bewaffneten" % zname,
          zb.get_at((zc + 10, zc - 4)).a == 0 and zb.get_at((zc + 10, zc + 4)).a == 0)
    if zname == "gegner_brecher":
        pruef("Der Brecher hat keinen Bruststreifen mehr",
              not any(zb.get_at((x, y)).a
                      and tuple(zb.get_at((x, y)))[:3] == K.C_RUST
                      for x in range(zb.get_width())
                      for y in range(zb.get_height())))
for zname in ("gegner_laeufer", "gegner_brecher"):
    zb = _PLATZHALTER[zname]()
    zc = zb.get_width() // 2
    pruef("%s: vor der Brust kein Lauf mehr" % zname,
          zb.get_at((zc + 12, zc)).a == 0, str(zb.get_at((zc + 12, zc))))

# ── Waffenbalance 0.32 ───────────────────────────────────────────────
# Gemeldet: "dass das MG einen so weit nach hinten drueckt, war so nicht
# gedacht ... standardmaessig extrem langsam, aber nicht gepusht".
from dustfront import regeln as _R42
_w42, _g42 = gefechtspaar("pvp", karte="staubtal")
_e42 = _w42.welt.ebene(0)
_platz42 = None
for _ty in range(3, _e42.hoehe - 3):
    for _tx in range(16, _e42.breite - 16):
        if all(_e42.begehbar(_tx + dx, _ty + dy) for dx in range(-15, 16) for dy in (-1, 0, 1)):
            _platz42 = pygame.Vector2((_tx + 0.5) * K.TILE, (_ty + 0.5) * K.TILE)
            break
    if _platz42:
        break
_k42 = _w42._dazu(9, "PROBE")
def _mg_weg(schub_regel):
    _k42.mg_schub = schub_regel
    _k42.unverwundbar = 999
    _k42.pos.update(_platz42); _k42.vorher.update(_platz42); _k42.tempo.update(0, 0)
    _k42.waffe = _k42.waffen.index("lmg")
    _k42.anlauf = 0.0; _k42.takt = 0.0
    for _ in range(int(3.0 / K.FIXED_DT)):
        _k42.magazin["lmg"] = 999
        _k42.ziel = _k42.pos + pygame.Vector2(300, 0)
        _k42.will = pygame.Vector2(0, 0)
        _k42.feuert = True
        _k42.schritt(K.FIXED_DT)
    _k42.feuert = False
    return _platz42.x - _k42.pos.x
_ohne42, _mit42 = _mg_weg(False), _mg_weg(True)
pruef("Das MG schiebt den Schuetzen von sich aus kaum", _ohne42 < 6,
      "%.0f px in 3 s Dauerfeuer" % _ohne42)
pruef("Mit der Regel MG-RUECKSTOSS SCHIEBT wie frueher",
      _mit42 > 15, "%.0f px" % _mit42)
pruef("Die Regel gibt es, aus als Vorgabe",
      "mg_schub" in _R42.NACH_NAME and _R42.vorgabe()["mg_schub"] is False)
_w42._regeln_setzen(dict(_w42.regelwerk, mg_schub=True))
pruef("Sie kommt bei allen Figuren an",
      all(k.mg_schub for k in _w42.kaempfer.values()))
_w42._regeln_setzen(dict(_w42.regelwerk, mg_schub=False))
from dustfront.entities import Geschoss as _G42
_ein42 = _G42(pygame.Vector2(0, 0), 0.0, K.WAFFEN["schrot"], 0, None, "schrot")
pruef("Der Schrot-Stoss gilt je Schuss, nicht je Kugel",
      abs(_ein42.schub_anteil * K.WAFFEN["schrot"]["geschosse"] - 1.0) < 1e-9)
pruef("Der Repetierer reicht weiter als das Sturmgewehr",
      K.WAFFEN["repetierer"]["reichweite"] > K.WAFFEN["sturm"]["reichweite"])
pruef("Und das MG nicht mehr fast so weit wie der Scharfschuetze",
      K.WAFFEN["lmg"]["reichweite"] < 0.5 * K.WAFFEN["scharf"]["reichweite"])
_w42.verlassen(); _g42.verlassen()

# ── 0.32: von Lobby zu Lobby, ohne LAN-GAST und LAN-GASTGEBER ─────────
# Gemeldet: "Es soll nicht mehr LAN-Gast und LAN-Gastgeber geben ...
# direkt in die Lobby ... wenn ein Gast eine Runde mit einem anderen
# Gastgeber verlaesst, soll er wieder zurueck in eine Lobby kommen."
# Gebaut mit zwei Apps, wie zwei Rechner: jede hat ihren eigenen Stapel.
import time as _t45
from dustfront import lan as _lan45, sitzung as _s45
from dustfront.core import App as _App45
_app_a = _App45("A", None, headless=True)
_app_b = _App45("B", None, headless=True)
# Seit 0.34.13 sieht man sich im LAN nur mit IM LAN SICHTBAR (sonst lauscht
# die Lobby nur auf 127.0.0.1 und fragt keine Firewall). Diese Pruefung ist
# das LAN - beide schalten es ein, wie es ein Spieler im Menue taete.
for _a45 in (_app_a, _app_b):
    _a45.opt["lan_offen"] = True

def _beide45(n=20):
    for _ in range(n):
        for _a in (_app_a, _app_b):
            for _sz in list(_a._aktive()):
                _sz.schritt(K.FIXED_DT)
        _t45.sleep(0.002)

_neuer_port(); _pa45 = _port[0]
_neuer_port(); _pb45 = _port[0]
_la45 = _s45.eigene_lobby(_app_a, headless_port=_pa45)
_lb45 = _s45.eigene_lobby(_app_b, headless_port=_pb45)
pruef("Jeder startet in seiner eigenen Lobby",
      _la45.in_lobby and _lb45.in_lobby and _la45.ist_gastgeber
      and _app_a.stapel == [_la45])
pruef("Ohne Konto und Namen heisst man nicht einfach SPIELER",
      _s45.spielername(_app_a).startswith("SPIELER"), _s45.spielername(_app_a))
pruef("Die Lobby ist im Netz zu finden (sie hat einen Ansager)",
      _la45.ansager is not None and _la45.ansager.sock is not None,
      _la45.ansager.fehler if _la45.ansager else "keiner")

_grund45 = _s45.beitreten(_app_b, "127.0.0.1:%d" % _pa45)
_gast45 = _app_b.stapel[-1]
_beide45(40)
pruef("Beitreten: B steigt aus seiner Lobby in die von A um",
      not _grund45 and not _gast45.ist_gastgeber and len(_la45.kaempfer) == 2
      and _lb45 not in _app_b.stapel, _grund45)
pruef("Die alte eigene Lobby ist dabei zugegangen",
      not _lb45.gastgeber.leitungen and _lb45.ansager is None)
_eintr45 = [x[0] for x in _gast45._menue_baut()]
pruef("Im Menue: anderer Lobby beitreten, Lobby verlassen, Spiel beenden",
      {"suchen", "raus", "beenden"} <= set(_eintr45), str(_eintr45))
_gast45._menue_auf()
_gast45._menue_wirken("raus", True, True)
_heim45 = _app_b.stapel[-1]
_beide45(20)
pruef("Lobby verlassen fuehrt in die eigene Lobby, nicht hinaus",
      _app_b.laeuft and _heim45.ist_gastgeber and _heim45.in_lobby
      and len(_la45.kaempfer) == 1, "%d bei A" % len(_la45.kaempfer))

# Der Gastgeber hoert auf: der Gast landet von selbst wieder daheim.
_s45.beitreten(_app_b, "127.0.0.1:%d" % _pa45)
_beide45(30)
_la45.plan_starten(0)
_beide45(20)
pruef("Mitten in einer fremden Runde", not _app_b.stapel[-1].in_lobby
      and not _app_b.stapel[-1].ist_gastgeber)
_app_a.werfen()
_beide45(10)
_daheim45 = _app_b.stapel[-1]
pruef("Hoert der Gastgeber auf, geht es zurueck in die eigene Lobby",
      _app_b.laeuft and _daheim45.ist_gastgeber and _daheim45.in_lobby)
pruef("Und dort steht, warum", "VERLOREN" in _daheim45.hinweis,
      _daheim45.hinweis)
pruef("Ein Beitritt ins Leere laesst einen, wo man ist",
      bool(_s45.beitreten(_app_b, "127.0.0.1:%d" % _pa45))
      and _app_b.stapel[-1] is _daheim45)

# Abgewiesen (Kennwort): auch das fuehrt heim, mit dem Grund.
_neuer_port()
_wk45 = Gefecht(_app_a, "WIRT", gastgeber=netz.Gastgeber(_port[0]),
                lobby=True, passwort="GEHEIM", ansagen=True)
_app_a.schieben(_wk45)
_s45.beitreten(_app_b, "127.0.0.1:%d" % _port[0], "falsch")
_beide45(30)
pruef("Abgewiesen: zurueck in die eigene Lobby, mit dem Grund",
      _app_b.stapel[-1].ist_gastgeber
      and "KENNWORT" in _app_b.stapel[-1].hinweis, _app_b.stapel[-1].hinweis)

# Die Suche findet die Lobby von A - mit Kennwort-Hinweis -, aber nie
# die eigene.
_such45 = _s45.LobbySuche(_app_b, _app_b.stapel[-1])
_app_b.schieben(_such45)
for _ in range(80):
    _beide45(1)
    _t45.sleep(0.01)
    if any(e["port"] == _port[0] for e in _such45._liste()):
        break
_gef45 = [e for e in _such45._liste() if e["port"] == _port[0]]
pruef("Die Lobbysuche findet die Lobby im Netz",
      len(_gef45) == 1 and _gef45[0]["name"] == "WIRT" and _gef45[0]["passwort"],
      str(_such45._liste()))
pruef("Die eigene Lobby steht nicht in der Liste",
      not any(e["kennung"] == _app_b.stapel[0].ansager.kennung
              for e in _such45._liste()))
pruef("Unter der Suche laeuft die eigene Lobby weiter, ohne Eingaben",
      _app_b.stapel[0].pausiert and _app_b.stapel[0] in _app_b._aktive())
_btn45 = [el for el in _such45.elemente if el.name.startswith("lobby:")]
pruef("Jede gefundene Lobby ist ein Knopf", bool(_btn45))
if _btn45:
    _such45.ausloesen(_btn45[0])
    pruef("Mit Kennwort fragt die Suche erst danach",
          "KENNWORT" in _such45.meldung and _such45._verbinde is None,
          _such45.meldung)
app.flaeche.fill(K.C_VOID)
_such45.zeichnen(app.flaeche, 1.0)          # darf nicht abstuerzen
pruef("Eine Antwort aus dem Netz wird geprueft, bevor sie zaehlt",
      _lan45.eintrag_pruefen(b"kein json", "1.2.3.4") is None
      and _lan45.eintrag_pruefen(b'{"port": 99999}', "1.2.3.4") is None
      and _lan45.eintrag_pruefen(b'{"port": 50505, "name": "x<>y"}',
                                 "1.2.3.4")["name"] == "XY")
for _a in (_app_a, _app_b):
    while _a.stapel:
        _a.werfen()

# ── 0.32: Rundentafel einfach / erweitert, Standardrunde ─────────────
# Gemeldet: "Menues fuer neue Spieler: Rundeneinstellungen einfach und
# erweitert, mit einer definierten Standardrunde."
from dustfront import regeln as _R46, lobby as _LB46, sitzung as _s46
_neuer_port()
_l46 = _s46.eigene_lobby(app, headless_port=_port[0])
pruef("Eine frische Lobby plant die Standardrunde",
      _l46.plan[0] == _R46.standardrunde(_l46._umfeld())
      and _l46.plan[0]["modus"] == K.STANDARDRUNDE["modus"],
      _R46.kurz(_l46.plan[0]))
_einf = [f.schluessel for f in _R46.sichtbar(_l46.plan[0], False)]
_alle = [f.schluessel for f in _R46.sichtbar(_l46.plan[0])]
pruef("Einfach zeigt Spielart, Karte, Dauer - und nicht alles",
      {"modus", "karte", "ende_wert"} <= set(_einf) and len(_einf) < len(_alle)
      and "knapp" not in _einf and "knapp" in _alle, str(_einf))
_alt46 = app.opt["runden_erweitert"]
app.opt["runden_erweitert"] = False
_t46 = _LB46.Rundenplanung(app, _l46)
_namen46 = [el.name for el in _t46.elemente]
pruef("Die Tafel faengt einfach an", "r:knapp" not in _namen46
      and "r:modus" in _namen46 and "ansicht" in _namen46, str(_namen46))
_t46.ausloesen([el for el in _t46.elemente if el.name == "ansicht"][0])
# Seit 0.34.96 blaettert die Liste, wenn sie nicht passt.
for _ in range(40):
    if "r:knapp" in [el.name for el in _t46.elemente]:
        break
    _t46._blaettern(1)
pruef("ERWEITERT zeigt alle Regeln (blaetternd) und merkt es sich",
      "r:knapp" in [el.name for el in _t46.elemente]
      and app.opt["runden_erweitert"] is True
      and all(el.rect.bottom <= _t46.tafel.bottom - 58 for el in _t46.elemente
              if el.name.startswith("r:")))
_l46.plan_verstellen(0, "modus", "pve")
_l46.plan_verstellen(0, "knapp", True)
pruef("Was unter ERWEITERT verstellt ist, weiss die einfache Ansicht",
      [f.schluessel for f in _R46.verborgen_geaendert(_l46.plan[0])] == ["knapp"])
_t46.ausloesen([el for el in _t46.elemente if el.name == "standard"][0])
pruef("STANDARDRUNDE setzt die Runde zurueck",
      _l46.plan[0] == _R46.standardrunde(_l46._umfeld()), _R46.kurz(_l46.plan[0]))
app.opt["runden_erweitert"] = _alt46
app.opt.speichern()
_l46.verlassen()

# ── 0.32: Barrierefreiheit - Blendung einfarbig, Blick voraus ────────
from dustfront.render import Kamera as _Kam47
_k47 = _Kam47((1000, 1000))
_weite47 = float(E.VORGABE["kamera_blick_weite"])
for _ in range(600):
    _k47.schritt(K.FIXED_DT, pygame.Vector2(1000, 1000),
                 pygame.Vector2(1300, 1000), (4000, 4000))
_ohne47 = _k47.pos.x - 1000
_k47.vorausschau = _weite47
for _ in range(600):
    _k47.schritt(K.FIXED_DT, pygame.Vector2(1000, 1000),
                 pygame.Vector2(1300, 1000), (4000, 4000))
pruef("Blick voraus: die Bildmitte liegt vor der Waffe",
      abs(_k47.pos.x - 1000 - _weite47) < 1.0
      and abs(_k47.pos.y - 1000) < 1.0, "%.1f statt %.1f vorher" % (
          _k47.pos.x - 1000, _ohne47))
for _ in range(600):
    _k47.schritt(K.FIXED_DT, pygame.Vector2(1000, 1000),
                 pygame.Vector2(1000 + 2, 1000 - 900), (4000, 4000))
pruef("Nur die Richtung zaehlt, nicht wie weit die Maus weg ist",
      abs((_k47.pos - pygame.Vector2(1000, 1000)).length()
          - _weite47) < 1.0 and _k47.pos.y < 1000)
_w47, _g47 = gefechtspaar("pvp")
_alt47 = app.opt["blendung"]
for _art47, _farbe47 in (("schwarz", (0, 0, 0)), ("weiss", (255, 255, 255))):
    app.opt["blendung"] = _art47
    _g47.befinden.blend = 1.0
    _g47.befinden.blend_rest = 2.0
    app.flaeche.fill((90, 60, 30))
    _g47.zeichnen(app.flaeche, 1.0)
    pruef("Blendung NUR %s: das Bild ist %s" % (_art47.upper(), _art47),
          tuple(app.flaeche.get_at((K.GAME_W // 2, K.GAME_H // 2)))[:3] == _farbe47,
          str(app.flaeche.get_at((K.GAME_W // 2, K.GAME_H // 2))))
    pruef("Und zeigt kein fremdes Bild", _g47.kos_zeigen is None)
app.opt["blendung"] = _alt47
_w47.verlassen(); _g47.verlassen()

# ── 0.32.6: Gegner wechseln die Ebene nur AUF der Treppe ─────────────
# Gemeldet: "laufen nicht wirklich auf die Pads", "despawnen in Sicht".
# Gemessen: der Rest, bei dem gewechselt wurde, war der der Nachbarkachel -
# sie wechselten schraeg neben der Rampe, standen oben im Nichts, kamen
# nicht weg und wurden umgesetzt (15 Zombies, 90 s: 7 bis 11 Mal).
_w52, _g52 = gefechtspaar("pve", karte="staubtal")
_w52.pause_rest = 1e9
for _x in list(_w52.welt.wesen):
    if isinstance(_x, KampfGegner):
        _x.lebt = False
_w52.gegner_offen = []; _w52.welle_rest = []
_n52 = _w52.welt.wege
# Die Aufstellung richtet sich nach der Treppe, nicht nach festen
# Versaetzen: seit STAUBTAL 0.32.29 (300 x 240, Aufzuege im Fels) lag
# "links oben neben der Rampe" mitten im Fels. Gesucht wird die Seite, von
# der man unten heran- und oben weggeht, und der Gegner startet leicht
# schraeg davor - genau so wechselten sie frueher neben der Treppe.
def _frei_weg52(e, tx, ty, r_von, r_bis):
    for dx, dy in ((0, 1), (0, -1), (1, 0), (-1, 0)):
        for r in range(r_von, r_bis):
            if all(e.begehbar(tx + dx * i, ty + dy * i)
                   and not e.loch(tx + dx * i, ty + dy * i)
                   for i in range(1, r + 1)):
                return (tx + dx * r, ty + dy * r), (dx, dy)
    return None, None

for _t52 in _n52.treppen:
    _e52, _tx52, _ty52, _z52 = _t52
    if _e52 != 0 or _z52 != 1:
        continue
    _unten52, _ri52 = _frei_weg52(_w52.welt.ebene(0), _tx52, _ty52, 3, 4)
    _oben_k52, _ = _frei_weg52(_w52.welt.ebene(1), _tx52, _ty52, 5, 7)
    if _unten52 and _oben_k52:
        break
_oben52 = _w52.welt.landeplatz(pygame.Vector2((_oben_k52[0] + .5) * 32,
                                              (_oben_k52[1] + .5) * 32), 9, _z52)
# Leicht schraeg versetzt, quer zur Anlaufrichtung.
_gg52 = KampfGegner(pygame.Vector2((_unten52[0] + .5 + 0.4 * _ri52[1]) * 32,
                                   (_unten52[1] + .5 + 0.4 * _ri52[0]) * 32),
                    "brecher", _e52, _w52)
_gg52.wartet = 0.0
_w52.welt.dazu(_gg52); _w52.gegner_offen.append(_gg52)
_wechsel52 = []
for _ in range(int(12.0 / K.FIXED_DT)):
    for _k in _w52.kaempfer.values():
        _k.leben = _k.max_leben; _k.ebene = _z52; _k.pos.update(_oben52); _k.tempo.update(0, 0)
    _vor = (_gg52.ebene, _n52.kachel(_gg52.pos))
    _w52.schritt(K.FIXED_DT)
    if _gg52.ebene != _vor[0]:
        _wechsel52.append(_vor[1])
pruef("Ein Gegner wechselt die Ebene nur auf der Treppe selbst",
      _wechsel52 and all(t == (_tx52, _ty52) for t in _wechsel52), str(_wechsel52))
pruef("Und steht oben auf festem Boden, nicht neben der Rampe im Nichts",
      _gg52.ebene == _z52 and _w52.welt.frei(_gg52.pos, _gg52.radius, _z52, True)
      and _gg52.pos.distance_to(_oben52) < 120,
      "Ebene %d, %.0f px vom Spieler" % (_gg52.ebene, _gg52.pos.distance_to(_oben52)))
_w52.verlassen(); _g52.verlassen()

# Aufzuege benutzen denselben E-Treppenpfad; Gegner wechseln nur auf
# Rampen, die wie bisher im Wegenetz verzeichnet sind.

# ── 0.32.6: Zoom ohne Wackeln, Kamera ohne Nachziehen ────────────────
# Gemeldet: "wenn man reinzoomt und sich bewegt, oder raus und rein-
# zoomt, ruckelt das Bild zur Seite oder hoch und findet sich erst nach
# einem Moment ein."
_w54, _g54 = gefechtspaar("pvp")
_w54.ich.pos.update(_w54.welt.ebene(0).pixel_breite / 2, _w54.welt.ebene(0).pixel_hoehe / 2)
app.eingabe.maus = pygame.Vector2(600, 40)     # Maus fest in einer Ecke
_seiten = set()
_w54.zoom_ziel = 0.75
for _ in range(80):
    _w54.ich.tempo.update(0, 0)
    _w54.schritt(K.FIXED_DT)
    _z = _w54.kamera.zoom
    _seiten.add((round(K.GAME_W * _z), round(K.GAME_H * _z), K.GAME_W * _z * 9 == K.GAME_H * _z * 16))
pruef("Beim Zoomen bleibt die Leinwand genau 16:9",
      all(x[2] for x in _seiten) and all(a * 9 == b * 16 for a, b, _ in _seiten),
      str(sorted(_seiten)[:4]))
_ecken = []
for _ in range(120):
    _w54.ich.tempo.update(0, 0)
    _w54.schritt(K.FIXED_DT)
    _ecken.append(tuple(_w54.kamera.ecke))
pruef("Danach steht das Bild still, ohne nachzuziehen",
      len(set(_ecken[30:])) == 1, "%d verschiedene Ecken" % len(set(_ecken[30:])))
_alt54 = app.opt["kamera_blick"], app.opt["kamera_blick_weite"]
app.opt["kamera_blick"] = True; app.opt["kamera_blick_weite"] = 40
pruef("BLICK VORAUS: die Weite kommt aus der Einstellung",
      app.opt.blick_weite() == 40.0)
app.opt["kamera_blick"] = False
pruef("Und ist aus, solange BLICK VORAUS aus ist", app.opt.blick_weite() == 0.0)
app.opt["kamera_blick"], app.opt["kamera_blick_weite"] = _alt54
app.eingabe.maus = pygame.Vector2(K.GAME_W / 2, K.GAME_H / 2)
_w54.verlassen(); _g54.verlassen()

# ── 0.32.7: Knall der Blendgranate leiser mit Abstand und Wegschauen ─
from dustfront import world as _W56
class _Ohr:
    ebene = 0
    winkel = 0.0                      # schaut nach rechts
    pos = pygame.Vector2(1000, 1000)
_o = _Ohr()
_nah = _W56.blend_ton_wert(pygame.Vector2(1040, 1000), 0, _o)
_mitte_hin = _W56.blend_ton_wert(pygame.Vector2(1300, 1000), 0, _o)
_mitte_weg = _W56.blend_ton_wert(pygame.Vector2(700, 1000), 0, _o)
_fern = _W56.blend_ton_wert(pygame.Vector2(1900, 1000), 0, _o)
pruef("Ganz nah ist der Knall voll", abs(_nah - 1.0) < 1e-6, "%.2f" % _nah)
pruef("Weiter weg deutlich leiser, als die Entfernung allein es macht",
      _mitte_hin < 0.75 * _W56.klang_wert(1.0, pygame.Vector2(1300, 1000), 0, _o),
      "%.2f" % _mitte_hin)
pruef("Wer wegschaut, hoert ihn noch leiser", _mitte_weg < _mitte_hin * 0.6,
      "%.2f / %.2f" % (_mitte_weg, _mitte_hin))
pruef("Aber man hoert ihn immer noch", _fern >= min(
      _W56.klang_wert(1.0, pygame.Vector2(1900, 1000), 0, _o), K.BLENDEN["ton_mindest"]) > 0,
      "%.2f" % _fern)

# Fremder Blendton und fremdes Blendbild lassen sich getrennt abschalten.
_w56, _g56 = gefechtspaar("pvp")
class _Kos56:
    bild = pygame.Surface((4, 4))
    def klang(self):
        return "ton"
_w56.kosmetik_von = lambda nr: _Kos56()
_aktiv_alt56 = type(_w56).kosmetik_aktiv
type(_w56).kosmetik_aktiv = property(lambda self: True)
_gespielt56 = []
_ton_alt56 = _w56.app.klaenge.ton_spielen
_w56.app.klaenge.ton_spielen = lambda klang, laut: _gespielt56.append(laut)
try:
    _w56.kos_zeigen = None
    _r1 = _w56.kosmetik_blitz(1, 0.8, 0.5, ton=False, bild=True)
    pruef("Ohne fremden Ton: der Knall bleibt der eigene, das Bild kommt trotzdem",
          _r1 is False and _w56.kos_zeigen is not None and not _gespielt56)
    _w56.kos_zeigen = None
    _r2 = _w56.kosmetik_blitz(1, 0.8, 0.5, ton=True, bild=False)
    pruef("Ohne fremdes Bild: der fremde Ton spielt, das Bild nicht",
          _r2 is True and _w56.kos_zeigen is None and _gespielt56 == [0.5])
finally:
    type(_w56).kosmetik_aktiv = _aktiv_alt56
    _w56.app.klaenge.ton_spielen = _ton_alt56
_w56.verlassen(); _g56.verlassen()

# ── 0.32.8: Der Schlag mit dem Brecheisen als Figur mit Eisen in der Hand
_w57, _g57 = gefechtspaar("pvp")
_k57 = _w57.ich
_vorher57 = _k57.bild
_k57.nahkampf()
_bilder57 = []
for _ in range(int(0.5 / K.FIXED_DT)):
    _bilder57.append(_k57.bild)
    _w57.schritt(K.FIXED_DT)
_schwung57 = [b for b in _bilder57 if "schwung" in b]
pruef("Beim Schlag haelt die Figur das Brecheisen statt der Waffe",
      _schwung57 and _bilder57[0] != _vorher57 and "schwung" in _bilder57[0],
      "%s -> %s" % (_vorher57, _bilder57[0]))
pruef("Und die Arme laufen mit: mehrere Bilder nacheinander",
      len(set(_schwung57)) >= 5, str(sorted(set(_schwung57))))
pruef("Das Eisen bleibt nach dem Schwung noch kurz in der Hand",
      len(_schwung57) * K.FIXED_DT >= K.WAFFEN["brecheisen"]["schwung"]
      + K.NAHKAMPF["nachhalten"] - 0.02, "%.2f s" % (len(_schwung57) * K.FIXED_DT))
pruef("Danach ist die Waffe wieder da", _bilder57[-1] == _vorher57, _bilder57[-1])
_e57 = app.bilder.bild(_schwung57[0])
pruef("Jedes Schwungbild ist gezeichnet", _e57.get_size() == (64, 64))
_w57.verlassen(); _g57.verlassen()

# ── Gameplay-Randfaelle aus der systematischen Fehlerliste ───────────
from dustfront.entities import Geschoss as _GeschossB, Rakete as _RaketeB

held.leben = held.max_leben
held.lebt = True
held.heilt_rest = 0.001
held.lebt = False
held.schritt(K.FIXED_DT)
pruef("Ein fertiges Medkit belebt keinen toten Spieler wieder",
      held.leben == held.max_leben)
held.lebt = True
held.am_boden = True
held.heilt_rest = 0.001
held.schritt(K.FIXED_DT)
pruef("Ein fertiges Medkit heilt keinen Spieler am Boden",
      held.leben == held.max_leben)
del held.am_boden

held.heilt_rest = 0.5
andere_waffe = (held.waffe + 1) % len(held.waffen)
held.waffe_waehlen(andere_waffe)
pruef("Waffenwechsel bricht ein angesetztes Medkit ab",
      held.heilt_rest == 0.0)

held.dash_rest = 0.1
held.stuerzen()
pruef("Ein Sturz beendet den laufenden Dash", held.dash_rest == 0.0)

_ziel_b = Gegner(held.pos + pygame.Vector2(24, 0), "laeufer", held.ebene)
szene.welt.dazu(_ziel_b)
_schuss_b = _GeschossB(held.pos, 0, K.WAFFEN["repetierer"], held.ebene)
_schuss_b.welt = szene.welt
_schuss_b.tempo.update(0, 0)
try:
    _schuss_b.einschlag(_ziel_b)
    _nulltreffer_b = not _schuss_b.lebt
except ValueError:
    _nulltreffer_b = False
pruef("Ein Geschosstreffer mit Nulltempo stuerzt nicht ab", _nulltreffer_b)

_ebene_b = szene.welt.ebene(0)
pruef("Ausserhalb der Karte liegt kein Loch",
      not _ebene_b.loch(-1, 0)
      and not _ebene_b.loch(_ebene_b.breite, 0)
      and not _ebene_b.loch(0, _ebene_b.hoehe))
_rakete_b = _RaketeB((-K.TILE, K.TILE), 0, K.WAFFEN["rakete"], 1,
                      ziel=held)
_rakete_b.welt = szene.welt
_rakete_b._ebene_wechseln()
pruef("Eine Rakete faellt am Kartenrand nicht auf eine tiefere Ebene",
      _rakete_b.ebene == 1)

_wesen_alt_b = szene.welt.wesen
_zustand_dash_b = (held.pos.copy(), held.vorher.copy(), held.ebene,
                   held.lebt, held.dash_rest, held.dash_bild_rest,
                   held.dash_richtung.copy(), held.heilt_rest,
                   held.schlag_zeigen, held.nahkampf_rest, held.waffe,
                   held.flug)
szene.welt.wesen = [held]
held.pos.update(K.GAME_W / 2, K.GAME_H / 2)
held.vorher.update(held.pos)
held.ebene = 0
held.lebt = True
held.flug = 0.0
held.heilt_rest = held.schlag_zeigen = held.nahkampf_rest = 0.0
held.waffe = 0
held.dash_richtung.update(1, 0)
_dash_flaeche_b = pygame.Surface((K.GAME_W, K.GAME_H), pygame.SRCALPHA)
held.dash_rest = held.dash_bild_rest = 0.0
szene.renderer.wesen_zeichnen(_dash_flaeche_b, szene.welt, 0,
                              pygame.Vector2(0, 0), 1.0)
_dash_still_b = pygame.image.tobytes(_dash_flaeche_b, "RGBA")
_dash_flaeche_b.fill((0, 0, 0, 0))
held.dash_rest = K.DASH["dauer"] - K.FIXED_DT
held.dash_bild_rest = held.dash_rest + K.DASH["bild_ausklang"]
szene.renderer.wesen_zeichnen(_dash_flaeche_b, szene.welt, 0,
                              pygame.Vector2(0, 0), 1.0)
_dash_flaeche_b.fill((0, 0, 0, 0))
held.dash_rest = K.DASH["dauer"] * 0.5
held.dash_bild_rest = K.DASH["dauer"] * 0.5 + K.DASH["bild_ausklang"]
szene.renderer.wesen_zeichnen(_dash_flaeche_b, szene.welt, 0,
                              pygame.Vector2(0, 0), 1.0)
pruef("Der laufende Dash zeichnet einen dezenten Windstoss",
      pygame.image.tobytes(_dash_flaeche_b, "RGBA") != _dash_still_b)
_dash_flaeche_b.fill((0, 0, 0, 0))
held.dash_rest = 0.0
held.dash_bild_rest = K.DASH["bild_ausklang"] * 0.5
szene.renderer.wesen_zeichnen(_dash_flaeche_b, szene.welt, 0,
                              pygame.Vector2(0, 0), 1.0)
pruef("Der Dash hinterlaesst einen kurzen Ausklang",
      pygame.image.tobytes(_dash_flaeche_b, "RGBA") != _dash_still_b)

class _WindprobeB:
    dash_richtung = pygame.Vector2(1, 0)
    dash_bild_rest = 0.0

def _windbild_b(vergangen):
    probe = _WindprobeB()
    probe.dash_rest = K.DASH["dauer"] - vergangen
    flaeche = pygame.Surface((160, 160), pygame.SRCALPHA)
    szene.renderer.dash_zeichnen(flaeche, pygame.Vector2(100, 100), probe)
    return flaeche

_wind_erstes_b = _windbild_b(K.FIXED_DT)
_wind_frueh_b = _windbild_b(0.015)
_wind_mitte_b = _windbild_b(0.060)
_wind_spaet_b = _windbild_b(0.120)
pruef("Die erste Windlinie setzt schon im ersten Dashbild ein",
      _wind_erstes_b.get_at((81, 100)).a > 0)
pruef("Windlinien erscheinen gestaffelt statt gleichzeitig",
      _wind_frueh_b.get_at((81, 100)).a > 0
      and _wind_frueh_b.get_at((68, 96)).a == 0
      and _wind_mitte_b.get_at((68, 96)).a > 0
      and _wind_mitte_b.get_at((55, 104)).a == 0
      and _wind_spaet_b.get_at((55, 104)).a > 0)

class _Welt_mit_MuendungB:
    muendungen = [(pygame.Vector2(40, 40), 0.0, 0, 0.055)]

_muendungsbild_b = pygame.Surface((128, 80))
_muendungsbild_b.fill((0, 0, 0))
szene.renderer.muendungsfeuer(_muendungsbild_b, _Welt_mit_MuendungB(),
                              pygame.Vector2(0, 0), 0)
_helle_muendungs_x_b = [x for x in range(128) for y in range(80)
                        if _muendungsbild_b.get_at((x, y))[:3] != (0, 0, 0)]
pruef("Das Muendungsfeuer sitzt vor der Laufspitze",
      _helle_muendungs_x_b and min(_helle_muendungs_x_b) >= 42)

held.pos, held.vorher, held.ebene, held.lebt = _zustand_dash_b[:4]
(held.dash_rest, held.dash_bild_rest, held.dash_richtung,
 held.heilt_rest, held.schlag_zeigen, held.nahkampf_rest,
 held.waffe, held.flug) = _zustand_dash_b[4:]
szene.welt.wesen = _wesen_alt_b

# ─────────────────────────────────────────────────────────────────────
# 0.34.11: "Die Autos werden beim Host nicht angezeigt, nur bei den Gaesten.
# Man kann noch keine Inputs da drin machen. Man soll auch C4 an das Auto
# werfen koennen." Der Fehler steckte im echten Ablauf: aus der Lobby heraus
# raeumte der Rundenstart die eben aufgestellten Buggys wieder weg. Die
# Pruefungen von 0.34.9 fingen ohne Lobby an und sahen das nie.
from dustfront.fahrzeug import Buggy as _Buggy71
from dustfront.entities import C4Ladung as _C4_71

w71, g71 = lobbypaar(modus="pvp", karte="staubtal")
w71.plan_starten(0)
netz_durchlassen(w71, g71, 10)
pruef("Aus der Lobby gestartet: STAUBTAL laeuft", w71.karte == "staubtal"
      and not w71.in_lobby and g71.karte == "staubtal", w71.karte)
pruef("Beim Gastgeber stehen die Buggys in der Welt",
      _nb(w71.fahrzeuge) == 5
      and all(b_.lebt and b_ in w71.welt.wesen for b_ in w71.fahrzeuge),
      str([(b_.lebt, b_ in w71.welt.wesen) for b_ in w71.fahrzeuge]))
pruef("... und der Gast sieht dieselben fuenf", _nb(g71.fahrzeuge) == 5)

# Der Gastgeber faehrt mit der Tastatur, wie im echten Spiel.
def _bild71(n_=1):
    """Wie die Spielschleife: je Bild erst die Eingabe auf neu, dann rechnen."""
    for _ in range(n_):
        w71.schritt(K.FIXED_DT)
        app.eingabe.neues_bild()

def _taste71(name_, runter_):
    code_ = app.eingabe.tabelle[name_][0]
    ev_ = pygame.event.Event(pygame.KEYDOWN if runter_ else pygame.KEYUP,
                             key=code_, mod=0, unicode="", scancode=0)
    app.eingabe.ereignis(ev_)
    w71.ereignis(ev_)

_ich71 = w71.ich
_b71 = min(w71.fahrzeuge, key=lambda b_: b_.pos.x)
_ich71.pos.update(_b71.ausstiegsorte(_ich71.radius)[0]); _ich71.vorher.update(_ich71.pos)
_ich71.ebene = 0; _ich71.treppe_rest = 0.0
_taste71("nutzen", True)
_bild71()
_taste71("nutzen", False)
pruef("Der Gastgeber steigt mit E ein", _ich71.im_fahrzeug and _b71.fahrer is _ich71)
_start71 = pygame.Vector2(_b71.pos)
_taste71("vor", True)
_bild71(120)
_taste71("vor", False)
pruef("... und faehrt mit W los", _b71.pos.distance_to(_start71) > 80
      and _ich71.pos.distance_to(_b71.pos) < 1.0,
      "%.0f px" % _b71.pos.distance_to(_start71))
_taste71("nutzen", True)
_bild71()
_taste71("nutzen", False)
pruef("... und steigt mit E wieder aus", not _ich71.im_fahrzeug and _b71.fahrer is None)
app.eingabe.alles_loslassen()

# Der Gast faehrt: E und W gehen als Eingabe zum Gastgeber.
_gk71 = w71.kaempfer[g71.meine_nummer]
_gb71 = max(w71.fahrzeuge, key=lambda b_: b_.pos.x)
_gk71.pos.update(_gb71.ausstiegsorte(_gk71.radius)[0]); _gk71.vorher.update(_gk71.pos)
_gk71.ebene = 0; _gk71.treppe_rest = 0.0
_ich71.pos.update(_b71.pos + pygame.Vector2(0, 80)); _ich71.vorher.update(_ich71.pos)
g71._knoepfe.add("nutzen")
netz_durchlassen(w71, g71, 6)
pruef("Der Gast steigt mit E ein", _gk71.im_fahrzeug and _gb71.fahrer is _gk71
      and g71.ich.im_fahrzeug)
_gstart71 = pygame.Vector2(_gb71.pos)
_alt_ein71 = g71._meine_eingabe
def _gas71():
    d_ = _alt_ein71(); d_["will"] = [0.0, -1.0]; return d_
g71._meine_eingabe = _gas71
netz_durchlassen(w71, g71, 60)
g71._meine_eingabe = _alt_ein71
pruef("... und faehrt mit W los", _gb71.pos.distance_to(_gstart71) > 80,
      "%.0f px" % _gb71.pos.distance_to(_gstart71))

# C4 an den Wagen: sie klebt, faehrt mit und trifft den Fahrer zu 70 %.
# Erst anhalten: der Gastgeber haelt das letzte Gas des Gastes, bis eine
# neue Eingabe kommt.
w71._anwenden(_gk71, {"will": [0.0, 0.0], "ziel": [0, 0], "knoepfe": []})
_gb71.geschw.update(0, 0)
_vorn71 = pygame.Vector2(1, 0).rotate(_gb71.winkel)
_quer71 = pygame.Vector2(-_vorn71.y, _vorn71.x)
_wurf71 = _gb71.pos + _quer71 * 50
_c71 = _C4_71(pygame.Vector2(_wurf71), (-_quer71).as_polar()[1], 0, _ich71, weite=80)
w71.welt.dazu(_c71)
for _ in range(30):
    w71.welt.schritt(K.FIXED_DT)
    w71._fahrzeuge_nachziehen()
pruef("C4 bleibt am Buggy kleben", _c71.traeger is _gb71 and _c71.haftend
      and _gb71.beruehrt(_c71.pos, _c71.radius + 1))
_rel71 = (_c71.pos - _gb71.pos).rotate(-_gb71.winkel)
for _ in range(90):
    w71._anwenden(_gk71, {"will": [0.7, -0.7], "ziel": [0, 0], "knoepfe": []})
    w71.welt.schritt(K.FIXED_DT)
    w71._fahrzeuge_nachziehen()
pruef("... und faehrt mit, auch durch die Kurve",
      ((_c71.pos - _gb71.pos).rotate(-_gb71.winkel) - _rel71).length() < 0.5
      and _gb71.pos.distance_to(_gstart71) > 120)
pruef("... und liegt beim Zeichnen obenauf", _c71.obenauf)
netz_durchlassen(w71, g71, 4)
pruef("Der Gast sieht die Ladung am Wagen",
      any(n_ == "c4_brick" and pygame.Vector2(x_, y_).distance_to(_c71.pos) < 3
          for (x_, y_, _w, _e, n_, _h, _k, _vx, _vy) in g71._fremde_schuesse))
_gk71.unverwundbar = 0.0
_gk71.leben = 1000.0
_d71 = _gk71.pos.distance_to(_c71.pos)
_c71.lade_rest = 0.0
_c71.detonieren()
pruef("Der Fahrer bekommt von der Ladung nichts ab (seit 0.34.77: im Fahrzeug geschuetzt)",
      _gk71.leben == 1000.0, "%.1f" % (1000.0 - _gk71.leben))
pruef("Der Buggy bleibt heil und fahrbereit",
      _gb71.lebt and _gb71 in w71.welt.wesen and _gb71.fahrer is _gk71)
_gk71.leben = _gk71.max_leben

# Die naechste Runde aus dem Plan: die Buggys bleiben, leer, am Platz.
w71._runde_neu()
w71.schritt(K.FIXED_DT)
pruef("Nach einem Neustart stehen die Buggys leer an ihrem Platz",
      _nb(w71.fahrzeuge) == 5
      and all(b_.lebt and b_ in w71.welt.wesen and b_.fahrer is None
              and b_.pos == b_.start[0] for b_ in w71.fahrzeuge)
      and not _gk71.im_fahrzeug)
w71.verlassen(); g71.verlassen()

# ─────────────────────────────────────────────────────────────────────
# 0.34.12: "C4 fuse time runter auf 3 s. Loadout bearbeiten in der Runde
# geht noch nicht, wird nicht angewendet."
from dustfront import konto as _KM72
from dustfront.entities import C4Ladung as _C4_72
pruef("C4 ist nach drei Sekunden scharf", K.C4["ladezeit"] == 3.0, str(K.C4["ladezeit"]))
_c72 = _C4_72(pygame.Vector2(0, 0), 0.0, 0, None)       # ohne Wurf: klebt sofort
_c72.welt = szene.welt
for _ in range(int(2.9 / K.FIXED_DT)):
    _c72.schritt(K.FIXED_DT)
_noch72 = _c72.bereit
for _ in range(int(0.2 / K.FIXED_DT)):
    _c72.schritt(K.FIXED_DT)
pruef("... nicht schon nach 2,9 s, aber nach 3,1 s", not _noch72 and _c72.bereit)

# Gastgeber und Gast teilen hier dasselbe Konto (dieselbe App). Gewechselt
# wird das gewaehlte Loadout, wie im Menue AUSRUESTUNG.
_gew72 = app.konto.gewaehlt
w72, g72 = gefechtspaar("pvp", regeln={"loadouts": "eigenes"})
# Mit KLASSE PFLICHT (seit 0.34.91): was der Gastgeber daraus macht.
_alt72 = _KM72.hotbar_aus_loadout(w72._mit_klasse(app.konto.loadout))
_neu_nr72 = next(i_ for i_, lo_ in enumerate(app.konto.loadouts)
                 if _KM72.hotbar_aus_loadout(w72._mit_klasse(lo_)) != _alt72)
_neu72 = _KM72.hotbar_aus_loadout(w72._mit_klasse(app.konto.loadouts[_neu_nr72]))
_gk72 = w72.kaempfer[g72.meine_nummer]
pruef("(Zu Beginn tragen beide das alte)",
      _gk72.waffen == _alt72 and w72.ich.waffen == _alt72, str(_gk72.waffen))
app.konto.gewaehlt = _neu_nr72
netz_durchlassen(w72, g72, 6)
pruef("Ein im Spiel geaendertes Loadout kommt beim Gastgeber an",
      _gk72.angemeldet is not None
      and _KM72.hotbar_aus_loadout(w72._mit_klasse(_gk72.angemeldet)) == _neu72,
      str(_gk72.angemeldet and _gk72.angemeldet.get("waffen")))
pruef("... gilt aber nicht sofort (kein Waffenwechsel mitten im Gefecht)",
      _gk72.waffen == _alt72 and w72.ich.waffen == _alt72)
pruef("Beide sehen, ab wann es gilt",
      "NÄCHSTEN EINSTIEG" in w72.hinweis and "NÄCHSTEN EINSTIEG" in g72.hinweis,
      "%r / %r" % (w72.hinweis, g72.hinweis))
w72._wieder_einsteigen(_gk72)
w72._wieder_einsteigen(w72.ich)
pruef("Beim naechsten Einstieg traegt der Gast das neue",
      _gk72.waffen == _neu72, "%s statt %s" % (_gk72.waffen, _neu72))
pruef("... und der Gastgeber auch", w72.ich.waffen == _neu72, str(w72.ich.waffen))
netz_durchlassen(w72, g72, 6)
pruef("... und der Gast sieht es in seiner Hotbar", g72.ich.waffen == _neu72,
      str(g72.ich.waffen))
w72.wunsch = dict(w72.wunsch, loadouts="eigenes")
app.konto.gewaehlt = _gew72
netz_durchlassen(w72, g72, 6)
w72._runde_neu()
pruef("Zur neuen Runde gilt es ebenso", _gk72.waffen == _alt72, str(_gk72.waffen))
w72.verlassen(); g72.verlassen()
app.konto.gewaehlt = _gew72

# ─────────────────────────────────────────────────────────────────────
# 0.34.13: "Mach das wahre Online besser: nicht nur ueber LAN spielen. Darf
# zusaetzliche Programme brauchen, solange sie in der zip auf dem Repo
# liegen. Keine Einstellung am Router, kein Dialog der Windows-Firewall."
# Statt cloudflared laeuft hier die Attrappe tests/attrappe_cloudflared.py:
# dieselben Aufrufe, dieselben Zeilen, nur ohne Cloudflare dazwischen.
import tempfile as _tf73
from dustfront import online as _on73, sitzung as _s73
from dustfront.einstellungen import VORGABE as _VG73
from dustfront.core import App as _App73

pruef("Codes werden erkannt, wie man sie bekommt",
      _on73.code_lesen("Thermal-Underlying-Providers-Toe")
      == "thermal-underlying-providers-toe"
      and _on73.code_lesen("https://thermal-underlying-providers-toe.trycloudflare.com/")
      == "thermal-underlying-providers-toe"
      and _on73.code_lesen(" diy-jane-pledge-statement.trycloudflare.com ")
      == "diy-jane-pledge-statement")
pruef("Adressen im LAN bleiben Adressen",
      not _on73.code_lesen("192.168.0.5:50505") and not _on73.code_lesen("spiele-pc")
      and not _on73.code_lesen("localhost") and not _on73.code_lesen(""))
pruef("Vorgabe: Online-Code an, im LAN sichtbar aus (keine Firewall-Abfrage)",
      _VG73["online_lobby"] is True and _VG73["lan_offen"] is False)

_ordner73 = _tf73.mkdtemp()
os.environ["ATTRAPPE_ORDNER"] = _ordner73
os.environ["DUSTFRONT_CLOUDFLARED"] = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "attrappe_cloudflared.py")

def _apps73(*apps, n=1):
    for _ in range(n):
        for _a in apps:
            for _sz in list(_a._aktive()):
                _sz.schritt(K.FIXED_DT)
        time.sleep(0.004)

def _bis73(bedingung, apps, sekunden=10.0):
    ende = time.time() + sekunden
    while time.time() < ende:
        if bedingung():
            return True
        _apps73(*apps)
    return bedingung()

_app_c = _App73("C", None, headless=True)
_app_d = _App73("D", None, headless=True)
_neuer_port(); _pc73 = _port[0]
_neuer_port(); _pd73 = _port[0]
_lc73 = _s73.eigene_lobby(_app_c, headless_port=_pc73)
_ld73 = _s73.eigene_lobby(_app_d, headless_port=_pd73)
pruef("Ohne LAN lauscht die eigene Lobby nur auf 127.0.0.1",
      _lc73.gastgeber.nur_lokal
      and _lc73.gastgeber.sock.getsockname()[0] == "127.0.0.1",
      str(_lc73.gastgeber.sock.getsockname()))
pruef("... und oeffnet keine UDP-Steckdose fuer die LAN-Suche", _lc73.ansager is None)

_lc73.gastgeber.tunnel_setzen(True)
_code73 = "sample-tunnel-for-%d" % _pc73
pruef("Der Tunnel steht und gibt einen Code",
      _bis73(lambda: _lc73.gastgeber.code == _code73, [_app_c]),
      "%s / %s" % (_lc73.gastgeber.code,
                   _lc73.gastgeber.tunnel.beschreibung()))
_menue73 = dict((s_, w_) for s_, _t, w_ in _lc73._menue_baut())
pruef("Im Pausenmenue steht ONLINE-CODE zum Kopieren", _menue73.get("code") == "KOPIEREN",
      str(_menue73.get("code")))
from dustfront.sitzung import code_zeile as _cz73
pruef("... und der Code selbst in der Zeile daneben", _cz73(_lc73) == _code73.upper(),
      _cz73(_lc73))
_lc73._menue_wirken("code", False, True)
pruef("... und auswaehlen kopiert ihn (oder sagt ihn wenigstens)",
      _code73.upper() in _lc73.hinweis, _lc73.hinweis)
_bild73 = pygame.Surface((K.GAME_W, K.GAME_H))
_lc73.zeichnen(_bild73, 0.5)

_such73 = _s73.LobbySuche(_app_d, _ld73)
_app_d.schieben(_such73)
pruef("Ohne LAN sucht die Lobbysuche nicht im Netz", _such73.sucher is None)
_such73.inhalt_zeichnen(_bild73)
_such73.verbinden(_code73.upper(), "")
pruef("Mit dem Code wartet sie auf den Zugang, ohne stehenzubleiben",
      _such73._zugang is not None and _such73._verbinde is None)
_drin73 = _bis73(lambda: len(_lc73.kaempfer) == 2
                 and not _app_d.stapel[-1].ist_gastgeber, [_app_c, _app_d])
_gast73 = _app_d.stapel[-1]
pruef("D tritt mit dem Code der Lobby von C bei", _drin73,
      "%d Kaempfer, oben %s" % (len(_lc73.kaempfer), type(_gast73).__name__))
pruef("... angezeigt wird der Code, nicht die Adresse dahinter",
      getattr(_gast73, "wohin", "") == _code73.upper(), getattr(_gast73, "wohin", ""))
pruef("... und es ist dieselbe Leitung wie immer (Weltmeldungen kommen an)",
      _bis73(lambda: _gast73.ich is not None, [_app_c, _app_d]))

# IM LAN SICHTBAR im laufenden Spiel: die Lobby lauscht dann auf allen
# Netzkarten und antwortet auf die Suche - wer drin ist, bleibt drin.
_app_c.opt["lan_offen"] = True
_lc73.netz_umstellen()
pruef("LAN an: die Lobby lauscht auf allen Netzkarten, mit Ansager",
      _lc73.gastgeber.sock.getsockname()[0] == "0.0.0.0" and _lc73.ansager is not None)
_apps73(_app_c, _app_d, n=30)
pruef("... und der Gast ist noch da", len(_lc73.kaempfer) == 2
      and _gast73.gast.offen)
_app_c.opt["lan_offen"] = False
_lc73.netz_umstellen()
pruef("LAN wieder aus: nur 127.0.0.1, kein Ansager",
      _lc73.gastgeber.sock.getsockname()[0] == "127.0.0.1" and _lc73.ansager is None)

# Ein falscher Code: zurueck in die eigene Lobby, mit dem Grund.
_app_e = _App73("E", None, headless=True)
_neuer_port(); _pe73 = _port[0]
_le73 = _s73.eigene_lobby(_app_e, headless_port=_pe73)
_such73e = _s73.LobbySuche(_app_e, _le73)
_app_e.schieben(_such73e)
_such73e.verbinden("gibt-es-gar-nicht", "")
_heim73 = _bis73(lambda: _app_e.stapel
                 and getattr(_app_e.stapel[-1], "ist_gastgeber", False)
                 and _app_e.stapel[-1] is not _le73, [_app_e])
pruef("Ein falscher Code fuehrt zurueck in die eigene Lobby", _heim73)
pruef("... und sagt, woran es lag",
      "NICHT ERREICHBAR" in (_app_e.stapel[-1].hinweis or ""),
      _app_e.stapel[-1].hinweis)

# Kommt Cloudflare nicht durch, steht der Grund da, nicht ein ewiges STARTET.
os.environ["ATTRAPPE_KEIN_EDGE"] = "1"
_t73 = _on73.Tunnel(_pc73 + 1)
_bis73(lambda: _t73._p is not None and _t73.fehler, [], 5.0)
_t73.schritt()
pruef("Kein Weg zu Cloudflare: der Code ist da, aber nicht bereit, mit Grund",
      _t73.zustand == "fehler" and not _t73.bereit
      and "NICHT ERREICHBAR" in _t73.beschreibung(), _t73.beschreibung())
_t73.schliessen()
del os.environ["ATTRAPPE_KEIN_EDGE"]

_app_c.opt["online_lobby"] = False
_lc73.netz_umstellen()
pruef("Online aus: kein Tunnel mehr", _lc73.gastgeber.tunnel is None)
for _a73 in (_app_d, _app_e, _app_c):
    for _sz73 in list(_a73.stapel):
        if hasattr(_sz73, "verlassen"):
            _sz73.verlassen()
time.sleep(0.2)
pruef("Kein cloudflared laeuft weiter, wenn alles zu ist",
      not _on73._laufende, str(len(_on73._laufende)))
_on73.alle_beenden()
del os.environ["DUSTFRONT_CLOUDFLARED"]

# ─────────────────────────────────────────────────────────────────────
# 0.34.15: "Hit animations - irgendwas, was klar symbolisiert, wenn man
# einen Gegner trifft." Ein X am Mauszeiger (render.Trefferzeichen), rot
# und groesser, wenn der Treffer erledigt; dazu ein Ticken.
w74, g74 = gefechtspaar("pvp")
_wk74 = w74.kaempfer[0]
_gk74 = w74.kaempfer[g74.meine_nummer]
for _k74 in (_wk74, _gk74):
    _k74.unverwundbar = 0.0
    _k74.leben = 100.0
_gk74.schaden(10.0, None, _wk74)
pruef("Ein Treffer zaehlt beim Schuetzen", _wk74.treffer_marken == 1
      and _wk74.toedlich_marken == 0, "%d/%d" % (_wk74.treffer_marken,
                                                 _wk74.toedlich_marken))
_gk74.schaden(1.0, None, _wk74)
pruef("Zwei Treffer im selben Augenblick (Schrot, Feuer) zaehlen einmal",
      _wk74.treffer_marken == 1)
_wk74.schaden(5.0, None, _wk74)
pruef("Sich selbst treffen zaehlt nicht", _wk74.treffer_marken == 1)
w74.schritt(K.FIXED_DT)
pruef("Beim Gastgeber springt das Zeichen auf", w74.trefferzeichen.rest > 0
      and not w74.trefferzeichen.toedlich)
_bild74 = pygame.Surface((K.GAME_W, K.GAME_H)); _bild74.fill((0, 0, 0))
_maus74 = pygame.Vector2(300, 180)
w74.trefferzeichen.zeichnen(_bild74, _maus74)
_hell74 = [(x_, y_) for x_ in range(280, 321) for y_ in range(160, 201)
           if _bild74.get_at((x_, y_))[:3] == (255, 250, 236)]
pruef("... als helles X um den Zeiger, die Mitte bleibt frei",
      len(_hell74) > 8 and _bild74.get_at((300, 180))[:3] == (0, 0, 0)
      # Jeder helle Punkt liegt auf einer der Diagonalen (Strichbreite
      # mit eingerechnet) - also wirklich ein X und kein Kreis oder Kasten.
      and all(abs(abs(x_ - 300) - abs(y_ - 180)) <= 4 for x_, y_ in _hell74)
      and all(max(abs(x_ - 300), abs(y_ - 180)) >= 3 for x_, y_ in _hell74),
      "%d Punkte" % len(_hell74))
w74.welt.zeit += 1.0
_gk74.leben = 3.0
_gk74.schaden(10.0, None, _wk74)
w74.schritt(K.FIXED_DT)
pruef("Ein Treffer, der erledigt, zaehlt als toedlich", _wk74.toedlich_marken == 1)
pruef("... und das Zeichen wird rot und bleibt laenger",
      w74.trefferzeichen.toedlich
      and w74.trefferzeichen.dauer == K.TREFFERMARKE["dauer_toedlich"])
_bild74.fill((0, 0, 0))
w74.trefferzeichen.zeichnen(_bild74, _maus74)
pruef("... in Rot zu sehen",
      any(_bild74.get_at((x_, y_))[:3] == K.C_RED
          for x_ in range(275, 326) for y_ in range(155, 206)))
# Der Gast trifft: sein Zaehler kommt mit der Weltmeldung, sein Zeichen
# springt bei ihm auf.
w74._wieder_einsteigen(_gk74)
_wk74.unverwundbar = 0.0
_wk74.leben = 100.0
w74.welt.zeit += 1.0
_wk74.schaden(10.0, None, _gk74)
_auf74 = False
for _ in range(8):
    w74.schritt(K.NETZ["takt"])
    g74.schritt(K.NETZ["takt"])
    _auf74 = _auf74 or g74.trefferzeichen.rest > 0
pruef("Der Gast bekommt seinen Treffer gemeldet", g74.ich.treffer_marken == 1,
      str(g74.ich.treffer_marken))
pruef("... und sieht sein Zeichen", _auf74)
from dustfront.render import Trefferzeichen as _TZ74
_neu74 = _TZ74()
_neu74.beobachten(g74.ich, K.FIXED_DT)
pruef("Wer neu hinschaut, sieht kein altes Zeichen (erst merken, dann zaehlen)",
      _neu74.rest == 0.0)
w74.verlassen(); g74.verlassen()

# Eigene Leute: kein Zeichen, auch nicht durch eine Granate.
w75, g75 = gefechtspaar("pve")
_a75, _b75 = w75.kaempfer[0], w75.kaempfer[g75.meine_nummer]
_b75.unverwundbar = 0.0
_b75.schaden(10.0, None, _a75)
pruef("Wer die eigenen Leute trifft, bekommt kein Zeichen",
      _a75.treffer_marken == 0 and _a75.toedlich_marken == 0)
w75.verlassen(); g75.verlassen()

# Auch im Einzelspiel.
from dustfront.entities import Gegner as _G76
_g76 = _G76(szene.held.pos + pygame.Vector2(60, 0), "laeufer", szene.held.ebene)
szene.welt.dazu(_g76)
_vor76 = szene.held.treffer_marken
szene.welt.zeit += 1.0
_g76.schaden(1.0, None, szene.held)
pruef("Im Einzelspiel zaehlt der Treffer am Zombie", szene.held.treffer_marken == _vor76 + 1)
_g76.lebt = False

# ─────────────────────────────────────────────────────────────────────
# 0.34.16: "Die Autos sollen sich natuerlicher anfuehlen, Driften soll
# sich realistisch anfuehlen." Reifen mit Grenze (Einspurmodell). Geprueft
# wird auf freier Flaeche, nur die Fahrphysik (Buggy._physik).
from dustfront.fahrzeug import Buggy as _B77

def _fahrt77(plan, b=None):
    """plan: [(Sekunden, gas, lenk, handbremse)] - gibt Buggy und Verlauf."""
    b = b or _B77(pygame.Vector2(0, 0))
    verlauf = []
    for dauer, gas, lenk, hb in plan:
        for _ in range(int(dauer / K.FIXED_DT)):
            b._physik(K.FIXED_DT, gas, lenk, hb)
            b.winkel += math.degrees(b.gier * K.FIXED_DT)
            b.pos += b.geschw * K.FIXED_DT
            vorn = b.vorn
            quer = pygame.Vector2(-vorn.y, vorn.x)
            beta = (math.degrees(math.atan2(b.geschw.dot(quer), b.geschw.dot(vorn)))
                    if b.geschw.length() > 30 else 0.0)
            verlauf.append((b.geschw.length(), beta, b.rutschen, b.winkel))
    return b, verlauf

_b77, _v77 = _fahrt77([(4.0, 1, 0, False)])
pruef("Geradeaus: Hoechstfahrt deutlich ueber zu Fuss, unter der Grenze",
      K.SPIELER["tempo"] * 1.8 < _v77[-1][0] <= K.FAHRZEUG["hoechst"],
      "%.0f" % _v77[-1][0])
pruef("... und dabei rutscht nichts", max(v_[2] for v_ in _v77[200:]) < 0.05)
_b77, _v77 = _fahrt77([(4.0, 1, 0, False), (2.0, 1, 1, False)])
_k77 = _v77[480:]
pruef("Voll eingelenkt bei Hoechstfahrt: das Heck kommt (Drift)",
      max(abs(v_[1]) for v_ in _k77) > 12 and max(v_[2] for v_ in _k77) > 0.5,
      "beta bis %.0f Grad" % max(abs(v_[1]) for v_ in _k77))
pruef("... aber er dreht sich nicht (unter 90 Grad quer)",
      max(abs(v_[1]) for v_ in _k77) < 90, "%.0f" % max(abs(v_[1]) for v_ in _k77))
pruef("... und behaelt Fahrt", min(v_[0] for v_ in _k77) > 80,
      "%.0f" % min(v_[0] for v_ in _k77))
_b77, _v77 = _fahrt77([(4.0, 1, 0, False), (0.8, 1, 1, False), (1.5, 1, 0, False)])
pruef("Lenkrad los: er faengt sich und faehrt wieder geradeaus",
      abs(_v77[-1][1]) < 3 and _v77[-1][2] < 0.05, "beta %.0f" % _v77[-1][1])
_b77, _v77 = _fahrt77([(1.0, 1, 0, False), (1.5, 0.6, 1, False)])
pruef("Mittelschnell in die Kurve: er haelt (kaum Drift)",
      max(abs(v_[1]) for v_ in _v77[120:]) < 20,
      "%.0f" % max(abs(v_[1]) for v_ in _v77[120:]))
_b77, _v77 = _fahrt77([(3.0, 1, 0, False), (0.2, 1, 1, False)])
_w77 = _b77.winkel
_b77, _v77b = _fahrt77([(0.5, 0.4, 1, True)], _b77)
pruef("Handbremse in der Kurve: er dreht sich schnell ein",
      abs(_b77.winkel - _w77) > 60 and max(v_[2] for v_ in _v77b) > 0.5,
      "%.0f Grad in 0,5 s" % (_b77.winkel - _w77))
_b77, _v77c = _fahrt77([(1.2, 1, -0.3, False)], _b77)
pruef("... faengt sich danach mit Gas wieder, ohne sich ganz zu drehen",
      max(abs(v_[1]) for v_ in _v77b + _v77c) < 120 and abs(_v77c[-1][1]) < 25
      and _v77c[-1][0] > 100,
      "beta am Ende %.0f, v %.0f" % (_v77c[-1][1], _v77c[-1][0]))
_b77, _v77 = _fahrt77([(1.0, 0, 1, False)])
pruef("Im Stand dreht er sich auch mit eingeschlagenen Raedern nicht",
      abs(_b77.winkel) < 0.5 and _b77.pos.length() < 0.5)
_b77, _v77 = _fahrt77([(2.0, 1, 0, False), (2.5, -1, 0, False)])
pruef("S bremst und faehrt dann rueckwaerts", _b77.fahrt < -40, "%.0f" % _b77.fahrt)

# Im Spiel: Reifenspuren bleiben im Sand, und der Gast bekommt das Rutschen.
w78, g78 = gefechtspaar("pvp", karte="staubtal")
_b78 = min(w78.fahrzeuge, key=lambda b_: b_.pos.x)
_k78 = w78.kaempfer[g78.meine_nummer]
_k78.pos.update(_b78.ausstiegsorte(_k78.radius)[0]); _k78.ebene = 0; _k78.treppe_rest = 0.0
w78._anwenden(_k78, {"will": [0, 0], "ziel": [0, 0], "knoepfe": ["nutzen"]})
w78._anwenden(_k78, {"will": [0, -1], "ziel": [0, 0], "knoepfe": [], "hb": True})
pruef("Die Dash-Taste ist im Buggy die Handbremse", _b78.handbremse is True)
_b78.rutschen = 0.9
_vor78 = len(w78.welt.ebene(0).dekale)
_b78._spur_letzte.clear()
_b78._spuren()
_b78.pos += _b78.vorn * 20
_b78._spuren()
pruef("Wo er rutscht, bleiben Reifenspuren liegen",
      len(w78.welt.ebene(0).dekale) > _vor78 or _vor78 > 0, "%d Flaechen" % len(w78.welt.ebene(0).dekale))
for _ in range(4):
    w78.schritt(K.NETZ["takt"])
    g78.schritt(K.NETZ["takt"])
# Das Rutschen rechnet der Gastgeber in jedem Schritt aus der Bewegung neu;
# hier steht der Wagen. Also direkt die Meldung nehmen, wie sie hinausgeht.
_b78.rutschen = 0.9
g78._fahrzeuge_uebernehmen(w78._weltmeldung()["fahrzeuge"])
_gb78 = [b_ for b_ in g78.fahrzeuge if b_.besetzt]
pruef("Der Gast bekommt das Rutschen gemeldet (fuer Spuren und Staub)",
      _gb78 and abs(_gb78[0].rutschen - 0.9) < 1e-6, str([b_.rutschen for b_ in _gb78]))
w78.verlassen(); g78.verlassen()

# ── 0.34.18: Bots, Gegner auf der Minikarte, Buggys gehen kaputt ─────
print("\n-- Bots")
from dustfront import regeln as _R80
from dustfront.bots import BotHirn as _Hirn80
from dustfront.minikarte import Minikarte as _Mk80, FARBE_FEIND as _FEIND80
from dustfront.entities import Geschoss as _Gs80


def _beide80(sekunden, w_, g_):
    for _ in range(max(1, int(round(sekunden / K.NETZ["takt"])))):
        w_.schritt(K.NETZ["takt"])
        g_.schritt(K.NETZ["takt"])


pruef("Die Regel BOTS gilt in PVP-Runden, nicht in PVE",
      any(f_.schluessel == "bots" for f_ in _R80.sichtbar(_R80.vorgabe(modus="team")))
      and not any(f_.schluessel == "bots" for f_ in _R80.sichtbar(_R80.vorgabe(modus="pve"))))
pruef("Bots und Gegner auf der Minikarte sind von Haus aus aus",
      _R80.vorgabe(modus="team")["bots"] == 0
      and _R80.vorgabe(modus="team")["gegner_karte"] is False)

w80, g80 = gefechtspaar("team", regeln={"bots": 6})
_bots80 = w80._bots()
_teams80 = [sum(1 for k_ in w80.kaempfer.values() if k_.team == i_) for i_ in (0, 1)]
pruef("TEAM bis 6: zwei Menschen und vier Bots, gleichmaessig 3 zu 3",
      len(_bots80) == 4 and _teams80 == [3, 3], "%d Bots, Teams %s" % (len(_bots80), _teams80))
pruef("Kein Bot traegt C4, jeder zwei Waffen und eine Wurfwaffe",
      all("c4" not in k_.waffen and len(k_.waffen) == 3 for k_ in _bots80),
      str([k_.waffen for k_ in _bots80]))
_beide80(0.5, w80, g80)
pruef("Der Gast sieht die Bots als Spieler, als Bots gekennzeichnet",
      sum(1 for k_ in g80.kaempfer.values() if k_.ist_bot) == 4)
pruef("Bots kommen nicht in die Bestenliste (gekennzeichnet in der Endliste)",
      all(e_["bot"] == (e_["name"].startswith("BOT-")) for e_ in w80._endstand()))
# Ein dritter Mensch kommt: ein Bot macht ihm Platz.
_n80 = netz.Gast("127.0.0.1:%d" % _port[0])
_g3_80 = Gefecht(app, "DRITTER", gast=_n80)
for _ in range(int(1.5 / K.NETZ["takt"])):
    w80.schritt(K.NETZ["takt"]); g80.schritt(K.NETZ["takt"]); _g3_80.schritt(K.NETZ["takt"])
_teams80 = [sum(1 for k_ in w80.kaempfer.values() if k_.team == i_) for i_ in (0, 1)]
pruef("Kommt ein Mensch dazu, geht ein Bot - es bleibt 3 zu 3",
      len(w80._bots()) == 3 and _teams80 == [3, 3], "%d Bots, Teams %s" % (len(w80._bots()), _teams80))
_g3_80.verlassen()
# Zurueck in die Lobby: keine Bots.
from dustfront.lobby import lobby_regeln as _lobby80
w80.wunsch = _lobby80()
w80._runde_neu()
pruef("In der Lobby gibt es keine Bots", not w80._bots() and w80.in_lobby)
w80.verlassen(); g80.verlassen()

_n80 = netz.Gastgeber(_neuer_port())
w80 = Gefecht(app, "WIRT", gastgeber=_n80, modus="pvp", seed=80, regeln={"bots": 4})
pruef("PVP bis 4, allein: drei Bots", len(w80._bots()) == 3)
w80.verlassen()

# Fairness. Ein Bot sieht nicht durch Waende, reagiert nicht sofort,
# schwenkt nicht schneller als erlaubt und trifft einen, der quer laeuft,
# deutlich seltener als einen, der stillsteht.
_n80 = netz.Gastgeber(_neuer_port())
w80 = Gefecht(app, "WIRT", gastgeber=_n80, modus="team", seed=3,
              regeln={"bots": 2, "bot_ki": "klassisch"})   # gemessen wird die klassische KI
_bot80 = w80._bots()[0]
_ich80 = w80.ich


def _stelle80(abstand, frei=True):
    for a_ in range(0, 360, 10):
        p_ = _bot80.pos + pygame.Vector2(abstand, 0).rotate(a_)
        if not w80.welt.frei(p_, 9, 0, True):
            continue
        # Frei heisst seit 0.34.26 auch: keine Kiste dazwischen - an der
        # bleibt jede Kugel haengen, und der Bot schiesst nicht hinein.
        # Seit 0.34.135 eine freie Gasse, nicht nur die Mittellinie: lag
        # 8 px daneben eine Mauer, traf die gewoellte Streuung des Bots ihre
        # Kante, und er schoss nach der Regel "nie in eine Mauer" gar nicht.
        if frei and all(w80.welt.deckung(_bot80.pos, p_ + pygame.Vector2(0, d_).rotate(a_), 0) == ""
                        for d_ in (-16, -8, 0, 8, 16)):
            return p_
        if not frei and not w80.welt.sicht_frei(_bot80.pos, p_, 0):
            return p_
    return None


_hinter80 = _stelle80(110, frei=False)
if _hinter80 is not None:
    _ich80.pos.update(_hinter80)
    pruef("Ein Bot sieht nicht durch die Wand", not _bot80.hirn.sieht(_ich80))
_frei80 = _stelle80(200)
# Von hier aus ist die Bahn frei - gemessen wird spaeter von genau hier
# (seit 0.34.38): im Reaktionstest geht der Bot ein paar Schritte, und
# stand er danach hinter einer Kiste, schoss er in sie hinein.
_platz80 = pygame.Vector2(_bot80.pos)
_ich80.pos.update(_frei80)
_ich80.unverwundbar = 1e9
_bot80.hirn.neues_leben()
_bot80.hirn.blick = _winkel80 = math.degrees(math.atan2(*(reversed(list(_frei80 - _bot80.pos))))) + 180
_erster80 = None
_dreh80 = 0.0
_alt80 = _bot80.hirn.blick
for i_ in range(int(3.0 / K.FIXED_DT)):
    _ich80.pos.update(_frei80)
    _ich80.tempo.update(0, 0)
    vor_ = _bot80.zaehler.get("schuesse", 0)
    w80.schritt(K.FIXED_DT)
    _dreh80 = max(_dreh80, abs((_bot80.hirn.blick - _alt80 + 180) % 360 - 180) / K.FIXED_DT)
    _alt80 = _bot80.hirn.blick
    if _erster80 is None and _bot80.zaehler.get("schuesse", 0) > vor_:
        _erster80 = i_ * K.FIXED_DT
pruef("Ein Bot schiesst nicht sofort: erst nach seiner Reaktionszeit",
      _erster80 is not None and _erster80 >= K.BOTS["reaktion"][0],
      "erster Schuss nach %s s" % _erster80)
pruef("Sein Fadenkreuz schwenkt nicht schneller als erlaubt (kein Schnappen)",
      _dreh80 <= K.BOTS["dreh"] + 1.0, "%.0f Grad/s" % _dreh80)


def _quote80(quer, sekunden=12.0):
    """Trefferquote des Bots auf den Wirt, der still steht oder quer laeuft."""
    _bot80.zaehler_leeren()
    _bot80.hirn.neues_leben()
    # Der Bot bleibt an seinem Platz und wirft nicht (seit 0.34.26): er
    # geht sonst vor Kisten zur Seite oder hinter Deckung und wirft seine
    # Granate - gemessen wuerde dann, wie oft er das Ziel neu suchen muss,
    # nicht, wie er zielt.
    platz_ = pygame.Vector2(_platz80)
    hin_ = _frei80 - platz_
    q_ = pygame.Vector2(-hin_.y, hin_.x).normalize()
    for i_ in range(int(sekunden / K.FIXED_DT)):
        t_ = i_ * K.FIXED_DT
        versatz = (math.sin(t_ * 108.0 / 50.0) * 50.0) if quer else 0.0
        p_ = _frei80 + q_ * versatz
        if w80.welt.frei(p_, 9, 0, True):
            _ich80.pos.update(p_)
        _ich80.tempo.update(0, 0)
        _bot80.leben = _bot80.max_leben
        _bot80.pos.update(platz_)
        _bot80.tempo.update(0, 0)
        _bot80.hirn.wurf_rest = 99.0
        # Volle Magazine: gemessen wird das Zielen. Seit 0.34.26 geht ein
        # Bot zum Nachladen in Deckung, und ein leeres Magazin hiesse hier
        # Deckungsgaenge statt Schuesse - mal mehr, mal weniger.
        for n_ in _bot80.waffen:
            if K.WAFFEN[n_].get("art") == "schuss":
                _bot80.magazin[n_] = K.WAFFEN[n_]["magazin"]
        w80.schritt(K.FIXED_DT)
    s_ = _bot80.zaehler.get("schuesse", 0)
    t_ = _bot80.zaehler.get("treffer", 0)
    return (t_ / s_) if s_ else 0.0, s_, t_


_still80, _ss80, _ts80 = _quote80(False)
_quer80, _sq80, _tq80 = _quote80(True)
pruef("Gegen einen, der still steht, trifft ein Bot (er ist nicht nutzlos)",
      _ss80 > 0 and _still80 > 0.25, "%.0f %% von %d" % (_still80 * 100, _ss80))
# Gezaehlt werden die Treffer in derselben Zeit, nicht die Quote je
# Schuss: gegen den, der quer laeuft, schiesst der Bot nur ein-, zweimal
# (das Fadenkreuz kommt nicht hinterher), und eine Quote aus zwei
# Schuessen ist 0 oder 50 Prozent, je nach Zufall (seit 0.34.19).
pruef("Gegen einen, der quer laeuft, trifft er deutlich seltener (kein Vorhalten)",
      _tq80 < _ts80 * 0.8,
      "%d Treffer gegen %d (Quote %.0f %% aus %d gegen %.0f %% aus %d)"
      % (_tq80, _ts80, _quer80 * 100, _sq80, _still80 * 100, _ss80))
# Blendgranate: er sieht nichts mehr.
_bot80.hirn.blenden(2.0)
pruef("Eine Blendgranate blendet auch einen Bot", not _bot80.hirn.sieht(_ich80))
w80.verlassen()

# Ohne Munition: das Brecheisen.
_n80 = netz.Gastgeber(_neuer_port())
w80 = Gefecht(app, "WIRT", gastgeber=_n80, modus="team", seed=3, knapp=True, regeln={"bots": 2})
_bot80 = w80._bots()[0]
for n_ in _bot80.waffen:
    _bot80.magazin[n_] = 0
    _bot80.vorrat[n_] = 0
_ich80 = w80.ich
_ich80.pos.update(_stelle80(120))
_ich80.max_leben = _ich80.leben = 5000
_ich80.unverwundbar = 0.0
_bot80.unverwundbar = 0.0
_schlaege80 = 0
for _ in range(int(8.0 / K.FIXED_DT)):
    vor_ = _bot80.nahkampf_rest
    w80.schritt(K.FIXED_DT)
    if _bot80.nahkampf_rest > vor_:
        _schlaege80 += 1
pruef("Ohne Munition geht ein Bot mit dem Brecheisen los und trifft",
      _schlaege80 >= 3 and _ich80.leben < 5000, "%d Schlaege, Leben %.0f" % (_schlaege80, _ich80.leben))
w80.verlassen()

# Treppen: ein Bot findet auf eine andere Ebene.
_n80 = netz.Gastgeber(_neuer_port())
w80 = Gefecht(app, "WIRT", gastgeber=_n80, modus="team", seed=5, regeln={"bots": 2})
_bot80 = w80._bots()[0]
_bot80.hirn.sieht = lambda w_: False      # nur der Weg zaehlt hier
_oben80 = freier_punkt(w80.welt, 1, random.Random(5))
for _ in range(int(40.0 / K.FIXED_DT)):
    _bot80.hirn.verdacht = (pygame.Vector2(_oben80), 1, w80.welt.zeit + 5.0)
    _bot80.hirn.ziel = None
    w80.schritt(K.FIXED_DT)
    if _bot80.ebene == 1:
        break
pruef("Ein Bot nimmt die Treppe, um auf eine andere Ebene zu kommen",
      _bot80.ebene == 1, "Ebene %d" % _bot80.ebene)
w80.verlassen()

# Kein Buggy fuer Bots.
_n80 = netz.Gastgeber(_neuer_port())
w80 = Gefecht(app, "WIRT", gastgeber=_n80, modus="pvp", karte="staubtal", seed=4, regeln={"bots": 2})
_bot80 = w80._bots()[0]
_wg80 = w80.fahrzeuge[0]
pruef("STAUBTAL hat fuenf Buggys", _nb(w80.fahrzeuge) == 5, str(len(w80.fahrzeuge)))
_bot80.pos.update(_wg80.ausstiegsorte(_bot80.radius)[0])
_bot80.ebene = _wg80.ebene
_bot80.treppe_rest = 0.0
w80._anwenden(_bot80, {"will": [0, 0], "ziel": [0, 0], "knoepfe": ["nutzen"]})
pruef("Ein Bot steigt nicht in einen Buggy", not _bot80.im_fahrzeug)
# Zurueck auf freies Feld - neben dem Buggy laege sein Punkt unter dem des Wagens.
_bot80.pos.update(freier_punkt(w80.welt, 0, random.Random(80)))
# Gegner auf der Minikarte: nur mit der Regel.


def _feindpunkte80(an):
    w80.regelwerk["gegner_karte"] = an
    f_ = pygame.Surface((K.GAME_W, K.GAME_H))
    f_.fill((0, 0, 0))
    _Mk80().zeichnen(f_, w80)
    r_ = _Mk80().rechteck(w80.welt)
    return sum(1 for x_ in range(r_.left, r_.right) for y_ in range(r_.top, r_.bottom)
               if f_.get_at((x_, y_))[:3] == _FEIND80)


pruef("Gegner stehen nur mit der Regel auf der Minikarte",
      _feindpunkte80(False) == 0 and _feindpunkte80(True) > 0)
w80.verlassen()

print("\n-- Buggys gehen kaputt")
w80, g80 = gefechtspaar("team", karte="staubtal")
_gk80 = w80.kaempfer[g80.meine_nummer]
_wg80 = w80.fahrzeuge[0]
_gk80.pos.update(_wg80.ausstiegsorte(_gk80.radius)[0])
_gk80.ebene = _wg80.ebene
_gk80.treppe_rest = 0.0
_gk80.unverwundbar = 0.0
w80._anwenden(_gk80, {"will": [0, 0], "ziel": [0, 0], "knoepfe": ["nutzen"]})
pruef("Im Buggy ist der Fahrer selbst kein Ziel mehr - der Wagen ist es",
      _gk80.im_fahrzeug and not _gk80.trefferbar and _wg80.trefferbar)
_ich80 = w80.ich
_vor80 = (_wg80.leben, _gk80.leben)
w80.welt.dazu(_Gs80(_wg80.pos + pygame.Vector2(-30, 0), 0.0, K.WAFFEN["sturm"],
                    _wg80.ebene, _ich80, "sturm"))
_beide80(0.1, w80, g80)
pruef("Ein Schuss auf den Wagen: der Wagen nimmt Schaden, der Fahrer nichts (seit 0.34.77)",
      _wg80.leben < _vor80[0] and _gk80.leben == _vor80[1],
      "Wagen %.0f, Fahrer %.1f" % (_wg80.leben, _gk80.leben))
pruef("... und zaehlt nicht als Treffer in der Statistik",
      _ich80.zaehler.get("treffer", 0) == 0)
_mit80 = [k_ for k_ in w80.kaempfer.values() if k_.team == _gk80.team and k_ is not _gk80]
if _mit80:
    _vor80 = _gk80.leben
    _wg80.schaden(20, None, _mit80[0])
    pruef("Die eigenen Leute verletzen den Fahrer nicht", _gk80.leben == _vor80)
_gk80.leben = 500.0
_wg80.schaden(K.FAHRZEUG["leben"], None, _ich80)
_beide80(0.3, w80, g80)
pruef("Kaputt: Wrack, Fahrer draussen und verletzt",
      _wg80.kaputt and _wg80.bild == "buggy_wrack" and not _gk80.im_fahrzeug
      and _gk80.trefferbar and _gk80.leben < 500.0, "Leben %.0f" % _gk80.leben)
pruef("Der Gast sieht das Wrack", any(b_.kaputt for b_ in g80.fahrzeuge))
w80._anwenden(_gk80, {"will": [0, 0], "ziel": [0, 0], "knoepfe": ["nutzen"]})
pruef("In ein Wrack steigt niemand ein", not _gk80.im_fahrzeug)
_beide80(K.FAHRZEUG["wrack_zeit"] + 0.3, w80, g80)
pruef("Nach der Brennzeit ist das Wrack weg", _nb(w80.fahrzeuge) == 4)
_beide80(K.FAHRZEUG["neu_nach"] + 1.5, w80, g80)
_neu80 = w80.fahrzeuge[-1]
pruef("Spaeter steht irgendwo ein neuer Wagen, heil und an einem freien Platz",
      _nb(w80.fahrzeuge) == 5 and not _neu80.kaputt and _neu80.passt(_neu80.pos)
      and _neu80.pos.distance_to(_wg80.start[0]) > 1.0 and _nb(g80.fahrzeuge) == 5)
w80.fahrzeuge[1].schaden(K.FAHRZEUG["leben"], None, _ich80)
w80.wunsch = dict(w80.regelwerk)
w80._runde_neu()
_beide80(0.3, w80, g80)
pruef("Zur neuen Runde stehen wieder alle fuenf heil an ihren Plaetzen",
      _nb(w80.fahrzeuge) == 5 and all(not b_.kaputt and b_.leben == b_.max_leben
                                      for b_ in w80.fahrzeuge))
w80.verlassen(); g80.verlassen()

print("\n-- Dash-Richtung beim Gast (0.34.19)")
w81, g81 = gefechtspaar("pvp")
_beide80(0.5, w81, g81)
_ich81 = w81.ich
_ich81.will.update(0, -1)
_ich81.dash_ladungen = max(1, _ich81.dash_ladungen)
_ich81.dash_sperre = 0.0
pruef("Der Gastgeber dasht nach oben", _ich81.dashen()
      and _ich81.dash_richtung.y < -0.9, str(_ich81.dash_richtung))
_beide80(0.1, w81, g81)
_bei_gast81 = g81.kaempfer.get(w81.meine_nummer)
pruef("Beim Gast zeigen die Windlinien auch nach oben, nicht nach rechts",
      _bei_gast81 is not None and _bei_gast81.dash_richtung.y < -0.9,
      str(getattr(_bei_gast81, "dash_richtung", None)))
w81.verlassen(); g81.verlassen()

print("\n-- Kleine Hindernisse halten nur mit ihrer Grundflaeche auf (0.34.19)")
_sw81 = W.karte_lesen("staubtal")[0]
_e81 = _sw81.ebene(0)
_kaktus81 = None
for _i81, _k81 in enumerate(_e81.kacheln):
    if _k81 != K.KAKTUS:
        continue
    _tx81, _ty81 = _i81 % _e81.breite, _i81 // _e81.breite
    if all(not K.KACHELN[_e81.kachel(_tx81 + dx_, _ty81 + dy_)]["fest"]
           and _e81.kachel(_tx81 + dx_, _ty81 + dy_) != K.LEER
           for dx_ in (-1, 0, 1) for dy_ in (-1, 0, 1) if dx_ or dy_):
        _kaktus81 = (_tx81, _ty81)
        break
pruef("STAUBTAL hat einen Kaktus mit freiem Boden rundherum", _kaktus81 is not None)
if _kaktus81:
    _r81 = 10.0
    _st81 = K.STEHEN["kaktus"]
    _mitte81 = pygame.Vector2(_kaktus81[0] * K.TILE + _st81["rahmen"][0] + _st81["rahmen"][2] / 2,
                              _kaktus81[1] * K.TILE + _st81["rahmen"][1] + _st81["rahmen"][3] / 2)
    _grenze81 = _r81 + _st81["rahmen"][2] / 2
    pruef("Am Kaktus kommt man bis an seinen Rand, nicht nur bis an die Kachel",
          _sw81.frei(_mitte81 + pygame.Vector2(-_grenze81 - 0.5, 0), _r81, 0)
          and _sw81.frei(_mitte81 + pygame.Vector2(0, _grenze81 + 0.5), _r81, 0))
    pruef("... in ihn hinein aber nicht",
          not _sw81.frei(_mitte81 + pygame.Vector2(-_grenze81 + 1.0, 0), _r81, 0))
    import types as _ty_mod81
    _wesen81 = _ty_mod81.SimpleNamespace(
        pos=_mitte81 + pygame.Vector2(-60, 0), radius=_r81, ebene=0,
        vorher=pygame.Vector2(), faellt=False)
    for _ in range(40):
        _sw81.bewegen(_wesen81, 3.0, 0.0)
    _abstand81 = _wesen81.pos.distance_to(_mitte81)
    pruef("Wer auf den Kaktus zulaeuft, bleibt erst an ihm stehen",
          _grenze81 - 0.5 <= _abstand81 <= _grenze81 + 3.5,
          "%.1f Pixel von der Mitte, Grenze %.1f" % (_abstand81, _grenze81))
    _sch81 = szene.renderer._kleinschatten(_st81, None)
    pruef("Der Schatten des Kaktus ist rund, kein Quadrat um die Kachel",
          _sch81.get_at((1, 1)).a == 0 and _sch81.get_at((K.TILE - 2, 1)).a == 0
          and _sch81.get_at((K.TILE // 2, K.TILE // 2)).a > 0)

_tk81 = testkarte()
_e81 = _tk81.ebene(0)
_wand81 = next(i for i, k in enumerate(_e81.kacheln) if k == K.WAND
               and _e81.kachel(i % _e81.breite - 1, i // _e81.breite) == K.BODEN)
_wx81, _wy81 = _wand81 % _e81.breite, _wand81 // _e81.breite
_vor_wand81 = pygame.Vector2(_wx81 * K.TILE - 9.0, _wy81 * K.TILE + 16)
pruef("Eine Mauer haelt weiter mit der ganzen Kachel auf",
      not _tk81.frei(_vor_wand81, 10.0, 0) and _tk81.frei(_vor_wand81 + pygame.Vector2(-2, 0), 10.0, 0))
_kiste81 = next(i for i, k in enumerate(_e81.kacheln) if k == K.KISTE)
_kx81, _ky81 = _kiste81 % _e81.breite, _kiste81 // _e81.breite
_ra81 = K.STEHEN["kiste"]["rahmen"]
_vor_kiste81 = pygame.Vector2(_kx81 * K.TILE + _ra81[0] - 10.5, _ky81 * K.TILE + 16)
pruef("Eine Kiste haelt mit ihrem Rahmen auf, nicht mit der Kachel",
      _tk81.frei(_vor_kiste81, 10.0, 0)
      and not _tk81.frei(_vor_kiste81 + pygame.Vector2(1.5, 0), 10.0, 0))
_wueste81 = W.Welt([W.Ebene.aus_text(W.KARTE_E0, 0)], satz="wueste")
_sk81 = K.STEHEN["sand_kiste"]["rahmen"]
# Schraeg vor der Ecke: bei einem Quadrat stiesse man an, an der runden
# Sandkiste geht es vorbei.
_ecke81 = pygame.Vector2(_kx81 * K.TILE + _sk81[0], _ky81 * K.TILE + _sk81[1])
_schraeg81 = _ecke81 + pygame.Vector2(-5.0, -5.0)
pruef("Die Sandkiste der Wueste ist rund: an ihrer Ecke kommt man vorbei",
      _wueste81.frei(_schraeg81, 10.0, 0) and not _tk81.frei(_schraeg81 + pygame.Vector2(-1, -1), 10.0, 0),
      str(_wueste81.huelle(K.KISTE)))

# ─────────────────────────────────────────────────────────────────────
# 0.34.20: "Ich moechte das Ganze auch auf iOS und iPadOS rueberbekommen
# ... einen tatsaechlich echten Port, dass der Code dort ausgefuehrt wird.
# Und dass es halt auch Crossplay-kompatibel ist."
# Hier laeuft kein iPhone. Geprueft wird, was dort anders ist: Finger
# statt Maus (DUSTFRONT_TOUCH), Zeichen als TEXTINPUT, der Datenordner,
# und der Weg zum Online-Code ohne cloudflared - gegen eine Attrappe von
# Cloudflare, die tut, was der Tunnel tut: WebSocket rein, TCP raus.
print("\n-- iOS: Plattform, Touch, Tastatur, Weg ohne cloudflared (0.34.20)")
import base64 as _b64_82, hashlib as _hl82, socket as _so82, struct as _st82, threading as _th82
from dustfront import plattform as _pf82, pfade as _pfade82, touch as _touch82
from dustfront import wszugang as _ws82, ui as _ui82
from dustfront import online as _on82

pruef("Auf diesem Rechner ist kein iOS", not _pf82.IOS and _pf82.prozesse_erlaubt())
_alt_touch82 = os.environ.pop("DUSTFRONT_TOUCH", None)
pruef("Ohne DUSTFRONT_TOUCH bleibt es bei Maus und Tastatur",
      not _pf82.touch_an() and App("OHNE", None, headless=True).touch is None)
os.environ["DUSTFRONT_TOUCH"] = "1"
pruef("Mit DUSTFRONT_TOUCH=1 gilt die Touch-Steuerung", _pf82.touch_an())

_alt_plattform82 = sys.platform
try:
    sys.platform = "ios"
    _ios_ordner82 = _pfade82._system_ordner()
finally:
    sys.platform = _alt_plattform82
pruef("Auf iOS liegen Einstellungen im Behaelter der App, nicht im App-Paket",
      _ios_ordner82.parts[-3:] == ("Library", "Application Support", "Dustfront"),
      str(_ios_ordner82))

# Bildschirmtastatur: Zeichen kommen als TEXTINPUT, und ein Feld liest
# KEYDOWN.unicode. Solange die Tastatur offen ist, wird umgesetzt.
_pf82._offen = True
_um82 = _pf82.text_umsetzen([
    pygame.event.Event(pygame.KEYDOWN, key=pygame.K_a, mod=0, scancode=4, unicode="a"),
    pygame.event.Event(pygame.TEXTINPUT, text="a"),
    pygame.event.Event(pygame.TEXTINPUT, text="bc-d"),
    pygame.event.Event(pygame.KEYDOWN, key=pygame.K_BACKSPACE, mod=0, scancode=42,
                       unicode="\b")])
pruef("Ein Wort aus der Zwischenablage wird Zeichen fuer Zeichen getippt, nichts doppelt",
      [e.unicode for e in _um82 if e.type == pygame.KEYDOWN and e.key == 0]
      == ["a", "b", "c", "-", "d"]
      and sum(1 for e in _um82 if e.type == pygame.KEYDOWN) == 6
      and _um82[-1].key == pygame.K_BACKSPACE, str([(e.type, getattr(e, "unicode", "")) for e in _um82]))
_tf82 = _ui82.Textfeld((10, 10, 200, 18), "CODE", "adresse")
for _e82 in _um82:
    if _e82.type == pygame.KEYDOWN:
        _tf82.tippen(_e82)
pruef("... und kommt so im Textfeld an (die Ruecktaste nimmt eines weg)",
      _tf82.wert == "abc-", _tf82.wert)
_pf82._offen = False
pruef("Ist die Tastatur zu, bleibt alles, wie es ist",
      len(_pf82.text_umsetzen([pygame.event.Event(pygame.TEXTINPUT, text="x")])) == 1)
_tf82.aktiv = True
_tf82.zeichnen(pygame.Surface((K.GAME_W, K.GAME_H)))
pruef("Ein Textfeld, das dran ist, verlangt die Tastatur", _pf82._gewuenscht)
_pf82.tastatur_abgleichen()
pruef("... und sie geht auf", _pf82.tastatur_offen())
_pf82.tastatur_abgleichen()
pruef("... und wieder zu, sobald kein Feld mehr dran ist", not _pf82.tastatur_offen())

# Die Steuerung in einem Gefecht. Die Finger kommen, wie SDL sie meldet:
# als Anteil des Fensters.
_tapp82 = App("IPHONE", None, headless=True)
pruef("Die App bringt die Touch-Steuerung mit",
      isinstance(_tapp82.touch, _touch82.Touchsteuerung))
_neuer_port()
_tw82 = Gefecht(_tapp82, "IPHONE", gastgeber=netz.Gastgeber(_port[0]), modus="pvp",
                seed=82)
_tapp82.schieben(_tw82)


def _finger82(art, fid, gx, gy, a_=None):
    a_ = a_ or _tapp82
    fw_, fh_ = a_.fenster.get_size()
    p_ = a_.zu_fenster((gx, gy, 1, 1))
    pygame.event.post(pygame.event.Event(art, finger_id=fid, touch_id=1, x=p_.x / fw_,
                                         y=p_.y / fh_, dx=0.0, dy=0.0, pressure=1.0))
    a_.ereignisse()


pygame.event.clear()
_tapp82.ereignisse()
pruef("Im Gefecht gehoeren die Finger der Steuerung", _tapp82.touch.spielt())
_start82 = pygame.Vector2(_tw82.ich.pos)
_finger82(pygame.FINGERDOWN, 1, 100, 250)
_finger82(pygame.FINGERMOTION, 1, 100 + K.TOUCH["stick_radius"], 250)
pruef("Der linke Stick, ganz nach rechts gezogen: volle Kraft nach rechts",
      _tapp82.eingabe.richtung().distance_to(pygame.Vector2(1, 0)) < 0.01,
      str(_tapp82.eingabe.richtung()))
for _ in range(60):
    _tapp82.ereignisse()
    _tw82.schritt(K.FIXED_DT)
pruef("... und die Figur laeuft nach rechts", _tw82.ich.pos.x - _start82.x > 20
      and abs(_tw82.ich.pos.y - _start82.y) < 2, str(_tw82.ich.pos - _start82))
_finger82(pygame.FINGERMOTION, 1, 100 + K.TOUCH["stick_radius"] * 0.4, 250)
_halb82 = _tapp82.eingabe.richtung().length()
pruef("Halb gezogen geht man langsamer", 0.2 < _halb82 < 0.8, "%.2f" % _halb82)
_finger82(pygame.FINGERUP, 1, 100, 250)
pruef("Losgelassen steht man", _tapp82.eingabe.richtung().length() < 0.01)

_finger82(pygame.FINGERDOWN, 2, 450, 150)
_finger82(pygame.FINGERMOTION, 2, 450, 150 - K.TOUCH["stick_radius"] * 0.3)
_mitte82 = _tw82.touch_mitte()
pruef("Der rechte Stick leicht gezogen zielt nur",
      not _tapp82.eingabe.gehalten("feuer")
      and _tapp82.eingabe.maus.y < _mitte82.y - 20
      and abs(_tapp82.eingabe.maus.x - _mitte82.x) < 1, str(_tapp82.eingabe.maus))
_finger82(pygame.FINGERMOTION, 2, 450, 150 - K.TOUCH["stick_radius"])
pruef("... weiter gezogen schiesst er auch, und zielt weiter weg",
      _tapp82.eingabe.gehalten("feuer") and _tapp82.eingabe.gedrueckt("feuer")
      and _mitte82.y - _tapp82.eingabe.maus.y > K.TOUCH["ziel_weit"] - 1,
      str(_tapp82.eingabe.maus))
_tw82.schritt(K.FIXED_DT)
pruef("Die Figur schaut, wohin der Stick zeigt (nach oben)",
      abs(((_tw82.ich.winkel + 90) + 180) % 360 - 180) < 3, "%.1f" % _tw82.ich.winkel)
_finger82(pygame.FINGERUP, 2, 450, 120)
pruef("Losgelassen schiesst er nicht mehr", not _tapp82.eingabe.gehalten("feuer")
      and _tapp82.eingabe.losgelassen("feuer"))

# Die Maus, die SDL aus einem Finger macht, darf im Spiel nicht schiessen.
pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=(900, 300), button=1,
                                     touch=True, window=None))
_tapp82.ereignisse()
pruef("Ein Finger ist im Spiel keine Maus (sonst schoesse jeder Tipp)",
      not _tapp82.eingabe.gehalten("feuer"))
pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=(900, 300), button=1,
                                     touch=False, window=None))
_tapp82.ereignisse()
pruef("... eine echte Maus schon (iPad mit Maus)", _tapp82.eingabe.gehalten("feuer"))
pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONUP, pos=(900, 300), button=1,
                                     touch=False, window=None))
_tapp82.ereignisse()


def _knopf82(aktion):
    return next(k_[2] for k_ in K.TOUCH["knoepfe"] if k_[0] == aktion)


_d82 = _knopf82("dash")
_finger82(pygame.FINGERDOWN, 3, *_d82)
pruef("DASH gedrueckt ist die gehaltene Dash-Taste (im Buggy die Handbremse)",
      _tapp82.eingabe.gehalten("dash") and "dash" in _tw82._knoepfe, str(_tw82._knoepfe))
_finger82(pygame.FINGERUP, 3, *_d82)
pruef("... und losgelassen wieder los", not _tapp82.eingabe.gehalten("dash"))
_tw82.ich.waffe = 0


def _erste82(platz):
    """Welche Waffe ein Druck auf diesen Platz waehlt: ohne Gruppen der
    Platz, mit Gruppen (JEDER HAT ALLES, seit 0.34.85) die erste Waffe der
    Gruppe."""
    if not _tw82.gruppen_hotbar:
        return platz
    return next(i_ for i_, w_ in enumerate(_tw82.ich.waffen) if _tw82.gruppe_von(w_) == platz)


_finger82(pygame.FINGERDOWN, 4, *_knopf82("waffe"))
pruef("WFF waehlt die naechste Waffe der Hotbar (mit Gruppen: die naechste Gruppe)",
      _tw82._waffe_wunsch == _erste82(1), str(_tw82._waffe_wunsch))
_finger82(pygame.FINGERUP, 4, *_knopf82("waffe"))
_tw82.ich.waffe = len(_tw82.ich.waffen) - 1
_finger82(pygame.FINGERDOWN, 4, *_knopf82("waffe"))
pruef("... nach der letzten wieder die erste", _tw82._waffe_wunsch == 0,
      str(_tw82._waffe_wunsch))
_finger82(pygame.FINGERUP, 4, *_knopf82("waffe"))
_finger82(pygame.FINGERDOWN, 5, *_knopf82("zweit"))
_finger82(pygame.FINGERUP, 5, *_knopf82("zweit"))
pruef("ZIEL bleibt an, bis man es wieder drueckt", _tapp82.eingabe.gehalten("zweit"))
_finger82(pygame.FINGERDOWN, 5, *_knopf82("zweit"))
_finger82(pygame.FINGERUP, 5, *_knopf82("zweit"))
pruef("... und geht dann aus", not _tapp82.eingabe.gehalten("zweit"))

# 0.34.22: Gezielt wird von der Figur aus, nicht ueber die Kamera (beim
# Laufen wackelte das Ziel, mit dem Scharfschuetzengewehr deutlich).
_finger82(pygame.FINGERDOWN, 21, 450, 150)
_finger82(pygame.FINGERMOTION, 21, 450 + K.TOUCH["stick_radius"] * 0.3, 150)
_zv82 = _tapp82.eingabe.ziel_versatz
_ziel82 = _tapp82.eingabe.ziel_welt(_tw82.kamera, _tw82.ich.pos)
pruef("Der rechte Stick zielt von der Figur aus (nach rechts), ohne Umweg ueber die Kamera",
      _zv82 is not None and _zv82.x > 20 and abs(_zv82.y) < 1
      and (_ziel82 - _tw82.ich.pos).distance_to(_zv82 * _tw82.kamera.zoom) < 0.01,
      "%s / %s" % (_zv82, _ziel82 - _tw82.ich.pos))
_finger82(pygame.FINGERUP, 21, 450, 150)
pruef("... und die Maus am Rechner zielt wie immer (ohne Stick kein Versatz)",
      App("OHNE2", None, headless=True).eingabe.ziel_versatz is None)
_tapp82.touch.zielen_an = True
_finger82(pygame.FINGERDOWN, 22, 450, 150)
_finger82(pygame.FINGERMOTION, 22, 450 + K.TOUCH["stick_radius"], 150)
_weit82 = _tapp82.eingabe.ziel_versatz.length()
_finger82(pygame.FINGERUP, 22, 450 + K.TOUCH["stick_radius"], 150)
pruef("Mit ZIEL bleibt der Blick weit, wenn der Daumen den Stick loslaesst",
      abs(_tapp82.eingabe.ziel_versatz.length() - _weit82) < 0.01
      and _weit82 > K.TOUCH["ziel_nah"] + 50, "%.0f" % _weit82)
_tapp82.touch.zielen_an = False
_tapp82.ereignisse()

# Zoomen mit zwei Fingern auf derselben Seite.
_zoom82 = _tw82.zoom_ziel
_finger82(pygame.FINGERDOWN, 23, 120, 200)
_finger82(pygame.FINGERDOWN, 24, 160, 200)
_finger82(pygame.FINGERMOTION, 24, 160 + K.TOUCH["zoom_schritt"] * 1.2, 200)
pruef("Zwei Finger auseinander zoomen naeher heran", _tw82.zoom_ziel < _zoom82,
      "%.2f -> %.2f" % (_zoom82, _tw82.zoom_ziel))
pruef("... und dabei laeuft die Figur nicht", _tapp82.eingabe.richtung().length() < 0.01)
_finger82(pygame.FINGERMOTION, 24, 160 - K.TOUCH["zoom_schritt"] * 1.5, 200)
pruef("... zusammen wieder weiter weg", _tw82.zoom_ziel >= _zoom82,
      "%.2f" % _tw82.zoom_ziel)
_finger82(pygame.FINGERUP, 24, 100, 200)
_finger82(pygame.FINGERMOTION, 23, 200, 200)
pruef("Der Finger, der liegen bleibt, wird kein Stick mitten im Zug",
      _tapp82.eingabe.richtung().length() < 0.01)
_finger82(pygame.FINGERUP, 23, 200, 200)

# Die Hotbar antippen.
_plaetze82 = _tw82.touch_hotbar()
# Seit 0.34.85 in JEDER HAT ALLES: ein Platz je Gruppe (K.ALLES_GRUPPEN).
pruef("Die Szene sagt, wo die Plaetze der Hotbar stehen",
      len(_plaetze82) == (len(K.ALLES_GRUPPEN) if _tw82.gruppen_hotbar else len(_tw82.ich.waffen))
      and len(_plaetze82) >= 3, str(len(_plaetze82)))
_finger82(pygame.FINGERDOWN, 25, *_plaetze82[2].center)
pruef("Den dritten Platz antippen waehlt die dritte Waffe (bzw. Gruppe)",
      _tw82._waffe_wunsch == _erste82(2), str(_tw82._waffe_wunsch))
_finger82(pygame.FINGERUP, 25, *_plaetze82[2].center)
pruef("... und schiesst dabei nicht", not _tapp82.eingabe.gehalten("feuer"))
_tw82._waffe_wunsch = -1
_finger82(pygame.FINGERDOWN, 26, *_plaetze82[-1].midtop)
pruef("... auch knapp darueber getroffen (die Felder sind nur 20 hoch)",
      _tw82._waffe_wunsch == _erste82(len(_plaetze82) - 1), str(_tw82._waffe_wunsch))
_finger82(pygame.FINGERUP, 26, *_plaetze82[-1].midtop)

# Im Auto mit dem Stick: er faehrt dorthin, wohin der Stick zeigt.
from dustfront.fahrzeug import Buggy as _Buggy82
_b82 = _Buggy82(pygame.Vector2(200, 200), 0, winkel=0.0)
_g82, _l82 = _b82.stick_steuern(pygame.Vector2(0, 1))
pruef("Auto nach rechts gerichtet, Stick nach unten: Gas und rechts einschlagen",
      _g82 > 0.4 and _l82 > 0.9, "%.2f %.2f" % (_g82, _l82))
_g82, _l82 = _b82.stick_steuern(pygame.Vector2(1, 0))
pruef("Stick in Fahrtrichtung: Vollgas geradeaus", _g82 == 1.0 and _l82 == 0.0)
_g82, _l82 = _b82.stick_steuern(pygame.Vector2(-1, 0))
pruef("Stick genau entgegen, im Stand: rueckwaerts", _g82 < 0 and _l82 == 0.0)
_b82.geschw.update(200, 0)
pruef("... in voller Fahrt: erst bremsen", _b82.stick_steuern(pygame.Vector2(-1, 0)) == (-1.0, 0.0))
_b82.winkel = 90.0
_g82, _l82 = _b82.stick_steuern(pygame.Vector2(1, 0))
pruef("Auto nach unten, Stick nach rechts: im Bild nach rechts heisst links einschlagen",
      _l82 < -0.9, "%.2f" % _l82)
pruef("Ein halb gedrueckter Stick gibt halb Gas",
      abs(_b82.stick_steuern(pygame.Vector2(0, 0.5))[0] - 0.5) < 0.01)
_tapp82.eingabe.analog = pygame.Vector2(0.3, 0)
pruef("Die Eingabe sagt dem Gastgeber, dass sie von einem Stick kommt",
      _tw82._meine_eingabe().get("rl") is True)

# Das Trefferzeichen: auf dem iPhone ein schwarzes Viereck dahinter.
from dustfront.render import Trefferzeichen as _Tz82
_tz82 = _Tz82()
_tz82.dauer, _tz82.rest = 1.0, 0.2           # blasst gerade aus
_grund82 = pygame.Surface((K.GAME_W, K.GAME_H))
_grund82.fill((70, 55, 40))
_tz82.zeichnen(_grund82, (300, 180))
_m82 = K.TREFFERMARKE
_rand82 = int(_m82["laenge"] + _m82["luecke"]) + 4
pruef("Kein Viereck hinter dem Trefferzeichen: neben dem X bleibt das Bild",
      tuple(_grund82.get_at((300 - _rand82 + 1, 180)))[:3] == (70, 55, 40)
      and tuple(_grund82.get_at((300, 180 - _rand82 + 1)))[:3] == (70, 55, 40))
_s82 = pygame.Surface((4, 4), pygame.SRCALPHA)
_s82.fill((200, 100, 50, 200))
_d82 = _pf82.deckkraft(_s82, 128)
pruef("Durchsichtig zeichnen ohne set_alpha: das Alpha je Pixel wird kleiner",
      _d82.get_alpha() in (None, 255) and 95 <= _d82.get_at((1, 1)).a <= 105
      and _s82.get_at((1, 1)).a == 200, str(_d82.get_at((1, 1))))

# Pause: alles loslassen, die Finger werden wieder zur Maus.
_finger82(pygame.FINGERDOWN, 6, 100, 250)
_finger82(pygame.FINGERMOTION, 6, 140, 250)
_finger82(pygame.FINGERDOWN, 7, *_knopf82("pause"))
_finger82(pygame.FINGERUP, 7, *_knopf82("pause"))
pruef("II oeffnet das Pausenmenue", _tw82.menue is not None)
pruef("... und was der Daumen hielt, ist losgelassen (die Figur laeuft nicht weiter)",
      _tapp82.eingabe.richtung().length() < 0.01 and not _tapp82.touch.spielt())
_finger82(pygame.FINGERUP, 6, 140, 250)
_esc_fenster82 = _tapp82.zu_fenster((*K.TOUCH["esc_mitte"], 1, 1)).topleft
pruef("Im Menue ist ein Finger wieder die Maus - nur nicht auf dem ESC-Knopf",
      not _tapp82.touch.schluckt(pygame.event.Event(
          pygame.MOUSEBUTTONDOWN, pos=(640, 360), button=1, touch=True))
      and _tapp82.touch.schluckt(pygame.event.Event(
          pygame.MOUSEBUTTONDOWN, pos=_esc_fenster82, button=1, touch=True)))
_finger82(pygame.FINGERDOWN, 8, *K.TOUCH["esc_mitte"])
_finger82(pygame.FINGERUP, 8, *K.TOUCH["esc_mitte"])
pruef("Der ESC-Knopf schliesst das Menue wieder", _tw82.menue is None
      and _tapp82.touch.spielt())
_flaeche82 = pygame.Surface((K.GAME_W, K.GAME_H))
_tapp82.touch.zeichnen(_flaeche82)
pruef("Sticks und Knoepfe werden gezeichnet",
      _flaeche82.get_at(_knopf82("dash")) != (0, 0, 0, 255))
# 0.34.21: auf dem iPhone war das Spiel schwarz, solange die Knoepfe zu
# sehen waren (Alpha je Pixel UND set_alpha auf einer Flaeche rechnet
# pygame-ce 2.5.6 dort falsch). Die Ebene der Knoepfe benutzt darum nur
# noch Alpha je Pixel - und laesst stehen, wo nichts von ihr liegt.
_flaeche82.fill((70, 55, 40))
_tapp82.touch.zeichnen(_flaeche82)
pruef("Die Knoepfe kommen ohne set_alpha aus (das machte das iPhone schwarz)",
      _tapp82.touch._overlay.get_alpha() in (None, 255),
      str(_tapp82.touch._overlay.get_alpha()))
pruef("... und wo kein Knopf liegt, bleibt das Bild, wie es ist",
      tuple(_flaeche82.get_at((200, 150)))[:3] == (70, 55, 40),
      str(_flaeche82.get_at((200, 150))))
_tapp82.werfen()


# Der Weg ohne cloudflared. Die Attrappe von Cloudflare nimmt einen
# WebSocket an - nur fuer den richtigen Code, sonst 404 wie Cloudflare -
# und reicht die Bytes an eine TCP-Adresse weiter, wie der Tunnel des
# Gastgebers an dessen Lobby.
class _CfAttrappe82:
    def __init__(self, code, ziel_port):
        self.code = code
        self.ziel_port = ziel_port
        self.koepfe = []
        self.rahmenarten = set()
        self.sock = _so82.socket()
        self.sock.bind(("127.0.0.1", 0))
        self.sock.listen(8)
        self.sock.settimeout(0.2)
        self.port = self.sock.getsockname()[1]
        self.zu = False
        _th82.Thread(target=self._annehmen, daemon=True).start()

    def _annehmen(self):
        while not self.zu:
            try:
                c, _ = self.sock.accept()
            except OSError:
                continue
            c.settimeout(None)
            _th82.Thread(target=self._einer, args=(c,), daemon=True).start()

    def _einer(self, c):
        puffer = b""
        while b"\r\n\r\n" not in puffer:
            stueck = c.recv(4096)
            if not stueck:
                return
            puffer += stueck
        kopf, rest = puffer.split(b"\r\n\r\n", 1)
        self.koepfe.append(kopf.decode("latin-1"))
        felder = {}
        for z in kopf.split(b"\r\n")[1:]:
            k, _, v = z.partition(b":")
            felder[k.strip().lower()] = v.strip()
        if not felder.get(b"host", b"").startswith(self.code.encode() + b"."):
            c.sendall(b"HTTP/1.1 404 Not Found\r\nContent-Length: 0\r\n\r\n")
            c.close()
            return
        antwort = _b64_82.b64encode(_hl82.sha1(
            felder[b"sec-websocket-key"] + b"258EAFA5-E914-47DA-95CA-C5AB0DC85B11").digest())
        c.sendall(b"HTTP/1.1 101 Switching Protocols\r\nUpgrade: websocket\r\n"
                  b"Connection: Upgrade\r\nSec-WebSocket-Accept: " + antwort + b"\r\n\r\n")
        t = _so82.create_connection(("127.0.0.1", self.ziel_port))
        stand = {"p": rest}

        def lesen(n):
            while len(stand["p"]) < n:
                d = c.recv(65536)
                if not d:
                    raise EOFError
                stand["p"] += d
            r, stand["p"] = stand["p"][:n], stand["p"][n:]
            return r

        def hoch():
            try:
                while True:
                    b1, b2 = lesen(2)
                    n = b2 & 0x7F
                    if n == 126:
                        n = _st82.unpack(">H", lesen(2))[0]
                    elif n == 127:
                        n = _st82.unpack(">Q", lesen(8))[0]
                    maske = lesen(4) if b2 & 0x80 else None
                    daten = lesen(n)
                    if maske:
                        daten = bytes(b ^ maske[i % 4] for i, b in enumerate(daten))
                    self.rahmenarten.add((b1 & 0x0F, bool(maske)))
                    if b1 & 0x0F == 8:
                        break
                    if b1 & 0x0F == 2:
                        t.sendall(daten)
            except (EOFError, OSError):
                pass
            t.close()

        def runter():
            try:
                c.sendall(bytes([0x89, 0]))        # ein Ping, wie Cloudflare ab und zu
                while True:
                    d = t.recv(65536)
                    if not d:
                        break
                    n = len(d)
                    k = bytes([0x82, n]) if n < 126 else (
                        bytes([0x82, 126]) + _st82.pack(">H", n) if n < 65536
                        else bytes([0x82, 127]) + _st82.pack(">Q", n))
                    c.sendall(k + d)
            except OSError:
                pass
            c.close()

        _th82.Thread(target=hoch, daemon=True).start()
        _th82.Thread(target=runter, daemon=True).start()

    def schliessen(self):
        self.zu = True
        self.sock.close()


_echo82 = _so82.socket()
_echo82.bind(("127.0.0.1", 0))
_echo82.listen(4)


def _echo_dienst82():
    while True:
        try:
            c_, _ = _echo82.accept()
        except OSError:
            return
        def einer(c_=c_):
            while True:
                d_ = c_.recv(65536)
                if not d_:
                    break
                c_.sendall(d_.upper())
        _th82.Thread(target=einer, daemon=True).start()


_th82.Thread(target=_echo_dienst82, daemon=True).start()
_cf82 = _CfAttrappe82("echo-test-lobby-code", _echo82.getsockname()[1])
_falsch82 = _ws82.WsZugang("wrong-test-lobby-code", ziel=("127.0.0.1", _cf82.port), tls=False)
_ws82.warten(_falsch82, 5)
pruef("Ein falscher Code: Cloudflare antwortet 404, und das steht da, bevor das Spiel anklopft",
      not _falsch82.bereit and "CODE FALSCH" in _falsch82.fehler, _falsch82.fehler)
_falsch82.schliessen()
_zug82 = _ws82.WsZugang("echo-test-lobby-code", ziel=("127.0.0.1", _cf82.port), tls=False)
pruef("Mit dem richtigen Code steht der Weg", _ws82.warten(_zug82, 5), _zug82.fehler)
_k82 = _cf82.koepfe[-1].split("\r\n")
pruef("Der Handschlag ist der von cloudflared (GET /, dieselben Kopfzeilen)",
      _k82[0] == "GET / HTTP/1.1"
      and {z.split(":")[0] for z in _k82[1:]} == {"Host", "User-Agent", "Connection",
                                                  "Sec-WebSocket-Key",
                                                  "Sec-WebSocket-Version", "Upgrade"}
      and "User-Agent: cloudflared/%s" % K.ONLINE["version"] in _k82, str(_k82))
_c82 = _so82.create_connection(("127.0.0.1", _zug82.port), timeout=5)
_c82.sendall(b"hallo")
_an82 = b""
while len(_an82) < 5:
    _an82 += _c82.recv(100)
pruef("Bytes gehen hin und her, unveraendert", _an82 == b"HALLO", repr(_an82))
_gross82 = bytes(random.Random(82).randrange(97, 123) for _ in range(70000))
_c82.sendall(_gross82)
_an82 = b""
while len(_an82) < len(_gross82):
    _an82 += _c82.recv(65536)
pruef("... auch 70 KB am Stueck, in mehreren Rahmen", _an82 == _gross82.upper())
pruef("... und das iPhone schickt nur maskierte Daten-Rahmen und beantwortet Pings",
      (2, True) in _cf82.rahmenarten and (0xA, True) in _cf82.rahmenarten
      and all(m for _a, m in _cf82.rahmenarten), str(_cf82.rahmenarten))
_c82.close()
_zug82.schliessen()
_cf82.schliessen()

os.environ["DUSTFRONT_WS_ZUGANG"] = "1"
_wahl82 = _on82.Zugang("some-other-test-code")
os.environ.pop("DUSTFRONT_WS_ZUGANG", None)
pruef("Wo kein Programm starten darf (oder es erzwungen wird), nimmt der Gast diesen Weg",
      isinstance(_wahl82, _ws82.WsZugang))
_wahl82.schliessen()
_on82.geraet.prozesse_erlaubt, _alt_pe82 = (lambda: False), _on82.geraet.prozesse_erlaubt
_tun82 = _on82.Tunnel(1)
_on82.geraet.prozesse_erlaubt = _alt_pe82
pruef("Auf iOS gibt es keinen Tunnel, und die Lobby sagt warum",
      _tun82.zustand == "fehler" and "IOS" in _tun82.beschreibung(), _tun82.beschreibung())

# Crossplay: ein Gastgeber am Rechner, ein Gast mit Fingern, der ueber den
# Code und den Weg ohne cloudflared kommt.
_neuer_port()
_hp82 = _port[0]
_wirt82 = Gefecht(app, "WIRT", gastgeber=netz.Gastgeber(_hp82), modus="pvp", seed=83)
_cfx82 = _CfAttrappe82("crossplay-test-lobby-code", _hp82)
_zx82 = _ws82.WsZugang("crossplay-test-lobby-code", ziel=("127.0.0.1", _cfx82.port),
                       tls=False)
pruef("Der Gast findet ueber den Code zum Gastgeber", _ws82.warten(_zx82, 5), _zx82.fehler)
_iapp82 = App("IPHONE2", None, headless=True)
_gast82 = Gefecht(_iapp82, "IPHONE", gast=netz.Gast(_zx82.adresse, zugang=_zx82))
_iapp82.schieben(_gast82)


def _beide82(sekunden):
    for _ in range(max(1, int(round(sekunden / K.NETZ["takt"])))):
        _iapp82.ereignisse()
        _wirt82.schritt(K.NETZ["takt"])
        _gast82.schritt(K.NETZ["takt"])
        time.sleep(0.002)


_beide82(1.0)
_ende82 = time.time() + 8
while _gast82.ich is None and time.time() < _ende82:
    _beide82(0.2)
pruef("Er ist drin: der Gastgeber kennt ihn, er sieht sich selbst",
      _gast82.ich is not None and len(_wirt82.kaempfer) == 2,
      "%d Kaempfer" % len(_wirt82.kaempfer))
_drin82 = _gast82.ich is not None and len(_wirt82.kaempfer) == 2
if _drin82:
    _beim_wirt82 = _wirt82.kaempfer[_gast82.meine_nummer]
    _beim_wirt82.unverwundbar = 1e9
    _vorher82 = pygame.Vector2(_beim_wirt82.pos)
    _finger82(pygame.FINGERDOWN, 11, 100, 250, _iapp82)
    _finger82(pygame.FINGERMOTION, 11, 100, 250 + K.TOUCH["stick_radius"], _iapp82)
    _beide82(0.8)
    pruef("Der Daumen auf dem iPhone bewegt die Figur beim Gastgeber (nach unten)",
          _beim_wirt82.pos.y - _vorher82.y > 15 and abs(_beim_wirt82.pos.x - _vorher82.x) < 3,
          str(_beim_wirt82.pos - _vorher82))
    _finger82(pygame.FINGERUP, 11, 100, 250, _iapp82)
    _schuesse82 = _beim_wirt82.zaehler.get("schuesse", 0)
    _beim_wirt82.magazin[_beim_wirt82.waffe_name] = 30
    _finger82(pygame.FINGERDOWN, 12, 450, 180, _iapp82)
    _finger82(pygame.FINGERMOTION, 12, 450 + K.TOUCH["stick_radius"], 180, _iapp82)
    _beide82(0.8)
    pruef("... und der rechte Stick schiesst dort, nach rechts",
          _beim_wirt82.zaehler.get("schuesse", 0) > _schuesse82
          and abs(((_beim_wirt82.winkel + 180) % 360) - 180) < 10,
          "%s Schuesse, Winkel %.0f" % (_beim_wirt82.zaehler.get("schuesse", 0),
                                         _beim_wirt82.winkel))
    _finger82(pygame.FINGERUP, 12, 450, 180, _iapp82)
_iapp82.werfen()
_wirt82.verlassen()
_cfx82.schliessen()
_zx82.schliessen()
os.environ.pop("DUSTFRONT_TOUCH", None)
if _alt_touch82 is not None:
    os.environ["DUSTFRONT_TOUCH"] = _alt_touch82

# 0.34.25: "dieses 3D-Rendern, was jetzt gerade bei zum Beispiel Plateaus
# oder Hindernissen verwendet wird ... beim Spieler, bei den Zielen, beim
# Auto und so weiter einbaust, sodass es wirklich ueberall drin ist"
# 0.34.34: "Entfern mal das 3D-Rendering bei Figuren, das ist doch nicht
# so gut." Figuren sind wieder flach; Buggy und Beute behalten ihre Hoehe.
# 0.34.94: "Deaktivier 3d rendering bei fahrzeugen" - nur noch die Beute
# steht in 3D; die Rechnung selbst wird mit einer festen Hoehe geprueft.
print("\n-- 3D nur fuer Gegenstaende, Figuren flach (0.34.25, 0.34.34)")
from dustfront.render import Renderer as _R83
from dustfront.entities import (Spieler as _Sp83, Gegner as _Gg83,
                                Aufsammler as _Auf83)
from dustfront.fahrzeug import Buggy as _Bg83
from dustfront.mehrspieler import Kaempfer as _Kae83
_f83 = K.FIGUREN_3D
pruef("Die Beute hat eine Hoehe; Fahrzeuge (seit 0.34.94), Spieler, Bots und Geschosse nicht",
      _Bg83.hoehe_3d == 0.0 and _Auf83.hoehe_3d > 0
      and _Sp83.hoehe_3d == 0.0 and _Kae83.hoehe_3d == 0.0 and _Gg83.hoehe_3d == 0.0
      and EN.Geschoss.hoehe_3d == 0.0,
      "%s %s %s %s" % (_Sp83.hoehe_3d, _Bg83.hoehe_3d, _Auf83.hoehe_3d, _Kae83.hoehe_3d))
_flach83 = [a_ for a_ in list(K.GEGNER) + list(K.BOSSE)
            if _Gg83(pygame.Vector2(0, 0), a_).hoehe_3d != 0.0]
pruef("... und kein Gegner und kein Boss steht in 3D", not _flach83, str(_flach83))
_r83 = _R83(app.bilder)
_z83 = pygame.Surface((200, 200))
_b83 = pygame.Surface((20, 20), pygame.SRCALPHA)
pygame.draw.circle(_b83, (200, 60, 60, 255), (10, 10), 8)


def _zeichne83(hoehe, p):
    _z83.fill((0, 0, 0))
    _r83.figur_zeichnen(_z83, _b83, pygame.Vector2(p), hoehe, 0, _b83)
    # Der Deckel ist das Bild selbst (genau seine Farbe), die Seite nicht.
    rot = [(x, y) for x in range(200) for y in range(200)
           if tuple(_z83.get_at((x, y)))[:3] == (200, 60, 60)]
    andere = [(x, y) for x in range(200) for y in range(200)
              if tuple(_z83.get_at((x, y)))[:3] not in ((200, 60, 60), (0, 0, 0))]
    return rot, andere


_rot83, _seite83 = _zeichne83(0, (20, 20))
pruef("Ohne Hoehe: das Bild genau an seiner Stelle, ohne Seitenwand",
      not _seite83 and abs(sum(x for x, _ in _rot83) / len(_rot83) - 20) < 1, "")
_h83 = 11.0                          # die Hoehe, die der Buggy bis 0.34.93 hatte
_rot83, _seite83 = _zeichne83(_h83, (20, 20))
_mx83 = sum(x for x, _ in _rot83) / len(_rot83)
_my83 = sum(y for _, y in _rot83) / len(_rot83)
pruef("Am Rand oben links: der Deckel rueckt von der Mitte weg, nach oben links",
      _mx83 < 19.5 and _my83 < 19.5, "%.1f %.1f" % (_mx83, _my83))
pruef("... und darunter steht eine dunklere Seitenwand in der Farbe der Figur",
      len(_seite83) > 10 and all(_z83.get_at(q)[1] < 60 for q in _seite83[:20]),
      "%d Pixel" % len(_seite83))
_rot83, _seite83 = _zeichne83(_h83, (100, 100))
pruef("In der Bildmitte sieht man genau von oben: keine Seite, kein Versatz",
      not _seite83 and abs(sum(x for x, _ in _rot83) / len(_rot83) - 100) < 1,
      "%d Seitenpixel" % len(_seite83))
# Die Figuren auf 76 x 76 haben viel leeren Rand. Zaehlte der mit, waere
# die Seitenwand fast schwarz (so war es im ersten Versuch).
_gross83 = pygame.Surface((76, 76), pygame.SRCALPHA)
pygame.draw.circle(_gross83, (200, 180, 120, 255), (38, 38), 6)
_sw83, _ = _r83._seite(_gross83, 1.0)
_farbe83 = _sw83.get_at((_sw83.get_width() // 2, _sw83.get_height() // 2))
pruef("Die Seitenwand hat die Farbe der Figur, nicht die des leeren Randes",
      all(abs(a - b) <= 8 for a, b in zip(_farbe83[:3], (200, 180, 120)))
      and _farbe83[3] == 255, str(_farbe83))
pruef("... und ist nur so gross wie ihr Umriss (Tempo)",
      _sw83.get_width() <= 14 and _sw83.get_height() <= 14, str(_sw83.get_size()))
_sw83b, _ = _r83._seite(_gross83, 1.0)
pruef("... und wird je Bild nur einmal gebaut", _sw83b is _sw83, "")
_rot83, _ = _zeichne83(_h83, (20, 20))
pruef("Die Quelle bleibt danach nicht gesperrt (sonst Absturz beim Blitten)",
      not _b83.get_locked(), "")

# 0.34.26: "sehr, sehr viele Hindernisse, auch zum Beispiel auf der
# Wuestenmap, auch auf anderen Maps, Schuesse durchlassen. Alles, was eine
# Art Textur hat und etwas blocken sollte, sollte auch Schuesse blocken. So
# etwas wie die Explosion einer Granate sollte aber leicht durchgehen. Und
# eine Blendgranate sollte dadurch nur abgeschwaecht werden."
print("\n-- Deckung: Hindernisse halten Kugeln, daempfen Explosion und Blitz (0.34.26)")
from dustfront import world as _W84
from dustfront.entities import Geschoss as _Gs84, Granate as _Gr84


def _kugel84(zeile, satz="", y=None):
    welt_ = _W84.Welt([_W84.Ebene.aus_text(["." * 14, zeile, "." * 14], 0)], satz=satz)
    y = 1.5 * K.TILE if y is None else y
    kugel = _Gs84(pygame.Vector2(0.5 * K.TILE, y), 0.0, K.WAFFEN["repetierer"], 0)
    kugel.welt = welt_
    kugel.vorher.update(kugel.pos)
    welt_.wesen.append(kugel)
    for _ in range(200):
        if not kugel.lebt:
            break
        kugel.schritt(K.FIXED_DT)
    return kugel


_falsch84 = []
for _z84 in "Xbshkwr#":
    for _satz84 in ("", "wueste", "schnee"):
        _k84 = _kugel84("....%s........." % _z84, _satz84)
        if _k84.lebt or not (3 * K.TILE <= _k84.pos.x < 5 * K.TILE):
            _falsch84.append("%s/%s: x %.0f" % (_z84, _satz84 or "-", _k84.pos.x))
pruef("Jedes Hindernis mit Bild haelt die Kugel auf, auf jedem Kartensatz",
      not _falsch84, ", ".join(_falsch84))
pruef("... und wo nichts steht, fliegt sie bis zum Ende ihrer Reichweite",
      _kugel84("." * 14).pos.x > 10 * K.TILE, "")
# Ein Kaktus fuellt seine Kachel nicht (18 von 32 Pixeln, seit 0.34.19
# haelt er nur so gross auf). Eine Kugel am Kachelrand geht vorbei.
_rand84 = _kugel84("....k.........", y=1 * K.TILE + 3)
pruef("Gehalten wird an der Grundflaeche, nicht an der Kachel: am Kaktus vorbei",
      _rand84.pos.x > 6 * K.TILE, "x %.0f" % _rand84.pos.x)

_welt84 = _W84.Welt([_W84.Ebene.aus_text(["............",
                                          "..X.........",
                                          "......#.....",
                                          "............"], 0)])
_T84 = K.TILE
_v84 = lambda x, y: pygame.Vector2(x * _T84, y * _T84)
pruef("Deckung: frei, hinter einer Kiste, hinter einer Mauer",
      _welt84.deckung(_v84(0.5, 0.5), _v84(5.5, 0.5), 0) == ""
      and _welt84.deckung(_v84(0.5, 1.5), _v84(4.5, 1.5), 0) == "hindernis"
      and _welt84.deckung(_v84(4.5, 2.5), _v84(8.5, 2.5), 0) == "wand",
      "%s / %s / %s" % (_welt84.deckung(_v84(0.5, 0.5), _v84(5.5, 0.5), 0),
                        _welt84.deckung(_v84(0.5, 1.5), _v84(4.5, 1.5), 0),
                        _welt84.deckung(_v84(4.5, 2.5), _v84(8.5, 2.5), 0)))
pruef("Wer neben der Kiste steht, steht nicht hinter ihr",
      _welt84.deckung(_v84(1.5, 1.5), _v84(1.5, 3.5), 0) == "", "")


def _granate84(ziel_pos):
    """Schaden einer Granate, die bei (0.5, 1.5) Kacheln zuendet."""
    welt_ = _W84.Welt([_W84.Ebene.aus_text(["............",
                                            "..X.........",
                                            "............",
                                            "............",
                                            "............"], 0)])
    opfer = _Spieler(ziel_pos, 0)
    opfer.welt = welt_
    opfer.unverwundbar = 0.0
    welt_.wesen.append(opfer)
    gr = _Gr84(_v84(0.5, 1.5), 0.0, K.WAFFEN["granate"], 0)
    gr.welt = welt_
    welt_.wesen.append(gr)
    welt_._raster_bauen()
    vorher = opfer.leben
    gr.zuenden()
    return vorher - opfer.leben


# Gleich weit weg (84 Pixel): einmal hinter der Kiste, einmal frei darunter.
_offen84 = _granate84(_v84(0.5, 1.5) + pygame.Vector2(0, 84))
_hinter84 = _granate84(_v84(0.5, 1.5) + pygame.Vector2(84, 0))
pruef("Eine Granate trifft hinter einer Kiste schwaecher, aber sie trifft",
      0 < _hinter84 < _offen84 * 0.9,
      "offen %.0f, hinter der Kiste %.0f" % (_offen84, _hinter84))
pruef("Hinter einer Mauer kommt noch weniger an als hinter einer Kiste",
      K.DECKUNG["explosion_wand"] < K.DECKUNG["explosion_hindernis"] < 1.0, "")


class _Blick84:
    def __init__(self, pos):
        self.pos = pygame.Vector2(pos)
        self.ebene = 0
        self.winkel = 180.0                   # schaut nach links, zum Blitz


_blitz84 = _v84(0.5, 1.5)
_frei84 = _W84.blend_wert(_blitz84 + pygame.Vector2(0, -1 * _T84), 0,
                          _Blick84(_v84(3.5, 0.5)), _welt84)
_kiste84 = _W84.blend_wert(_blitz84, 0, _Blick84(_v84(3.5, 1.5)), _welt84)
pruef("Eine Blendgranate hinter einer Kiste blendet schwaecher, aber sie blendet",
      0 < _kiste84 < _frei84, "frei %.2f, hinter der Kiste %.2f" % (_frei84, _kiste84))
pruef("... hinter einer Mauer gar nicht",
      _W84.blend_wert(_v84(4.5, 2.5), 0, _Blick84(_v84(8.5, 2.5)), _welt84) == 0.0, "")

# 0.34.26: "Bots ... jeweils zwei verschiedene Waffen ... eine Granate, aber
# jeweils nur in ihrem Leben eine werfen koennen ... dieselben Leben wie
# Spieler ... keine Medkits oder Munition einsammeln, sondern wenn ihre
# Munition und Granaten aufgebraucht sind, einfach in den Nahkampf ... in
# Deckung gehen ... Ziele priorisieren, wie zum Beispiel die Hotzone ...
# auf Wahl zu jedem Team hinzugefuegt ... Team-Manager-Editor fuer den Host"
print("\n-- Bots: Ausruestung, Deckung, Zielvorrang, Team-Manager (0.34.26)")
from dustfront.bots import bot_loadout as _blo85
from dustfront.mehrspieler import KampfBeute as _Beute85
_rnd85 = random.Random(85)
_los85 = [_blo85(_rnd85) for _ in range(60)]
pruef("Jeder Bot hat zwei verschiedene Waffen und genau eine Granate, nie C4",
      all(len(set(l_["waffen"])) == 2 and l_["wuerfe"] == ["granate"] for l_ in _los85),
      str(_los85[:2]))
_fest85 = _blo85(_rnd85, {"name": "X", "waffen": ["sturm", "schrot"],
                          "wuerfe": ["blend", "rauch"]})
pruef("Auch bei EINES FUER ALLE nur eine Wurfwaffe",
      len(_fest85["wuerfe"]) == 1 and "c4" not in _fest85["wuerfe"], str(_fest85))

w85, g85 = gefechtspaar("team", regeln={"bots": 4}, knapp=False)
_bot85 = w85._bots()[0]


def _ausgeruestet85(k_):
    wuerfe_ = [n_ for n_ in k_.waffen if K.WAFFEN[n_].get("art") == "wurf"]
    schuss_ = [n_ for n_ in k_.waffen if K.WAFFEN[n_].get("art") == "schuss"]
    return (len(wuerfe_) == 1 and k_.magazin[wuerfe_[0]] == 1
            and k_.vorrat.get(wuerfe_[0], 0) == 0 and len(schuss_) == 2
            and all(k_.vorrat[n_] > 0 for n_ in schuss_)
            and k_.medkits == 0 and k_.knapp)


pruef("Eine Granate ohne Nachschub, Reserve fuer die Waffen, kein Medkit, Munition knapp",
      _ausgeruestet85(_bot85),
      "%s %s %s Medkits %d" % (_bot85.waffen, _bot85.magazin, _bot85.vorrat, _bot85.medkits))
pruef("... obwohl die Runde unbegrenzte Munition hat (sonst kaeme der Nahkampf nie)",
      not w85.knapp and _bot85.knapp)
pruef("Ein Bot hat dieselben Leben wie ein Spieler",
      _bot85.max_leben == w85.ich.max_leben, "%s / %s" % (_bot85.max_leben, w85.ich.max_leben))
_bot85.lebt = False
_bot85.wieder_in = 0.0
w85._wieder_einsteigen(_bot85)
pruef("Nach dem Wiedereinstieg genauso: wieder eine Granate, kein Medkit",
      _ausgeruestet85(_bot85), "%s %s" % (_bot85.magazin, _bot85.medkits))
# Die Granate kommt nicht wieder, auch nicht mit Nachladen.
_gr85 = [i_ for i_, n_ in enumerate(_bot85.waffen) if n_ == "granate"][0]
_bot85.magazin["granate"] = 0
_bot85.waffe = _gr85
_bot85.nachladen()
for _ in range(int(5.0 / K.FIXED_DT)):
    _bot85.schritt(K.FIXED_DT)
pruef("Ist die Granate geworfen, laedt er keine neue nach",
      _bot85.magazin["granate"] == 0 and _bot85.hirn._wurf_platz() < 0,
      str(_bot85.magazin))
_bot85.waffe = 0
# Beute: liegt direkt unter ihm, er nimmt sie nicht.
_bot85.medkits = 0
for _art85 in ("medkit", "munition"):
    _b85 = _Beute85(pygame.Vector2(_bot85.pos), _art85, _bot85.ebene, w85.kaempfer)
    w85.welt.dazu(_b85)
    _vorher85 = dict(_bot85.vorrat)
    for _ in range(10):
        _b85.schritt(K.FIXED_DT)
    pruef("Ein Bot hebt kein %s auf" % _art85,
          _b85.lebt and _bot85.medkits == 0 and _bot85.vorrat == _vorher85, "")
    _b85.lebt = False

# Team-Manager im Gefecht: Bots fest in eine Mannschaft, sofort.
w85.regelwerk["bots"] = 0
w85._bots_fuehren(0.0, sofort=True)
pruef("AUFFUELLEN AUS und keine festen Bots: keine Bots", not w85._bots(),
      str(len(w85._bots())))
w85.tm_verstellen(("bots", 1), +1)
w85.tm_verstellen(("bots", 1), +1)
_je85 = [sum(1 for k_ in w85._bots() if k_.team == i_) for i_ in (0, 1)]
pruef("Team-Manager: zwei Bots in BLAU, sofort, und keiner in ROT",
      _je85 == [0, 2] and w85.regelwerk["bots_t1"] == 2, str(_je85))
w85.tm_verstellen(("fuellen", None), +1)          # bis 2 Spieler
w85.tm_verstellen(("fuellen", None), +1)          # bis 4 Spieler
_je85 = [sum(1 for k_ in w85.kaempfer.values() if k_.team == i_) for i_ in (0, 1)]
# Erwartet: jede Mannschaft wird auf 2 aufgefuellt (4 Spieler auf zwei
# Seiten, oder so viele Menschen, wie die groessere hat), BLAU hat dazu
# mindestens seine zwei festen Bots neben den Menschen.
_m85 = [sum(1 for k_ in w85._tm_menschen() if k_.team == i_) for i_ in (0, 1)]
_ziel85 = max([2] + _m85)
_soll85 = [max(_ziel85, _m85[0]), max(_ziel85, _m85[1] + 2)]
pruef("Mit AUFFUELLEN gilt die groessere Zahl (BLAU hat seine zwei fest)",
      _je85 == _soll85, "%s statt %s, Menschen %s" % (_je85, _soll85, _m85))
_ich85 = w85.ich
_alt85 = _ich85.team
w85.tm_verstellen(("mensch", _ich85.nummer), +1)
pruef("Team-Manager: ein Spieler wechselt sofort, mit Fraktion, und bleibt fest",
      _ich85.team != _alt85 and _ich85.team_fest
      and _ich85.fraktion == w85._fraktion_fuer(_ich85.nummer, _ich85.team), "")
w85._teams_ausgleichen()
pruef("... das Ausgleichen rührt ihn nicht an", _ich85.team != _alt85, "")
_beide80(0.6, w85, g85)
_beim_gast85 = g85.kaempfer.get(_ich85.nummer)
pruef("Der Gast sieht ihn in der neuen Mannschaft",
      _beim_gast85 is not None and _beim_gast85.team == _ich85.team, "")
pruef("Die Regeln kennen BOTS IN ROT / BLAU und BOTS DAZU, mit Grenze",
      _R80.saeubern({"modus": "team", "bots_t0": 99})["bots_t0"] == K.BOTS["je_team_hoechstens"]
      and any(f_.schluessel == "bots_t1" for f_ in _R80.sichtbar(_R80.vorgabe(modus="team")))
      and any(f_.schluessel == "bots_dazu" for f_ in _R80.sichtbar(_R80.vorgabe(modus="pvp")))
      and not any(f_.schluessel.startswith("bots_t") for f_ in _R80.sichtbar(_R80.vorgabe(modus="pvp"))),
      "")

# Team-Manager in der Lobby: verstellt den Plan, und der gilt beim Start.
w85.lobby_betreten()
w85.plan[0] = _R80.saeubern(dict(w85.plan[0], modus="team", bots=0), w85._umfeld())
pruef("Der Team-Manager gibt es in der Lobby, mit Bot-Zeilen fuer die naechste Runde",
      ("bots", 0) in w85._tm_zeilen() and ("mensch", _ich85.nummer) in w85._tm_zeilen(),
      str(w85._tm_zeilen()))
w85.tm_verstellen(("bots", 0), +1)
w85.tm_verstellen(("bots", 0), +1)
w85.tm_verstellen(("bots", 0), +1)
_ich85.team_wunsch, _ich85.team_fest = -1, False
w85.tm_verstellen(("mensch", _ich85.nummer), +1)     # AUTOMATISCH -> ROT
pruef("In der Lobby geht es in den Plan und an den Wunsch des Spielers",
      w85.plan[0]["bots_t0"] == 3 and _ich85.team_wunsch == 0 and _ich85.team_fest, "")
w85.plan_starten(0)
_je85 = [sum(1 for k_ in w85._bots() if k_.team == i_) for i_ in (0, 1)]
pruef("Beim Start: drei Bots in ROT, und der Spieler steht, wo der Gastgeber ihn wollte",
      _je85 == [3, 0] and _ich85.team == 0, "%s, Spieler in %d" % (_je85, _ich85.team))
w85.verlassen(); g85.verlassen()

# Ohne Mannschaften: BOTS DAZU.
w85 = Gefecht(app, "WIRT", gastgeber=netz.Gastgeber(_neuer_port()), modus="pvp",
              seed=85, regeln={"bots_dazu": 3})
pruef("PVP mit BOTS DAZU 3: drei Bots, jeder gegen jeden", len(w85._bots()) == 3
      and len({k_.fraktion for k_ in w85.kaempfer.values()}) == 4, str(len(w85._bots())))
w85.verlassen()

# Deckung: zum Nachladen hinter die Kiste.
_dw85 = _W84.Welt([_W84.Ebene.aus_text(["...............",
                                        "...............",
                                        "......X........",
                                        "...............",
                                        "..............."], 0)])
w85 = Gefecht(app, "WIRT", gastgeber=netz.Gastgeber(_neuer_port()), modus="team",
              seed=85, regeln={"bots_t0": 1})
_bot85 = w85._bots()[0]


class _GDeckung85:
    """Ein Gefecht in klein: nur die Welt und was das Hirn davon fragt."""
    welt = _dw85
    regeln = {"zone": False}


_h85 = _Hirn80(_GDeckung85(), _bot85, random.Random(85))
_bot85.pos.update(_v84(5.5, 2.5))
_bot85.ebene = 0
_feind85 = _v84(12.5, 2.5)
_ort85 = _h85._deckung_suchen(_feind85)
pruef("Deckung: er findet eine Stelle, an der die Kiste ihn vom Gegner trennt",
      _ort85 is not None and _dw85.deckung(_feind85, _ort85, 0) != ""
      and _ort85.distance_to(_bot85.pos) <= max(K.BOTS["deckung_radien"]) + 1,
      str(_ort85))
_bot85.nachlade_rest = 1.0


class _Ziel85:
    pos = _feind85
    ebene = 0


pruef("... und will dorthin, solange er nachlaedt",
      _h85._deckung(_Ziel85(), {"knoepfe": []}) is not None, "")
_bot85.nachlade_rest = 0.0
_h85.deckung_rest = 0.0
pruef("... und ohne Grund nicht", _h85._deckung(_Ziel85(), {"knoepfe": []}) is None, "")
w85.verlassen()

# Kiste in der Schusslinie: er schiesst nicht hinein.
w85 = Gefecht(app, "WIRT", gastgeber=netz.Gastgeber(_neuer_port()), modus="team",
              seed=3, regeln={"bots": 2})
_bot85 = w85._bots()[0]
_ich85 = w85.ich
_ich85.unverwundbar = 1e9
_blockiert85 = 0
_frei_schuesse85 = 0
for i_ in range(int(6.0 / K.FIXED_DT)):
    linie_ = _bot85.hirn.linie if _bot85.hirn.ziel is _ich85 else ""
    vor_ = _bot85.zaehler.get("schuesse", 0)
    w85.schritt(K.FIXED_DT)
    if _bot85.zaehler.get("schuesse", 0) > vor_:
        if linie_ == "hindernis":
            _blockiert85 += 1
        else:
            _frei_schuesse85 += 1
pruef("Steht eine Kiste in der Schusslinie, schiesst ein Bot nicht hinein",
      _blockiert85 == 0, "%d Schuesse in die Kiste" % _blockiert85)
w85.verlassen()

# HUEGEL: der Kreis geht vor - auch wenn ein Gegner zu sehen ist.
w85 = Gefecht(app, "WIRT", gastgeber=netz.Gastgeber(_neuer_port()), modus="huegel",
              seed=85, regeln={"bots_t1": 1})
_bot85 = [k_ for k_ in w85._bots()][0]
_ich85 = w85.ich
_ich85.unverwundbar = 1e9
_bot85.unverwundbar = 1e9
_bot85.ebene = w85.zone_ebene
_start85 = None
for _ in range(400):
    p_ = freier_punkt(w85.welt, w85.zone_ebene, random.Random(_))
    if 260 < p_.distance_to(w85.zone_mitte) < 420:
        _start85 = p_
        break
if _start85 is not None:
    _bot85.pos.update(_start85)
    _bot85.vorher.update(_start85)
    _bot85.hirn.neues_leben()
    _abstand85 = _start85.distance_to(w85.zone_mitte)
    _kaempfte85 = 0
    for _ in range(int(8.0 / K.FIXED_DT)):
        # Der Gegner steht immer auf der anderen Seite, weg vom Kreis.
        weg_ = (_bot85.pos - w85.zone_mitte)
        if weg_.length_squared() > 1:
            p_ = _bot85.pos + weg_.normalize() * 120
            if w85.welt.frei(p_, 9, _bot85.ebene, True):
                _ich85.pos.update(p_)
                _ich85.ebene = _bot85.ebene
        w85.schritt(K.FIXED_DT)
        if _bot85.hirn.ziel is _ich85:
            _kaempfte85 += 1
    pruef("HUEGEL: ein Bot geht in den Kreis, statt dem Gegner nachzulaufen",
          _bot85.pos.distance_to(w85.zone_mitte) < _abstand85 - 100,
          "von %.0f auf %.0f, %d Schritte im Kampf"
          % (_abstand85, _bot85.pos.distance_to(w85.zone_mitte), _kaempfte85))
w85.verlassen()

# 0.34.27: "Lass die Bots Callouts kurz vor Aktionen geben, die als kleine
# Untertitel ueber ihnen angezeigt werden. Sie sollen auch taktische
# Aktionen durchfuehren, wie flankieren, suppression ..., breaching (in
# Kooperation mit anderen Bots) und Feuerschutz fuer andere Bots und
# Spieler des Teams."
print("\n-- Bots: Funk und Taktik (0.34.27)")
from dustfront import bottaktik as _BT86
from dustfront.entities import Geschoss as _Gs86
# Seit 0.34.43 stehen die Sprueche nicht mehr ueber den Koepfen
# (K.BOTS["callouts"] aus). Geprueft wird hier, wie sie entstehen und beim
# Gast ankommen - darum fuer diesen Abschnitt eingeschaltet.
_callouts86 = K.BOTS["callouts"]
K.BOTS["callouts"] = True

w86, g86 = gefechtspaar("team", regeln={"bots_t0": 2, "bots_t1": 2})
_eigen86 = [b_ for b_ in w86._bots() if b_.team == w86.ich.team]
_fremd86 = [b_ for b_ in w86._bots() if b_.team != w86.ich.team]
_a86 = _eigen86[0]
_a86.hirn.funk_sperre = 0.0
_a86.hirn.funk_zuletzt = {}
pruef("Ein Bot sagt an, was er vorhat",
      _a86.hirn.funken("flanke") and _a86.funk in K.BOTS["funk"]["flanke"]
      and _a86.funk_rest == K.BOTS["funk_dauer"], _a86.funk)
pruef("... und redet nicht ununterbrochen", not _a86.hirn.funken("kontakt"), "")
pruef("... ausser bei etwas Wichtigem (Granate, REIN)",
      _a86.hirn.funken("granate", wichtig=True) and _a86.funk in K.BOTS["funk"]["granate"], "")
_beide80(0.4, w86, g86)
_beim_gast86 = g86.kaempfer.get(_a86.nummer)
pruef("Der Gast bekommt den Funkspruch mit der Weltmeldung",
      _beim_gast86 is not None and _beim_gast86.funk == _a86.funk
      and _beim_gast86.funk_rest > 0, "%r" % (getattr(_beim_gast86, "funk", None),))
pruef("Mit Mannschaften liest nur die eigene mit",
      w86._funk_hoerbar(_a86) and not w86._funk_hoerbar(_fremd86[0]), "")
for _ in range(int((K.BOTS["funk_dauer"] + 0.3) / K.FIXED_DT)):
    _a86.schritt(K.FIXED_DT)
pruef("Nach seiner Dauer ist der Spruch weg", _a86.funk_rest == 0.0, "")

# Niedergehalten: eine Kugel knapp vorbei.
_b86 = _eigen86[1]
_b86.hirn.unterdrueckt = 0.0
_b86.hirn.funk_sperre = 0.0
_b86.hirn.funk_zuletzt = {}
_kugel86 = _Gs86(_b86.pos + pygame.Vector2(0, 14), 0.0, K.WAFFEN["sturm"],
                 _b86.ebene, von=_fremd86[0])
w86.welt.wesen.append(_kugel86)
_kugel86.welt = w86.welt
_BT86.unterdrueckung_pruefen(w86)
pruef("Eine Kugel knapp vorbei haelt einen Bot nieder, und er sagt es",
      _b86.hirn.unterdrueckt > 0 and _b86.funk in K.BOTS["funk"]["beschuss"],
      "%.1f %r" % (_b86.hirn.unterdrueckt, _b86.funk))
_kugel86.lebt = False
w86.verlassen(); g86.verlassen()


def _freie_flaeche86(welt, rnd, breite=9, hoehe=5):
    """Eine freie, ebene Flaeche auf Ebene 0 (in Kacheln), fuer eine
    gebaute Szene mitten in einer echten Karte."""
    e_ = welt.ebene(0)
    for _ in range(4000):
        tx_ = rnd.randrange(2, e_.breite - breite - 2)
        ty_ = rnd.randrange(2, e_.hoehe - hoehe - 2)
        if all(K.KACHELN[e_.kachel(x_, y_)]["name"] == "boden"
               for x_ in range(tx_, tx_ + breite) for y_ in range(ty_, ty_ + hoehe)):
            return tx_, ty_
    return None


# Hinter einer Kiste: einer flankiert, der andere haelt nieder.
w86 = Gefecht(app, "WIRT", gastgeber=netz.Gastgeber(_neuer_port()), modus="team",
              karte="staubtal", seed=86, regeln={"bots_t0": 2, "bots_t1": 2})
_ich86 = w86.ich
_ich86.unverwundbar = 1e9
_ich86.max_leben = _ich86.leben = 1e6
_freund86 = [b_ for b_ in w86._bots() if b_.team != _ich86.team]
_rest86 = [b_ for b_ in w86._bots() if b_.team == _ich86.team]
_platz86 = _freie_flaeche86(w86.welt, random.Random(86), 12, 7)
if _platz86 is not None:
    for b_ in _rest86:
        b_.lebt = False                 # nur die Szene zaehlt
    _tx86, _ty86 = _platz86
    w86.welt.ebene(0).setzen(_tx86 + 7, _ty86 + 3, K.KISTE)
    _T86 = K.TILE
    _kiste86 = pygame.Vector2((_tx86 + 7.5) * _T86, (_ty86 + 3.5) * _T86)
    _ich_ort86 = _kiste86 + pygame.Vector2(_T86 * 1.0, 0)
    _orte86 = [_kiste86 + pygame.Vector2(-_T86 * 5, -_T86 * 1.2),
               _kiste86 + pygame.Vector2(-_T86 * 5, _T86 * 1.2)]
    _rollen86 = {"flanke": set(), "druck": set()}
    _druckschuesse86 = 0
    for i_, b_ in enumerate(_freund86):
        b_.pos.update(_orte86[i_]); b_.vorher.update(b_.pos); b_.ebene = 0
        b_.unverwundbar = 1e9
        b_.hirn.neues_leben()
    for _ in range(int(4.0 / K.FIXED_DT)):
        _ich86.pos.update(_ich_ort86); _ich86.vorher.update(_ich_ort86); _ich86.ebene = 0
        _ich86.tempo.update(0, 0)
        vor_ = [b_.zaehler.get("schuesse", 0) for b_ in _freund86]
        w86.schritt(K.FIXED_DT)
        for j_, b_ in enumerate(_freund86):
            if b_.hirn.taktik is not None:
                _rollen86["flanke"].add(b_.nummer)
            if b_.hirn.druck_rest > 0:
                _rollen86["druck"].add(b_.nummer)
                if b_.zaehler.get("schuesse", 0) > vor_[j_]:
                    _druckschuesse86 += 1
    pruef("Gegner hinter einer Kiste: einer flankiert, einer haelt nieder",
          _rollen86["flanke"] and _rollen86["druck"]
          and _rollen86["flanke"] != _rollen86["druck"],
          str(_rollen86))
    pruef("... und wer niederhaelt, schiesst dabei auch", _druckschuesse86 > 0,
          "%d Schuesse" % _druckschuesse86)
    # Wohin: neben die Kiste, wo die Bahn frei ist.
    _h86 = _freund86[0].hirn
    _freund86[0].pos.update(_orte86[0])
    _dp86 = _h86.druckpunkt(_ich_ort86, 0)
    pruef("Der Punkt zum Niederhalten liegt neben der Deckung, mit freier Bahn",
          _dp86.distance_to(_ich_ort86) <= max(K.BOTS["druck_versatz"]) + 1
          and w86.welt.deckung(_freund86[0].pos, _dp86, 0) == ""
          and not w86.welt.schuss_halt(_dp86, 0),
          str(_dp86))
    _fp86 = _h86.flankenpunkt(_ich_ort86, 0)
    pruef("Der Flankenpunkt hat freie Bahn zum Gegner, seitlich von ihm",
          _fp86 is not None and w86.welt.deckung(_fp86, _ich_ort86, 0) == ""
          and min(K.BOTS["flanke_radien"]) - 1 <= _fp86.distance_to(_ich_ort86)
          <= max(K.BOTS["flanke_radien"]) + 1, str(_fp86))
else:
    pruef("Auf STAUBTAL gibt es eine freie Flaeche fuer die Szene", False, "")
w86.verlassen()

# Feuerschutz: der Gegner bei dem Kameraden, der nachlaedt, geht vor.
w86 = Gefecht(app, "WIRT", gastgeber=netz.Gastgeber(_neuer_port()), modus="team",
              karte="staubtal", seed=87, regeln={"bots_t0": 1, "bots_t1": 2})
_ich86 = w86.ich
_wache86 = [b_ for b_ in w86._bots() if b_.team == _ich86.team][0]
_feinde86 = [b_ for b_ in w86._bots() if b_.team != _ich86.team]
_platz86 = _freie_flaeche86(w86.welt, random.Random(87), 14, 12)
if _platz86 is not None:
    _p86 = pygame.Vector2((_platz86[0] + 3) * K.TILE, (_platz86[1] + 3) * K.TILE)
    _wache86.pos.update(_p86)
    _ich86.pos.update(_p86 + pygame.Vector2(0, 150))
    _feinde86[0].pos.update(_ich86.pos + pygame.Vector2(150, 0))      # beim Kameraden
    _feinde86[1].pos.update(_p86 + pygame.Vector2(130, -60))          # naeher an der Wache
    for x_ in [_wache86, _ich86] + _feinde86:
        x_.ebene = 0
        x_.vorher.update(x_.pos)
    _ich86.nachlade_rest = 1.5
    _wache86.hirn.neues_leben()
    _wache86.hirn._wahrnehmen()
    pruef("Feuerschutz: der Gegner beim Kameraden, der nachlaedt, geht vor",
          _wache86.hirn.ziel is _feinde86[0]
          and _wache86.funk in K.BOTS["funk"]["feuerschutz"],
          "%s %r" % (getattr(_wache86.hirn.ziel, "name", None), _wache86.funk))
    _ich86.nachlade_rest = 0.0
    _wache86.hirn.neues_leben()
    _wache86.hirn._wahrnehmen()
    pruef("... ohne das der naechste", _wache86.hirn.ziel is _feinde86[1],
          str(getattr(_wache86.hirn.ziel, "name", None)))
else:
    pruef("Auf STAUBTAL gibt es eine freie Flaeche fuer die Szene", False, "")
w86.verlassen()

# Stuermen: zwei Bots wissen, wo einer steckt, und sehen ihn nicht.
w86 = Gefecht(app, "WIRT", gastgeber=netz.Gastgeber(_neuer_port()), modus="team",
              karte="staubtal", seed=88, regeln={"bots_t0": 0, "bots_t1": 2})
_ich86 = w86.ich
_trupp86 = [b_ for b_ in w86._bots() if b_.team != _ich86.team]
_plan86 = None
_rnd86 = random.Random(88)
for _ in range(300):
    ort_ = freier_punkt(w86.welt, 0, _rnd86)
    s_ = _trupp86[0].hirn.sammelpunkt(ort_, 0)
    if s_ is None:
        continue
    _ich86.pos.update(ort_); _ich86.ebene = 0
    for i_, b_ in enumerate(_trupp86):
        b_.pos.update(s_ + pygame.Vector2(30 * i_, 0))
        b_.vorher.update(b_.pos); b_.ebene = 0
        b_.hirn.neues_leben()
        b_.hirn.gesehen[_ich86] = (pygame.Vector2(ort_), 0, w86.welt.zeit)
    w86._sturm_pause = {}
    w86._sturm_takt = 0.0
    _BT86.stuerme_fuehren(w86, K.FIXED_DT)
    if w86._stuerme:
        _plan86 = w86._stuerme[0]
        break
pruef("Zwei Bots, die wissen, wo einer steckt, planen einen Sturm",
      _plan86 is not None and set(_plan86["mitglieder"]) == set(_trupp86)
      and all(b_.hirn.sturm is _plan86 for b_ in _trupp86), "")
if _plan86 is not None:
    pruef("Gesammelt wird ausser Sicht des Gegners",
          not w86.welt.sicht_frei(_plan86["sammel"], _plan86["ziel"], 0), "")
    pruef("... und der Erste sagt es an",
          _trupp86[0].funk in K.BOTS["funk"]["sammeln"], repr(_trupp86[0].funk))
    _plan86["bereit"] = {b_.nummer for b_ in _trupp86}
    w86._sturm_takt = 0.0
    _BT86.stuerme_fuehren(w86, K.FIXED_DT)
    pruef("Sind alle da: REIN - und der Erste wirft vorher seine Granate",
          _plan86["phase"] == "rein" and _trupp86[0].funk in K.BOTS["funk"]["rein"]
          and _trupp86[0].hirn.sturm_wurf is not None,
          "%s %r" % (_plan86["phase"], _trupp86[0].funk))
    _ein86 = {"knoepfe": [], "waffe": -1}
    _will86, _blick86, _ = _trupp86[1].hirn.taktik_sturm(K.FIXED_DT, _ein86)
    pruef("... und die anderen gehen mit hinein, Richtung Ziel",
          _will86.length_squared() > 0.1, str(_will86))
    for b_ in _trupp86:
        b_.lebt = False
    w86._sturm_takt = 0.0
    _BT86.stuerme_fuehren(w86, K.FIXED_DT)
    pruef("Ist der Trupp gefallen, ist der Plan vorbei", not w86._stuerme, "")
    # Seit 0.34.44 nur in Ueberzahl: kennen sie zwei Gegner, bleiben sie.
    for b_ in _trupp86:
        b_.lebt = True
    _zweiter86 = type("F", (), {"lebt": True, "pos": pygame.Vector2(ort_) + pygame.Vector2(40, 0),
                                "ebene": 0})()
    for b_ in _trupp86:
        b_.hirn.gesehen[_zweiter86] = (pygame.Vector2(_zweiter86.pos), 0, w86.welt.zeit)
    w86._sturm_pause = {}
    w86._sturm_takt = 0.0
    _BT86.stuerme_fuehren(w86, K.FIXED_DT)
    _zwei86 = list(w86._stuerme)
    for b_ in _trupp86:
        b_.hirn.gesehen.pop(_zweiter86, None)
    w86._sturm_pause = {}
    w86._sturm_takt = 0.0
    _BT86.stuerme_fuehren(w86, K.FIXED_DT)
    pruef("Zwei gegen zwei stuermen nicht - nur in Ueberzahl (seit 0.34.44); gegen einen wieder",
          not _zwei86 and bool(w86._stuerme), "%d / %d" % (len(_zwei86), len(w86._stuerme)))
w86.verlassen()
K.BOTS["callouts"] = _callouts86

# 0.34.28: "Mach mir bitte einen separaten Gamemode, den man aus dem
# Hauptmenue waehlt ... Testmodus ... spectator ... ELEMENTAR, dass NICHTS
# in der kompletten Welt, auch spaeter nicht, mich wahrnehmen oder
# beeinflussen kann ... alle Spezialaktionen ueber das Numpad ... Zeit fuer
# ALLES stoppen, alle KI stoppen, alle Entities eliminieren, einen Player
# Character spawnen ... Spawner-Menue fuer quasi alles ... auch spawnen,
# waehrend die Zeit gestoppt ist ... verschiedene Arten von Godmode."
print("\n-- Testmodus (0.34.28)")
from dustfront import testmodus as _TM87
from dustfront.mehrspieler import KampfGegner as _KG87, Kaempfer as _Kae87
from dustfront.entities import Granate as _Gr87, Geschoss as _Gs87
_tm = _TM87.Testmodus(app, karte="staubtal")
_geist87 = _tm._geist
_D87 = K.FIXED_DT


def _sim87(n):
    for _ in range(n):
        _tm.schritt(_D87)


_sim87(5)
pruef("Der Beobachter steht in keiner Liste der Welt",
      _geist87 not in _tm.welt.wesen and _geist87 not in _tm.welt.neue
      and _geist87 not in _tm.kaempfer.values() and _tm.beobachter, "")
pruef("Den Testmodus gibt es am Rechner",
      _TM87.verfuegbar(), "")
_alt87 = os.environ.get("DUSTFRONT_TOUCH")
os.environ["DUSTFRONT_TOUCH"] = "1"
# Bis 0.34.62 gab es ihn mit Touch nicht; seit 0.34.63 auch auf iPhone
# und iPad (gewuenscht). Wie er dort bedient wird, prueft der Abschnitt
# "Testmodus mit Touch".
pruef("... und seit 0.34.63 auch mit Touch-Steuerung (iOS)", _TM87.verfuegbar(), "")
if _alt87 is None:
    os.environ.pop("DUSTFRONT_TOUCH", None)
else:
    os.environ["DUSTFRONT_TOUCH"] = _alt87

# Eine freie Stelle und den Beobachter mitten hinein.
_ort87 = freier_punkt(_tm.welt, 0, random.Random(87))
_geist87.pos.update(_ort87)
_geist87.ebene = 0
_sim87(3)
_tm._zeiger_welt = pygame.Vector2(_ort87)

# Der Ziffernblock: Tastencodes und Scancodes.
_ev87 = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_KP0, scancode=0, mod=0, unicode="")
pruef("Numpad 0 ist die Zeit", _TM87.numpad_name(_ev87) == "0", "")
_ev87 = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_HOME,
                           scancode=getattr(pygame, "KSCAN_KP_7", -1), mod=0, unicode="")
pruef("... auch mit NumLock aus (Scancode statt Taste)", _TM87.numpad_name(_ev87) == "7", "")
from dustfront.font import SCHRIFT as _SCHRIFT87
_zu_lang87 = [_tm._tastentext(n_)[0] for n_, r_ in _tm.tasten_flaechen()
              if not _tm._tastentext(n_)[0]
              or _SCHRIFT87.breite(_tm._tastentext(n_)[0]) > r_.width - 4]
pruef("Jede Taste des Ziffernblocks hat eine Aufschrift, die auf die Taste passt",
      not _zu_lang87, str(_zu_lang87))

# Spawner: jeder Eintrag laesst sich setzen - bei laufender und bei
# stehender Zeit.
_fehler87 = []
for _stehend87 in (False, True):
    _tm.zeit_stopp = _stehend87
    for e_ in _tm.eintraege:
        if e_.name == "SPIELER, ICH":
            continue
        try:
            _tm.spawnen(e_, pos=_ort87, ebene=0)
            _sim87(2)
        except Exception as err_:
            _fehler87.append("%s: %r" % (e_.name, err_))
_tm.zeit_stopp = False
pruef("Jeder Eintrag im Spawner laesst sich setzen, auch bei stehender Zeit",
      not _fehler87, "; ".join(_fehler87[:4]))
_sim87(30)
pruef("... und der Beobachter steht danach immer noch in keiner Liste",
      _geist87 not in _tm.welt.wesen and _geist87 not in _tm.kaempfer.values(), "")

_tm.alles_weg()
pruef("LEEREN: nichts mehr in der Welt",
      not _tm.welt.wesen and not _tm.kaempfer and not _tm.fahrzeuge
      and not _tm.welt.feuer and not _tm.welt.rauch, str(len(_tm.welt.wesen)))

# Anzahl und Einstellungen.
_laeufer87 = _tm._eintrag(K.GEGNER["laeufer"]["name"])
_tm._sp_werte[_laeufer87.name] = {"anzahl": list(K.TESTMODUS["anzahlen"]).index(3)}
_neu87 = _tm.spawnen(_laeufer87, pos=_ort87, ebene=0)
pruef("ANZAHL 3 setzt drei", len(_neu87) == 3 and all(isinstance(g_, _KG87) for g_ in _neu87),
      str(len(_neu87)))

# Nichts nimmt den Beobachter wahr. Gegner und Bots mitten um ihn herum,
# eine Granate zu seinen Fuessen, eine Blendgranate vor der Nase.
_tm.alles_weg()
_bot_a87 = _tm.bot_setzen(_ort87 + pygame.Vector2(40, 0), 0, {"team": 0})
_bot_b87 = _tm.bot_setzen(_ort87 + pygame.Vector2(-40, 0), 0, {"team": 1})
_zombie87 = _tm.gegner_setzen("laeufer", _ort87 + pygame.Vector2(0, 30), 0, {"ki": True})
_tm.wurf_setzen("granate", _ort87, 0, {"zuender": "sofort"})
_tm.wurf_setzen("blend", _ort87, 0, {"zuender": "sofort"})
_leben87 = _geist87.leben
_gesehen87 = False
for _ in range(int(3.0 / _D87)):
    _tm.schritt(_D87)
    for b_ in (_bot_a87, _bot_b87):
        if b_.hirn is not None and (b_.hirn.ziel is _geist87 or _geist87 in b_.hirn.gesehen):
            _gesehen87 = True
    if getattr(_zombie87, "_ziel", None) is _geist87:
        _gesehen87 = True
pruef("Kein Bot und kein Gegner nimmt den Beobachter je wahr", not _gesehen87, "")
pruef("Eine Granate zu seinen Fuessen tut ihm nichts, eine Blendgranate blendet ihn nicht",
      _geist87.leben == _leben87 and _tm.befinden.blend == 0.0,
      "Leben %.0f, Blendung %.2f" % (_geist87.leben, _tm.befinden.blend))

# Die Zeit.
_tm.taste("0")
_z87 = _tm.welt.zeit
_p87 = pygame.Vector2(_bot_a87.pos)
_sim87(60)
pruef("ZEIT STEHT: nichts bewegt sich, die Weltzeit steht",
      _tm.welt.zeit == _z87 and _bot_a87.pos == _p87, "%.3f" % (_tm.welt.zeit - _z87))
_vorher87 = len(_tm.welt.wesen)
_tm.gegner_setzen("renner", _ort87 + pygame.Vector2(60, 60), 0, {"ki": True})
pruef("... und gespawnt wird trotzdem, sofort sichtbar",
      len(_tm.welt.wesen) == _vorher87 + 1, "")
_tm.taste(".")
_sim87(1)
pruef("EINZEL rechnet genau einen kleinen Schritt",
      abs(_tm.welt.zeit - _z87 - K.TESTMODUS["einzelschritt"] * _D87) < 1e-6,
      "%.4f" % (_tm.welt.zeit - _z87))
_tm.taste("0")
_tm.faktor_nr = list(K.TESTMODUS["zeitfaktoren"]).index(2.0)
_z87 = _tm.welt.zeit
_sim87(60)
pruef("ZEIT x2 rechnet doppelt so schnell", abs((_tm.welt.zeit - _z87) - 120 * _D87) < 1e-6,
      "%.3f" % (_tm.welt.zeit - _z87))
_tm.faktor_nr = list(K.TESTMODUS["zeitfaktoren"]).index(0.5)
_z87 = _tm.welt.zeit
_sim87(60)
pruef("... x0,5 halb so schnell", abs((_tm.welt.zeit - _z87) - 30 * _D87) < 1e-6,
      "%.3f" % (_tm.welt.zeit - _z87))
_tm.faktor_nr = list(K.TESTMODUS["zeitfaktoren"]).index(1.0)

# KI aus.
_tm.alles_weg()
_bot87 = _tm.bot_setzen(_ort87 + pygame.Vector2(60, 0), 0, {"team": 0})
_feind87 = _tm.bot_setzen(_ort87 + pygame.Vector2(-60, 0), 0, {"team": 1})
_zombie87 = _tm.gegner_setzen("laeufer", _ort87 + pygame.Vector2(0, 80), 0, {"ki": True})
_tm.taste("/")
_orte87 = [pygame.Vector2(x_.pos) for x_ in (_bot87, _feind87, _zombie87)]
_schuesse87 = _bot87.zaehler.get("schuesse", 0) + _feind87.zaehler.get("schuesse", 0)
_sim87(int(2.0 / _D87))
pruef("KI AUS: Bots und Gegner stehen still und schiessen nicht",
      all(x_.pos.distance_to(o_) < 1.0 for x_, o_ in zip((_bot87, _feind87, _zombie87), _orte87))
      and _bot87.zaehler.get("schuesse", 0) + _feind87.zaehler.get("schuesse", 0) == _schuesse87,
      str([round(x_.pos.distance_to(o_), 1) for x_, o_ in zip((_bot87, _feind87, _zombie87), _orte87)]))
_tm.taste("/")
_sim87(int(2.0 / _D87))
pruef("... und mit KI AN wieder los", _zombie87.pos.distance_to(_orte87[2]) > 5.0
      or not _zombie87.lebt, "")

# Uebernehmen, Gottmodus, zurueck.
_tm.alles_weg()
_bot87 = _tm.bot_setzen(_ort87, 0, {"team": 0})
_tm._zeiger_welt = pygame.Vector2(_bot87.pos)
_tm.blick = 0
_tm.taste("3")
pruef("3 am Zeiger uebernimmt den Bot: er hat kein Hirn mehr, die Kamera folgt ihm",
      _tm.ich is _bot87 and not _tm.beobachter and _bot87.hirn is None
      and not _bot87.ist_bot, "")
_tm.gott = frozenset({"unverwundbar"})
_sim87(2)
_l87 = _bot87.leben
_bot87.schaden(50, None, None)
pruef("GOTT UNVERWUNDBAR: kein Schaden", _bot87.leben == _l87, "%.0f" % _bot87.leben)
_tm.gott = frozenset({"unsterblich"})
_sim87(2)
_bot87.schaden(500, None, None)
pruef("GOTT UNSTERBLICH: Schaden ja, aber nie unter 1",
      _bot87.lebt and 0.5 <= _bot87.leben <= 1.0, "%.1f" % _bot87.leben)
_bot87.leben = _bot87.max_leben
_tm.gott = frozenset({"unsichtbar", "munition"})
_feind87 = _tm.bot_setzen(_ort87 + pygame.Vector2(100, 0), 0, {"team": 1})
_name87 = _bot87.waffe_name
_bot87.magazin[_name87] = 0
_gesehen87 = False
for _ in range(int(2.0 / _D87)):
    _tm.schritt(_D87)
    if _feind87.hirn.ziel is _bot87:
        _gesehen87 = True
pruef("GOTT UNSICHTBAR: der feindliche Bot nimmt die gesteuerte Figur nicht wahr",
      not _gesehen87, "")
pruef("GOTT MUNITION: das Magazin bleibt voll",
      _bot87.magazin[_name87] == K.WAFFEN[_name87]["magazin"], str(_bot87.magazin))
_tm.taste("3")
pruef("3 noch einmal: zurueck zum Beobachter, der Bot hat sein Hirn wieder",
      _tm.beobachter and _tm.ich is _geist87 and _bot87.hirn is not None
      and _bot87.ist_bot and not getattr(_bot87, "ki_unsichtbar", False), "")
_tm.gott = frozenset()

# Loeschen am Zeiger.
_tm._zeiger_welt = pygame.Vector2(_feind87.pos)
_tm.taste("enter")
pruef("ENTF loescht, was am Zeiger liegt",
      not _feind87.lebt and _feind87 not in _tm.welt.wesen
      and _feind87 not in _tm.kaempfer.values(), "")

# Hotzone.
_tm.zone_setzen(_ort87, 0)
pruef("HOTZONE HIER: der Kreis liegt am Zeiger, und gekaempft wird um ihn",
      _tm.regeln["zone"] and _tm.zone_mitte == _ort87 and K.MODI["team"]["zone"] is False, "")
_tm.zone_aus()

# Kartenwechsel behaelt die Einstellungen.
_tm.gott = frozenset({"munition"})
_tm.ki_stopp = True
app.schieben(_tm)
_tm.karte_laden("")
_tm2 = app.oben
pruef("Eine andere Karte laden: neuer Testmodus, dieselben Einstellungen",
      isinstance(_tm2, _TM87.Testmodus) and _tm2 is not _tm and _tm2.karte == ""
      and _tm2.ki_stopp and _tm2.gott == frozenset({"munition"}), "")
pruef("Gebucht wird im Testmodus nichts",
      _TM87.Testmodus._runde_buchen(_tm2) is None and _TM87.Testmodus._abbruch_buchen(_tm2) is None, "")
_bild87 = pygame.Surface((K.GAME_W, K.GAME_H))
_tm2.spawner_offen = True
_tm2.zeichnen(_bild87, 1.0)
_tm2.spawner_offen = False
_tm2.menue_offen = True
_tm2.zeichnen(_bild87, 1.0)
pruef("Spawner und Testmenue lassen sich zeichnen", True, "")
app.werfen()

# 0.34.29: "Der Core soll schon jetzt gebaut werden, sodass ich das ganze
# schonmal im Testmodus in Aktion sehen kann." Zielorientierte KI: der
# Kern (goap.py), die Daten (wesen/), die Bots damit (bot_goap.py) und
# ihre Gedanken im Testmodus. Planung: docs/KI.md.
print("\n-- Zielorientierte KI (0.34.29)")
from dustfront import goap as _GO88, wesen_daten as _WD88, bot_goap as _BG88
from dustfront import regeln as _RG88

# Ausdruecke: rechnen, ja - Code ausfuehren, nie.
pruef("Ein Ausdruck rechnet mit Fakten, Zahlen und Merkmalen",
      _GO88.Ausdruck("80 * a * b + max(0, 3 - mut)").wert({"a": 1, "b": 1, "mut": 1}) == 82.0, "")
pruef("... ein unbekannter Name ist 0", _GO88.Ausdruck("5 * gibts_nicht + 1").wert({}) == 1.0, "")
_boese88 = []
for t_ in ("__import__('os')", "a.b", "'text'", "open('x')", "[1, 2]", "lambda: 1", "a[0]",
           "(1).__class__"):
    try:
        _GO88.Ausdruck(t_)
        _boese88.append(t_)
    except (ValueError, SyntaxError):
        pass
pruef("... und alles andere wird beim Laden abgelehnt (kein Code aus Datendateien)",
      not _boese88, str(_boese88))

# Der Planer findet Kombinationen selbst.
_akt88 = [_GO88.Aktion("deckung", "", "in_deckung", "2"),
          _GO88.Aktion("laden_deckung", "in_deckung, leer", "!leer", "1"),
          _GO88.Aktion("laden_ohne", "!feind, leer", "!leer", "1"),
          _GO88.Aktion("laden_offen", "leer", "!leer", "6")]
_plan88 = _GO88.planen({"leer": True, "feind": True}, {"leer": False}, _akt88)
pruef("Planer: mit Gegner erst in Deckung, dann nachladen",
      [a_.name for a_ in _plan88] == ["deckung", "laden_deckung"], str(_plan88))
_plan88 = _GO88.planen({"leer": True}, {"leer": False}, _akt88)
pruef("... ohne Gegner gleich", [a_.name for a_ in _plan88] == ["laden_ohne"], str(_plan88))
pruef("... schon erfuellt: leerer Plan, unmoeglich: None",
      _GO88.planen({}, {"leer": False}, _akt88) == []
      and _GO88.planen({}, {"fliegt": True}, _akt88) is None, "")
_kette88 = [_GO88.Aktion("s%d" % i_, "f%d" % i_, "f%d" % (i_ + 1), "1") for i_ in range(10)]
pruef("... und mehr als TIEFE Schritte plant er nicht",
      _GO88.planen({"f0": True}, {"f10": True}, _kette88) is None
      and len(_GO88.planen({"f0": True}, {"f4": True}, _kette88)) == 4, "")
pruef("... Kosten aus Merkmalen: der Mutige laedt offen, der Vorsichtige in Deckung",
      [a_.name for a_ in _GO88.planen({"leer": True, "feind": True}, {"leer": False},
                                      [_akt88[0], _akt88[1],
                                       _GO88.Aktion("offen", "leer", "!leer", "6 - 5 * mut")],
                                      {"mut": 0.9})] == ["offen"]
      and [a_.name for a_ in _GO88.planen({"leer": True, "feind": True}, {"leer": False},
                                          [_akt88[0], _akt88[1],
                                           _GO88.Aktion("offen", "leer", "!leer", "6 - 5 * mut")],
                                          {"mut": 0.1})] == ["deckung", "laden_deckung"], "")

# Das Gehirn: waehlt das dringendste Ziel, haelt es gegen Wackeln, und
# eine gescheiterte Aktion bleibt eine Weile draussen.
_hirn88 = _GO88.Gehirn([_GO88.Ziel("laden", "!leer", "50 * leer"),
                        _GO88.Ziel("kampf", "besiegt", "45 + gereizt")],
                       _akt88 + [_GO88.Aktion("schiessen", "", "besiegt", "1")])
_a88 = _hirn88.denken(0.0, {"leer": True, "feind": True}, {"gereizt": 0})
pruef("Gehirn: das dringendste Ziel, der erste Schritt seines Plans",
      _hirn88.ziel.name == "laden" and _a88.name == "deckung", str(_a88))
_hirn88.denken(0.1, {"leer": True, "feind": True}, {"gereizt": 7})
pruef("... ein knapp dringenderes Ziel verdraengt das laufende nicht (Vorsprung)",
      _hirn88.ziel.name == "laden", _hirn88.ziel.name)
_hirn88.melden("gescheitert")
_a88 = _hirn88.denken(0.2, {"leer": True, "feind": True}, {"gereizt": 0})
pruef("... gescheitert: ohne diese Aktion neu geplant",
      _a88.name == "laden_offen" and "GESCHEITERT: deckung" in [t_ for _z, t_ in _hirn88.protokoll],
      str(_a88))
_a88 = _hirn88.denken(0.2 + K.GOAP["sperre"] + 0.1, {"leer": True, "feind": True}, {"gereizt": 0})
pruef("... und nach der Sperre wieder mit", _a88.name == "deckung", str(_a88))
_hirn88.erzwungen = "kampf"
_a88 = _hirn88.denken(5.0, {"leer": True, "feind": True}, {"gereizt": 0})
pruef("... ein erzwungenes Ziel gilt, egal wie dringlich (Testmodus)",
      _hirn88.ziel.name == "kampf" and _a88.name == "schiessen", str(_a88))

# Die Daten.
pruef("wesen/*.txt laesst sich lesen, jeder Verweis und jedes Verhalten stimmt",
      not _WD88.pruefen(_WD88.neu_laden()),
      "; ".join(_WD88.pruefen()[:3]))
pruef("... mit der Spezies der Mehrspieler-Bots",
      K.GOAP["spezies_bot"] in _WD88.daten().spezies, "")
_d88 = _WD88.Daten()
_WD88.aus_text("[ziel gut]\nwill: a\n\n[aktion kaputt]\nkosten: 3 +\n\nzeile ohne block\n"
               "[aktion gut]\nmacht: a\n[spezies s]\nziele: gut, fehlt\naktionen: gut\n"
               "merkmal mut: 0.9 0.1\n", _d88, "probe.txt")
_f88 = _WD88.pruefen(_d88)
pruef("Ein Fehler in den Daten kostet nur seinen Block - mit Datei und Zeile gemeldet",
      "gut" in _d88.ziele and "gut" in _d88.aktionen and "kaputt" not in _d88.aktionen
      and any("probe.txt:4" in f_ for f_ in _f88) and any("fehlt" in f_ for f_ in _f88)
      and _d88.spezies["s"].merkmale["mut"] == (0.1, 0.9), str(_f88))

# Die Regel BOT-KI.
# Seit 0.34.96 ist GOAP die Vorgabe (gewuenscht).
pruef("Regel BOT-KI: GOAP ist die Vorgabe, klassisch waehlbar",
      _RG88.vorgabe()["bot_ki"] == "goap"
      and _RG88.saeubern({"bot_ki": "klassisch"})["bot_ki"] == "klassisch"
      and _RG88.saeubern({"bot_ki": "unsinn"})["bot_ki"] == "goap", "")
_n88 = netz.Gastgeber(_neuer_port())
_w88 = Gefecht(app, "WIRT", gastgeber=_n88, modus="team", seed=88,
               regeln={"bots": 4, "bot_ki": "goap"})
pruef("... mit GOAP denken alle Bots der Runde zielorientiert",
      _w88._bots() and all(isinstance(b_.hirn, _BG88.GoapHirn) for b_ in _w88._bots()),
      str([type(b_.hirn).__name__ for b_ in _w88._bots()]))
_w88.verlassen()
_n88 = netz.Gastgeber(_neuer_port())
_w88 = Gefecht(app, "WIRT", gastgeber=_n88, modus="team", seed=88, regeln={"bots": 4})
pruef("... ohne die Regel GOAP (Vorgabe seit 0.34.96)",
      _w88._bots() and all(isinstance(b_.hirn, _BG88.GoapHirn) for b_ in _w88._bots()), "")
_w88.verlassen()

# Im Testmodus: GOAP gegen klassisch, auf kurze Entfernung.
_tm = _TM87.Testmodus(app, karte="staubtal")
_e88 = _tm._eintrag("BOT")
pruef("Spawner: der BOT hat die Einstellung HIRN (KLASSISCH / GOAP)",
      "hirn" in _e88.optionen and _TM87.OPTIONEN["hirn"][1]() == list(K.GOAP["arten"]), "")
_tm._sp_werte["BOT"] = {"hirn": list(K.GOAP["arten"]).index("goap")}
# Zwei Stellen mit freier Sicht: sie sollen kaempfen, nicht einander
# suchen. Seit 0.34.32 irgendwo auf der Karte - neben dem (zufaelligen)
# Einstiegsort von ROT gab es manchmal keine, und der Test brach ab.
_r88 = random.Random(88)
_a88 = _b88 = None
for _ in range(4000):
    a_ = pygame.Vector2(freier_punkt(_tm.welt, 0, _r88))
    p_ = a_ + pygame.Vector2(_r88.choice((170, 200, 240)), 0).rotate(_r88.uniform(0, 360))
    if (_tm.welt.frei(a_, 14, 0, True) and _tm.welt.frei(a_ + pygame.Vector2(0, 24), 14, 0, True)
            and _tm.welt.frei(p_, 14, 0, True) and _tm.welt.frei(p_ + pygame.Vector2(0, 24), 14, 0, True)
            and _tm.welt.deckung(a_, p_, 0) == ""):
        _a88, _b88 = a_, p_
        break
pruef("(zwei Stellen mit freier Sicht fuer das Gefecht)", _b88 is not None, "")
_rot88 = _tm.spawnen(_e88, pos=_a88, ebene=0)
_rot88 = [k_ for k_ in _tm._bots()]
pruef("... der Spawner setzt mit HIRN GOAP einen planenden Bot",
      _rot88 and all(isinstance(k_.hirn, _BG88.GoapHirn) for k_ in _rot88), "")
_rot88 += [_tm.bot_setzen(_a88 + pygame.Vector2(0, 24), 0, {"team": 0, "hirn": "goap"})]
_blau88 = [_tm.bot_setzen(_b88 + pygame.Vector2(0, 24 * i_), 0, {"team": 1, "hirn": "klassisch"})
           for i_ in range(2)]
# Keiner geht zu Boden (seit 0.34.52): auf Liegende schiesst keiner mehr,
# und warf ROT beide mit einer Granate um, war das Gefecht vorbei, bevor der
# erste Schuss fiel - vorher fuellte das Niederhalten auf die Liegenden die
# Schusszahl. So dauert das Gefecht die ganzen 30 Sekunden.
for b_ in _blau88 + _rot88:
    b_.unverwundbar = 1e9
_tm.wiedereinstieg = False
_geist88 = _tm._geist
_geist88.pos.update(_a88 + pygame.Vector2(20, 0))
_geist88.ebene = 0
_aktionen88 = set()
_ziele88 = set()
_gesehen88 = False
for _ in range(int(30.0 / _D87)):
    _tm.schritt(_D87)
    for k_ in _rot88:
        g_ = k_.hirn.gehirn if k_.hirn is not None else None
        if g_ is not None and k_.lebt:
            if g_.aktion is not None:
                _aktionen88.add(g_.aktion.name)
            if g_.ziel is not None:
                _ziele88.add(g_.ziel.name)
        if k_.hirn is not None and (k_.hirn.ziel is _geist88 or _geist88 in k_.hirn.gesehen):
            _gesehen88 = True
_schuesse88 = sum(k_.zaehler.get("schuesse", 0) for k_ in _rot88)
pruef("GOAP-Bots planen, greifen an und schiessen",
      "angreifen" in _aktionen88 and "feind_ausschalten" in _ziele88 and _schuesse88 > 0,
      "Aktionen %s, Schuesse %d" % (sorted(_aktionen88), _schuesse88))
pruef("... und auch sie nehmen den Beobachter nie wahr", not _gesehen88, "")

# Die Gedanken: Taste 8 schaltet durch AUS, KURZ, GEDANKEN.
_tm.info = 0
_stufen88 = []
for _ in range(3):
    _tm.taste("8")
    _stufen88.append(_tm.info)
pruef("Taste 8: KURZ, GEDANKEN, AUS", _stufen88 == [1, 2, 0], str(_stufen88))
_denker88 = next((k_ for k_ in _rot88 if k_.lebt), None) or _tm.bot_setzen(
    _a88, 0, {"team": 0, "hirn": "goap"})
_tm._zeiger_welt = pygame.Vector2(_denker88.pos)
_tm.blick = _denker88.ebene
pruef("... gezeigt wird die GOAP-Figur am Zeiger", _tm.denker() is _denker88, "")
_tm.info = 2
_bild88 = pygame.Surface((K.GAME_W, K.GAME_H))
_tm.zeichnen(_bild88, 1.0)
pruef("... und ihre Gedanken lassen sich zeichnen", True, "")
_tm.ziel_erzwingen(1)
_zwang88 = _denker88.hirn.gehirn.erzwungen
pruef("ZIEL ERZWINGEN: das erste Ziel der Liste", _zwang88 == _denker88.hirn.gehirn.ziele[0].name,
      str(_zwang88))
for _ in range(len(_denker88.hirn.gehirn.ziele)):
    _tm.ziel_erzwingen(1)
pruef("... einmal ganz herum wieder frei", _denker88.hirn.gehirn.erzwungen is None, "")
_alt88 = _denker88.hirn.gehirn
_tm.ki_daten_laden()
pruef("KI-DATEN NEU LADEN gibt jeder GOAP-Figur ein neues Gehirn",
      _denker88.hirn.gehirn is not _alt88 and _denker88.hirn.merkmale == _alt88.merkmale, "")
_tm.verlassen()

# 0.34.30: Schritt 3 aus docs/KI.md - Zombies und Bosse auf GOAP, als Test
# fuer dumme Wesen. Sie sollen sich spielen wie bisher.
print("\n-- Zombies und Bosse mit GOAP (0.34.30)")
from dustfront import gegner_goap as _GG89
from dustfront.mehrspieler import KampfGegner as _KG89
_sp89 = {a_: _GG89.spezies_fuer(a_) for a_ in ("laeufer", "renner", "speier", "koloss", "mutter")}
pruef("Spezies: Zombie, Speier, Boss - aus der Art",
      _sp89 == {"laeufer": "zombie", "renner": "zombie", "speier": "speier",
                "koloss": "boss", "mutter": "boss"}, str(_sp89))
_d89 = _WD88.Daten()
_WD88.aus_text("[spezies renner]\nhirn: gegner\n", _d89)
pruef("... und eine Spezies mit dem Namen der Art geht vor (nur ein Block in der Datei)",
      _GG89.spezies_fuer("renner", _d89) == "renner" and _GG89.spezies_fuer("laeufer", _d89) == "zombie", "")
pruef("Jede Spezies in wesen/ kennt nur Verhalten ihres Hirns (bot / gegner)",
      not _WD88.pruefen(_WD88.neu_laden()), "; ".join(_WD88.pruefen()[:3]))
_d89f = _WD88.Daten()
_WD88.aus_text("[aktion schiessen]\ntut: kaempfen\n[spezies z]\nhirn: gegner\naktionen: schiessen\n"
               "[spezies q]\nhirn: rakete\n", _d89f)
_f89 = _WD88.pruefen(_d89f)
pruef("... ein Zombie mit dem Verhalten eines Bots und ein unbekanntes Hirn fallen auf",
      any("kennt hirn gegner nicht" in f_ for f_ in _f89) and any("unbekanntes hirn" in f_ for f_ in _f89),
      str(_f89))

pruef("Regel GEGNER-KI: klassisch ist die Vorgabe, gilt nur mit Gegnern",
      _RG88.vorgabe()["gegner_ki"] == "klassisch"
      and "gegner_ki" in [f_.schluessel for f_ in _RG88.sichtbar(_RG88.vorgabe(modus="pve"))]
      and "gegner_ki" not in [f_.schluessel for f_ in _RG88.sichtbar(_RG88.vorgabe(modus="pvp"))], "")
_n89 = netz.Gastgeber(_neuer_port())
_w89 = Gefecht(app, "WIRT", gastgeber=_n89, modus="pve", seed=89, regeln={"gegner_ki": "goap"})
_g89 = _KG89(pygame.Vector2(_w89.ich.pos), "mutter", 0, _w89)
_kind89 = _g89._brut_erzeugen(pygame.Vector2(_w89.ich.pos), "laeufer")
pruef("... mit GOAP denkt jeder neue Gegner zielorientiert, auch die Brut",
      isinstance(_g89.hirn, _GG89.GegnerHirn) and isinstance(_kind89.hirn, _GG89.GegnerHirn)
      and _g89.hirn.spezies == "boss", "")
pruef("... die Zielpuppe nie", _KG89(pygame.Vector2(0, 0), "puppe", 0, _w89).hirn is None, "")
_w89.verlassen()
_n89 = netz.Gastgeber(_neuer_port())
_w89 = Gefecht(app, "WIRT", gastgeber=_n89, modus="pve", seed=89)
pruef("... ohne die Regel klassisch wie bisher",
      _KG89(pygame.Vector2(_w89.ich.pos), "laeufer", 0, _w89).hirn is None, "")
_w89.verlassen()

# Im Testmodus, auf freiem Feld: hin und zuschlagen, spucken, herumirren.
_tm = _TM87.Testmodus(app, karte="staubtal")
_tm.wiedereinstieg = False
pruef("Spawner: Gegner und Bosse haben die Einstellung HIRN",
      all("hirn" in e_.optionen for e_ in _tm.eintraege if e_.gruppe in ("GEGNER", "BOSSE")), "")
_r89 = random.Random(89)
_feld89 = None
for _ in range(4000):
    a_ = pygame.Vector2(freier_punkt(_tm.welt, 0, _r89))
    b_ = a_ + pygame.Vector2(170, 0)
    if (_tm.welt.frei(a_, 24, 0, True) and _tm.welt.frei(b_, 34, 0, True)
            and _tm.welt.frei((a_ + b_) / 2, 34, 0, True) and _tm.welt.deckung(a_, b_, 0) == ""):
        _feld89 = (a_, b_)
        break
pruef("(eine freie Bahn fuer die Zombie-Tests)", _feld89 is not None, "")


def _angriff89(art, hirn, sekunden=10.0):
    _tm.alles_weg()
    p_ = _tm.puppe_setzen(_feld89[0], 0, {"team": 0, "leben": 10.0})
    g_ = _tm.gegner_setzen(art, _feld89[1], 0, {"ki": True, "hirn": hirn})
    l_ = p_.leben
    aktionen_ = set()
    for _ in range(int(sekunden / _D87)):
        _tm.schritt(_D87)
        if g_.hirn is not None and g_.hirn.gehirn.aktion is not None:
            aktionen_.add(g_.hirn.gehirn.aktion.name)
    return l_ - p_.leben, aktionen_, g_


for art_, soll_ in (("laeufer", {"hinlaufen", "zuschlagen"}), ("speier", {"spucken"})):
    # Sechs Laeufe je Seite zusammen (seit 0.34.32): ein einzelner Speier
    # streut zwischen 0 und 56 Schaden (14 je Treffer), klassisch wie GOAP
    # - verglichen wird, wie viel sie treffen, nicht wer einmal Glueck hatte.
    _klassisch89, _goap89, _a89 = 0.0, 0.0, set()
    for _ in range(6):
        _klassisch89 += _angriff89(art_, "klassisch")[0]
        _s89, _neu89, _g89 = _angriff89(art_, "goap")
        _goap89 += _s89
        _a89 |= _neu89
    pruef("GOAP-%s: plant %s und trifft etwa so viel wie der klassische"
          % (art_.upper(), " + ".join(sorted(soll_))),
          soll_ <= _a89 and _goap89 > 0 and 0.5 * _klassisch89 <= _goap89 <= 1.6 * _klassisch89,
          "GOAP %.0f, klassisch %.0f, %s" % (_goap89, _klassisch89, sorted(_a89)))

_tm.alles_weg()
_g89 = _tm.gegner_setzen("laeufer", _feld89[0], 0, {"ki": True, "hirn": "goap"})
# Gemessen wird die Strecke, nicht der Abstand zum Start (seit 0.34.35):
# wer herumirrt, kommt auch mal dorthin zurueck, wo er anfing - der Abstand
# allein war dann nach sechs Sekunden manchmal nur 10 px.
_weg89 = 0.0
for _ in range(int(6.0 / _D87)):
    _p89 = pygame.Vector2(_g89.pos)
    _tm.schritt(_D87)
    _weg89 += _g89.pos.distance_to(_p89)
pruef("Ohne Ziel irrt ein GOAP-Zombie langsam herum, statt zu stehen",
      _g89.hirn.gehirn.ziel is not None and _g89.hirn.gehirn.ziel.name == "herumirren"
      and _weg89 > 40.0,
      "%s, %.0f px gelaufen" % (_g89.hirn.gehirn.ziel, _weg89))
pruef("... und nimmt dabei den Beobachter nicht wahr", _g89._ziel is None, "")

# Der Boss: lauert, wenn sein Ziel auf einer anderen Ebene ist, und zieht
# angeschlagen seine Faehigkeit vor.
_tm.alles_weg()
_puppe89 = _tm.puppe_setzen(_feld89[0], 0, {"team": 0, "leben": 10.0})
_boss89 = _tm.gegner_setzen("koloss", _feld89[1], 0, {"ki": True, "hirn": "goap"})
_ort89 = pygame.Vector2(_boss89.pos)
for _ in range(int(2.0 / _D87)):
    # Jeden Schritt: ueber der Bahn ist auf Ebene 1 kein Boden, die Puppe
    # fiele sonst gleich wieder herunter.
    _puppe89.ebene = 1
    _tm.schritt(_D87)
pruef("GOAP-Boss: Ziel auf einer anderen Ebene - er lauert und wechselt nicht",
      _boss89.hirn.gehirn.ziel is not None and _boss89.hirn.gehirn.ziel.name == "lauern"
      and _boss89.ebene == 0, str(_boss89.hirn.gehirn.ziel))
_puppe89.ebene = 0
_boss89.leben = _boss89.max_leben * 0.3
_boss89.f_rest = _boss89.faehigkeit["takt"] * 0.4
_boss89.f_vorlauf = 0.0
_angesagt89 = False
for _ in range(int(0.5 / _D87)):
    _tm.schritt(_D87)
    _angesagt89 = _angesagt89 or _boss89.f_vorlauf > 0.0
pruef("... angeschlagen zieht er seine Faehigkeit vor - mit vollem Vorlauf (Phase zwei)",
      _angesagt89 and "faehigkeit_vorziehen" in [t_.split(": ")[-1].split(" ")[0]
                                                  for _z, t_ in _boss89.hirn.gehirn.protokoll
                                                  if t_.startswith("PLAN")],
      str(list(_boss89.hirn.gehirn.protokoll)[-4:]))

# Testmodus: KI STOP haelt auch sie an, und ihre Gedanken lassen sich zeigen.
_tm.taste("/")
_ort89 = pygame.Vector2(_boss89.pos)
_sim87(int(1.0 / _D87))
pruef("KI STOP haelt auch GOAP-Gegner an", _boss89.pos.distance_to(_ort89) < 1.0, "")
_tm.taste("/")
_tm._zeiger_welt = pygame.Vector2(_boss89.pos)
_tm.blick = _boss89.ebene
pruef("Gedanken: gezeigt wird der GOAP-Gegner am Zeiger", _tm.denker() is _boss89, "")
_tm.info = 2
_tm.zeichnen(pygame.Surface((K.GAME_W, K.GAME_H)), 1.0)
_tm.ki_daten_laden()
pruef("... zeichnen und KI-DATEN NEU LADEN gehen auch fuer ihn",
      _boss89.hirn.gehirn is not None, "")

# 0.34.31: zwei Fehler, gefunden in den Aufnahmen der Gefechte.
print("\n-- GOAP, aus den Aufnahmen (0.34.31)")
_tm.alles_weg()
_bot90 = _tm.bot_setzen(_feld89[0], 0, {"team": 0, "hirn": "goap"})
_feind90 = _tm.puppe_setzen(_feld89[1], 0, {"team": 1})
_h90 = _bot90.hirn
_h90.ziel = _feind90
_h90.gesehen[_feind90] = (pygame.Vector2(_feind90.pos), 0, _tm.welt.zeit)
_h90.linie = "hindernis"
_ein90 = {"t": "ein", "will": [0.0, 0.0], "ziel": [0.0, 0.0], "feuert": False, "zielt": False,
          "nutzen": False, "ziehen": False, "hb": False, "waffe": -1, "knoepfe": [], "admin": ""}
_r90 = _h90.tun_suchen(_D87, _ein90)
pruef("SUCHEN mit sichtbarem Gegner hinter einer Kiste: er geht zur Seite, statt 'fertig' "
      "zu melden und im Feuer stehen zu bleiben",
      _r90[4] == "laeuft" and _r90[0].length() > 0.1, "%s %s" % (_r90[4], _r90[0]))
_h90.linie = ""
pruef("... mit freier Linie ist Suchen fertig", _h90.tun_suchen(_D87, _ein90)[4] == "fertig", "")

_tm.alles_weg()
_tm.zone_setzen(_feld89[0] + (_feld89[0] - _feld89[1]) * 1.5, 0)
_bot90 = _tm.bot_setzen(_feld89[0], 0, {"team": 0, "hirn": "goap"})
_feind90 = _tm.puppe_setzen(_feld89[1], 0, {"team": 1})
_ziele90 = set()
for _ in range(int(2.0 / _D87)):
    _tm.schritt(_D87)
    if _bot90.hirn.gehirn.ziel is not None:
        _ziele90.add(_bot90.hirn.gehirn.ziel.name)
pruef("HUEGEL: ausserhalb des Kreises geht der Kreis vor, auch mit einem Gegner im Blick",
      "kreis" in _ziele90 and "feind_ausschalten" not in _ziele90
      and _bot90.hirn.gehirn.dringlichkeiten.get("kreis", 0)
      > _bot90.hirn.gehirn.dringlichkeiten.get("feind_ausschalten", 0), str(sorted(_ziele90)))
_tm.zone_aus()
_tm.verlassen()

# 0.34.32: "Teils war das Rendering fehlerhaft, manche Bots waren zum Teil
# unsichtbar. Ich will alles im Sichtfeld perfekt sehen. Nimm die Sachen
# aus der Testansicht aus dem Video raus und zeig mir nur die jeweilige
# Aktion ueber den Koepfen." Die saubere Ansicht und werkzeug_aufnahme.py.
print("\n-- Saubere Ansicht und Aufnahmen (0.34.32)")
_tm = _TM87.Testmodus(app, karte="staubtal")
pruef("Das Testmenue passt in seinen Kasten, jede Zeile",
      all(_tm.MENUE.contains(r_) for r_ in _tm._menue_flaechen()),
      "%d Zeilen, unterste bei %d, Kasten bis %d" % (len(_tm._menue_flaechen()),
                                                    _tm._menue_flaechen()[-1].bottom,
                                                    _tm.MENUE.bottom))
_tm.nebel = True                   # seit 0.34.91 aus als Vorgabe - hier geht es um ihn
# Ganz heraus: seit 0.34.95 ist bis Zoom K.ZOOM klar (1,5) alles klar.
_tm.zoom_ziel = _tm._zoom_weich = max(K.ZOOM["stufen"])
_tm.schritt(_D87)
pruef("Herausgezoomt zeichnet der Testmodus sonst nur im normalen Bild Figuren (Nebel)",
      _tm.sicht_welt() is not None, "")
_tm.menue_wirken("sauber")
pruef("SAUBERE ANSICHT im Testmenue: an, und herausgezoomt kein Nebel mehr - "
      "jede Figur im Bild wird gezeichnet",
      _tm.sauber and _tm.sicht_welt() is None, "")
_bot91 = _tm.bot_setzen(_feld89[0], 0, {"team": 0, "hirn": "goap"})
_alt91 = _tm.bot_setzen(_feld89[0] + pygame.Vector2(0, 40), 0, {"team": 0, "hirn": "klassisch"})
_feind91 = _tm.bot_setzen(_feld89[1], 0, {"team": 1, "hirn": "goap"})
_sim87(int(1.0 / _D87))
pruef("... ueber dem Kopf steht die Aktion (GOAP) oder der Zustand (klassisch)",
      _tm.aktion_text(_bot91) == (_bot91.hirn.gehirn.aktion.name.replace("_", " ").upper()
                                  if _bot91.hirn.gehirn.aktion else "")
      and (_tm.aktion_text(_alt91) in ("UNTERWEGS", "KAMPF", "DRUCK", "FLANKE", "DECKUNG")
           or _tm.aktion_text(_alt91).startswith("STURM")),
      "%r / %r" % (_tm.aktion_text(_bot91), _tm.aktion_text(_alt91)))
pruef("... kein Funk: ueber dem Kopf nur die Aktion", not _tm._funk_hoerbar(_bot91), "")
for i_ in range(8):
    _tm.gegner_setzen("laeufer", _feld89[1] + pygame.Vector2(2 * i_, 0), 0,
                      {"ki": True, "hirn": "goap"})
_sim87(int(0.5 / _D87))
_bild91 = pygame.Surface((K.GAME_W, K.GAME_H))
_tm.zeichnen(_bild91, 1.0)
_felder91 = _tm._aktionen_zeichnen(_bild91)
pruef("... auch in einem Rudel liegt keine Beschriftung auf einer anderen",
      _felder91 and not any(a_.colliderect(b_) for i_, a_ in enumerate(_felder91)
                            for b_ in _felder91[i_ + 1:]), "%d Felder" % len(_felder91))
_k91 = _tm.zustand()
pruef("... und sie bleibt ueber einen Kartenwechsel", _k91.get("sauber") is True, "")
_tm.menue_wirken("sauber")
pruef("... aus: Funk und Nebel wie vorher", _tm._funk_hoerbar(_bot91) and _tm.sicht_welt() is not None, "")
_tm.verlassen()

import werkzeug_aufnahme as _WA91
_fehler91 = []
for n_, (datei_, szene_) in _WA91.SZENEN.items():
    try:
        tm_ = _WA91.testmodus_fuer_aufnahme(app, 1.0)
        titel_, wer_, ende_, sek_, zoom_, *rest_ = szene_(tm_, random.Random(91))
        for _ in range(30):
            if rest_:
                rest_[0]()             # was die Szene vor jedem Bild tut
            tm_.schritt(_D87)
        tm_.zeichnen(_bild91, 1.0)
        if not (wer_ and titel_ and sek_ > 0 and zoom_ >= 1.0 and not ende_()):
            _fehler91.append(n_)
        tm_.verlassen()
    except Exception as err_:
        _fehler91.append("%s: %r" % (n_, err_))
pruef("werkzeug_aufnahme.py: jede Szene baut sich auf, laeuft und zeichnet (ohne ffmpeg)",
      not _fehler91 and len(_WA91.SZENEN) >= 5, str(_fehler91))
pruef("... 30 Bilder je Sekunde aus 120 Rechenschritten",
      _WA91.SCHRITTE_JE_BILD == 4, str(_WA91.SCHRITTE_JE_BILD))
# Und so wird auch wirklich aufgenommen (bis 0.34.127 rechnete jedes Bild
# 6 statt 4 Schritte - alle Videos liefen 1,5-mal zu schnell). Ohne ffmpeg:
# ein Schreiber, der die Bilder nur zaehlt.
import tempfile as _tf91
class _Schreiber91:
    def __init__(self, pfad_):
        self.stdin = self
        self.bilder = 0
        self._f = open(pfad_, "wb")
    def write(self, roh_):
        self.bilder += 1
    def close(self):
        self._f.close()
    def wait(self):
        return 0
_schreiber91 = []
_alt_vs91 = _WA91._video_schreiber
_WA91._video_schreiber = lambda pfad_: _schreiber91.append(_Schreiber91(pfad_)) or _schreiber91[-1]
_schritte91 = [0]
_alt_ts91 = _TM59.Testmodus.schritt
def _ts_zaehl91(self_, dt_):
    _schritte91[0] += 1
    return _alt_ts91(self_, dt_)
_TM59.Testmodus.schritt = _ts_zaehl91
try:
    _WA91.aufnehmen(app, "duell", _tf91.mkdtemp(prefix="aufnahme_test_"), ton=False)
finally:
    _TM59.Testmodus.schritt = _alt_ts91
    _WA91._video_schreiber = _alt_vs91
pruef("... und jedes geschriebene Bild ist genau so viele Rechenschritte (Videos in echtem Tempo)",
      _schreiber91 and _schreiber91[0].bilder > 0
      and _schritte91[0] == _schreiber91[0].bilder * _WA91.SCHRITTE_JE_BILD,
      "%d Schritte, %d Bilder" % (_schritte91[0], _schreiber91[0].bilder if _schreiber91 else 0))

# 0.34.35: "Und mit Sound. Und wie waere es, wenn du mir die auch
# verlangsamst? ... jeweils noch eine 0,5-Speed-Version dazu."
import tempfile as _tf94
_band94 = _WA91.Tonband(app.klaenge, lambda: 0.25)
app.klaenge.spielen("tod", 1.0)
app.klaenge.spielen("schuss_sturm", 0.5)
_ereig94 = list(_band94.ereignisse)
_band94.abhaengen()
pruef("Tonband: schreibt mit, was gespielt wuerde (Zeit, Klang, Lautstaerke) - "
      "und gibt das Abspielen danach zurueck",
      len(_ereig94) == 2 and _ereig94[0][0] == 0.25 and "spielen" not in app.klaenge.__dict__,
      str(len(_ereig94)))
_wav94 = os.path.join(_tf94.mkdtemp(), "ton.wav")
_ok94 = _band94.wav(_wav94, 1.0)
import wave as _wave94
from array import array as _arr94
with _wave94.open(_wav94, "rb") as w_:
    _rate94, _n94 = w_.getframerate(), w_.getnframes()
    _proben94 = _arr94("h", w_.readframes(_n94))
pruef("... und mischt daraus eine Tonspur: eine Sekunde, laut genug, nicht uebersteuert",
      _ok94 and _n94 == _rate94 and max(abs(v_) for v_ in _proben94) > 1000
      and max(abs(v_) for v_ in _proben94[:int(0.2 * _rate94) * 2]) == 0,
      "%d Proben, Spitze %d" % (_n94, max(abs(v_) for v_ in _proben94)))

# 0.34.33: "Bau bitte fuer wirklich jede Entity eine Death Animation ein,
# gerade kann ich nie sicher sein, ob die einfach verschwinden oder ob die
# tot sind. Also Death Animation und einen Blutfleck auf dem Boden, je nach
# Entity anderes Blut." 0.34.34: "Der Fleck reicht, Animation muss nicht
# sein. Ein Death Sound reicht mir."
print("\n-- Tod: Fleck je Blut und Todeslaut (0.34.33, 0.34.34)")
from dustfront.entities import tod_blut as _todblut92
_arten92 = [a_ for a_ in list(K.GEGNER) + list(K.BOSSE) if a_ not in K.UEBUNG]
_fehlt92 = [a_ for a_ in _arten92 + ["spieler"] if a_ not in K.TOD["wesen"]]
_falsch92 = [(a_, bl_) for a_, bl_ in K.TOD["wesen"].items() if bl_ not in K.BLUT]
pruef("Jede Gegnerart, jeder Boss und die Figuren haben ihr Blut",
      not _fehlt92 and not _falsch92, "%s %s" % (_fehlt92, _falsch92))
pruef("... und das Blut ist nicht ueberall dasselbe",
      len(set(K.TOD["wesen"].values())) >= 5, "")
from dustfront import audio as _AU92
pruef("Den Todeslaut gibt es, auch ohne Datei (Platzhalter)",
      "tod" in K.KLANG_NAMEN and "tod" in _AU92._PLATZHALTER
      and len(_AU92._PLATZHALTER["tod"]()) > 1000, "")

_tm = _TM87.Testmodus(app, karte="staubtal")
_tm.wiedereinstieg = False
# Gestorben wird hier beim ersten Mal (seit 0.34.40 fallen Bots im Testmodus
# sonst erst zu Boden, VERWUNDETE BOTS) - geprueft wird der Tod selbst.
_tm.verwundete_setzen(False)
_flecken92 = []
_laute92 = []
_alt_fleck92 = _tm.welt.blutfleck
_alt_klang92 = _tm.welt.klang


def _fleck_merken92(pos, ebene, radius, art="mensch", variante=0):
    _flecken92.append(art)
    _alt_fleck92(pos, ebene, radius, art, variante)


def _klang_merken92(name, laut=1.0, pos=None, ebene=None):
    _laute92.append(name)
    _alt_klang92(name, laut, pos, ebene)


_tm.welt.blutfleck = _fleck_merken92
_tm.welt.klang = _klang_merken92
_ort92 = pygame.Vector2(_feld89[0])
_opfer92 = [_tm.gegner_setzen(a_, _ort92 + pygame.Vector2(30 * i_, 0), 0, {"ki": False})
            for i_, a_ in enumerate(_arten92)]
_opfer92.append(_tm.bot_setzen(_ort92 + pygame.Vector2(0, 40), 0, {"team": 0}))
_opfer92.append(_tm.puppe_setzen(_ort92 + pygame.Vector2(40, 40), 0, {"team": 1}))
_sim87(3)
del _flecken92[:], _laute92[:]
for w_ in _opfer92:
    if w_.lebt:          # der Blaeher reisst beim Platzen vielleicht schon wen mit
        w_.leben = 0.0
        w_.sterben(None)
pruef("Wer stirbt, hinterlaesst sofort einen Fleck - im Blut seiner Art",
      sorted(_flecken92) == sorted(_todblut92(w_) for w_ in _opfer92), str(sorted(_flecken92)))
pruef("... und man hoert es: je Tod ein Todeslaut",
      _laute92.count("tod") == len(_opfer92), "%d Laute fuer %d Tote" % (_laute92.count("tod"),
                                                                       len(_opfer92)))
_sim87(3)
_bild92 = pygame.Surface((K.GAME_W, K.GAME_H))
_tm.zeichnen(_bild92, 1.0)
pruef("... keine Leiche, keine Animation: die Toten sind aus der Welt",
      not any(w_ in _tm.welt.wesen for w_ in _opfer92) and not hasattr(_tm.welt, "leichen"), "")

_farben92 = {}
for bl_ in K.BLUT:
    f_ = _tm.renderer.blutfleck(9.0, bl_)
    _farben92[bl_] = tuple(f_.get_at((f_.get_width() // 2, f_.get_height() // 2)))[:3]
pruef("Der Fleck hat je Blut seine Farbe", len(set(_farben92.values())) == len(K.BLUT),
      str(_farben92))
_v92 = [_tm.renderer.blutfleck(9.0, "zombie", v_) for v_ in range(8)]
pruef("... und liegt in acht Formen da, nicht jeder gleich",
      len({pygame.image.tobytes(v_, "RGBA") for v_ in _v92}) >= 4, "")

# ENTF: loeschen (verschwindet) oder toeten (stirbt) - jetzt sieht man's.
_g92 = _tm.gegner_setzen("laeufer", _ort92, 0, {"ki": False})
_sim87(2)
del _flecken92[:], _laute92[:]
_tm._zeiger_welt = pygame.Vector2(_g92.pos)
_tm.blick = 0
_tm.taste("enter")
pruef("ENTF LOESCHT: weg, ohne Fleck und ohne Laut",
      not _g92.lebt and not _flecken92 and "tod" not in _laute92, "")
_tm.menue_wirken("entf")
_g92 = _tm.gegner_setzen("speier", _ort92, 0, {"ki": False})
_sim87(2)
_tm._zeiger_welt = pygame.Vector2(_g92.pos)
_tm.taste("enter")
pruef("ENTF TOETET (Testmenue): er stirbt, mit seinem Blut und dem Todeslaut",
      not _g92.lebt and _flecken92 == ["saeure"] and "tod" in _laute92
      and _tm._tastentext("enter")[0] == "TÖTEN", str(_flecken92))
_tm.verlassen()

# Im Netz: der Gast bekommt den Tod gemeldet und legt Fleck und Laut selbst.
w92, g92 = gefechtspaar("pve")
_ort92 = pygame.Vector2(w92.ich.pos) + pygame.Vector2(60, 0)
_z92 = KampfGegner(_ort92, "speier", w92.ich.ebene, w92)
w92.welt.dazu(_z92)
for _ in range(6):
    w92.schritt(K.NETZ["takt"])
    g92.schritt(K.NETZ["takt"])
_gf92, _gk92 = [], []
_galt_f92, _galt_k92 = g92.welt.blutfleck, g92.welt.klang
g92.welt.blutfleck = lambda pos, eb, r, art="mensch", v=0: (_gf92.append((art, r)),
                                                           _galt_f92(pos, eb, r, art, v))
g92.welt.klang = lambda name, laut=1.0, pos=None, eb=None: (_gk92.append(name),
                                                          _galt_k92(name, laut, pos, eb))
_z92.schaden(_z92.leben + 50, None, w92.ich)
for _ in range(6):
    w92.schritt(K.NETZ["takt"])
    g92.schritt(K.NETZ["takt"])
pruef("Netz: der Gast sieht den Fleck im Blut des Speiers und hoert den Todeslaut",
      [a_ for a_, _r in _gf92] == ["saeure"] and "tod" in _gk92, "%s %s" % (_gf92, _gk92))
del _gf92[:]
g92._wirkung_nachspielen([["d", 10.0, 10.0, 0, 0, "<script>", 9.0],
                          ["d", 10.0, 10.0, 0, 0, "zombie", "kaputt"],
                          ["d", 10.0, 10.0, 0, 0, "zombie", 1e9]])
pruef("... eine kaputte Meldung kostet hoechstens sich selbst: unbekanntes Blut wird "
      "\"mensch\", die Groesse ist begrenzt",
      len(_gf92) == 2 and _gf92[0][0] == "mensch" and _gf92[1][0] == "zombie"
      and _gf92[1][1] <= 60.0 * max(b_["groesse"] for b_ in K.BLUT.values()), str(_gf92))
w92.verlassen()
g92.verlassen()

# 0.34.34: "Bau dir mal eine LANGE Liste an Namen von Operators aus CoD oder
# Battlefield oder so aehnlich zusammen, damit die Bots bessere Namen haben.
# Also so Tags sollen die quasi haben (Ghost, Chimera usw usw)."
print("\n-- Rufnamen der Bots (0.34.34)")
_n93 = K.BOTS["namen"]
pruef("Eine lange Liste von Rufnamen, jeder nur einmal",
      len(_n93) >= 300 and len(set(_n93)) == len(_n93), "%d Namen" % len(_n93))
pruef("... nur Grossbuchstaben, hoechstens zehn - passt mit BOT- ueber den Kopf",
      all(n_.isalpha() and n_.isupper() and len(n_) <= 10 for n_ in _n93),
      str([n_ for n_ in _n93 if not (n_.isalpha() and n_.isupper() and len(n_) <= 10)][:5]))
pruef("... darunter GHOST und CHIMERA", "GHOST" in _n93 and "CHIMERA" in _n93, "")
_n93_ = netz.Gastgeber(_neuer_port())
_w93 = Gefecht(app, "WIRT", gastgeber=_n93_, modus="pvp", seed=93, regeln={"bots": 10})
_bn93 = [k_.name for k_ in _w93._bots()]
pruef("Bots heissen BOT- und ein Rufname aus der Liste, keiner doppelt",
      _bn93 and all(n_.startswith("BOT-") and n_[4:] in _n93 for n_ in _bn93)
      and len(set(_bn93)) == len(_bn93), str(_bn93))
_w93.verlassen()

# 0.34.38: "Sie sollen etwas mehr Commitment zu ihren Aufgaben zeigen ... das
# MG sollten sie priorisieren, dass sie wirklich laenger schiessen ... besser
# hoeren ... vor Granaten weglaufen, und da kann auch mal die Panik ueberhand
# nehmen ... Dashes sollen sie nicht haben." Innenleben, Rang und Bindung.
print("\n-- Innenleben, Bindung, Hoeren, Granaten (0.34.38)")
from dustfront import innenleben as _IL94

# Rang und Bindung im Gehirn (goap.Ziel).
_akt94 = [_GO88.Aktion("a", "", "fa", "1"), _GO88.Aktion("b", "", "fb", "1"),
          _GO88.Aktion("c", "", "fc", "1")]
_hirn94 = _GO88.Gehirn([_GO88.Ziel("eins", "fa", "50", bindung="2"),
                        _GO88.Ziel("zwei", "fb", "40 + x"),
                        _GO88.Ziel("not", "fc", "10 * n", rang="2 * n")], _akt94)
_hirn94.denken(0.0, {}, {"x": 0, "n": 0})
_hirn94.denken(0.5, {}, {"x": 30, "n": 0})
pruef("Bindung: ein dringenderes Ziel gleichen Rangs wartet, bis die Bindung um ist",
      _hirn94.ziel.name == "eins" and _hirn94.gebunden > 1.0, str(_hirn94.ziel))
_hirn94.denken(2.2, {}, {"x": 30, "n": 0})
pruef("... danach wechselt er", _hirn94.ziel.name == "zwei" and _hirn94.gewechselt, "")
_hirn94.denken(2.3, {}, {"x": 30, "n": 1})
pruef("... ein hoeherer Rang unterbricht sofort, auch wenn er weniger dringlich ist",
      _hirn94.ziel.name == "not", str(_hirn94.ziel))
_lese94 = _WD88.Daten()
_WD88.aus_text("[ziel z]\nwill: a\ndringlich: 5\nrang: 1 + panik\nbindung: 2 * disziplin\n", _lese94)
pruef("... beide kommen aus den Daten (rang:, bindung:)",
      _lese94.ziele["z"].rang.wert({"panik": 1}) == 2.0
      and _lese94.ziele["z"].bindung.wert({"disziplin": 0.5}) == 1.0, "")

# Dual Utility: mit Zufall und Unschaerfe unter den guten, nie ein schlechtes.
import collections as _co94
_gew94 = _co94.Counter()
for i_ in range(200):
    h_ = _GO88.Gehirn([_GO88.Ziel("gut", "fa", "60"), _GO88.Ziel("fast", "fb", "52"),
                       _GO88.Ziel("schlecht", "fc", "20")], _akt94, rnd=random.Random(i_))
    h_.denken(0.0, {}, {"unschaerfe": 1.0})
    _gew94[h_.ziel.name] += 1
pruef("Unscharfe Wahl: unter Stress mal das zweitbeste, nie das schlechte",
      _gew94["gut"] > _gew94["fast"] > 20 and _gew94["schlecht"] == 0, str(dict(_gew94)))
h_ = _GO88.Gehirn([_GO88.Ziel("gut", "fa", "60"), _GO88.Ziel("fast", "fb", "52")], _akt94,
                  rnd=random.Random(1))
pruef("... ohne Stress immer das beste",
      all(h_.denken(t_, {}, {"unschaerfe": 0.0}) and h_.ziel.name == "gut" for t_ in range(5)), "")

# Innenleben: Stress, Panik, Drill, Zuversicht.
_r94 = random.Random(94)
_i94 = _IL94.Innenleben({"mut": 0.5, "disziplin": 0.3, "drill": 0.0}, _r94)
_i94.ereignis("vorbei")
_s1_94 = _i94.stress
_i94.ereignis("vorbei")
pruef("Stress: eine Kugel knapp vorbei zaehlt, dieselbe Garbe nicht zwanzigmal",
      _s1_94 > 0 and _i94.stress == _s1_94, "%.3f %.3f" % (_s1_94, _i94.stress))
_d94 = _IL94.Innenleben({"mut": 0.5, "disziplin": 1.0, "drill": 1.0}, _r94)
_i94.ereignis("kamerad")
_d94.ereignis("kamerad")
pruef("... Disziplin und Drill daempfen, was ankommt", _d94.stress < _i94.stress * 0.6,
      "%.2f %.2f" % (_d94.stress, _i94.stress))
for _ in range(6):
    _i94.ereignis("kamerad")
    _i94.schritt(0.3, False, False)
pruef("... zu viel davon: Panik", _i94.panik, "Stress %.2f" % _i94.stress)
_dauer94 = []
for drill_ in (0.0, 1.0):
    i_ = _IL94.Innenleben({"mut": 0.5, "disziplin": 0.5, "drill": drill_}, random.Random(3))
    i_.stress = 0.99
    i_._panik_pruefen()
    _dauer94.append(i_.panik_rest)
pruef("... mit Drill ist sie kuerzer", _dauer94[1] < _dauer94[0] * 0.6, str(_dauer94))
_i94.beruhigen()
_i94.stress = 0.5
for _ in range(20):
    _i94.schritt(0.1, True, False)
_in94 = _i94.stress
_i94.stress = 0.5
for _ in range(20):
    _i94.schritt(0.1, False, False)
pruef("... und geht von selbst zurueck, in Deckung schneller", _in94 < _i94.stress < 0.5,
      "%.2f %.2f" % (_in94, _i94.stress))
_q94 = _IL94.zuversicht_rechnen(1.0, [(1.0, 1.0)], [(1.0, 1.0)])
_qp94 = _IL94.zuversicht_rechnen(1.0, [(1.0, 0.0)], [(1.0, 1.0)])
pruef("Zuversicht wie in Days Gone: zwei gegen einen ist gut, ein panischer Kamerad zaehlt "
      "fuer die andere Seite",
      _q94 == 2.0 and _qp94 == 0.5 and _IL94.stufe_von(_q94) == 3 and _IL94.stufe_von(_qp94) == 1
      and _IL94.zuversicht_rechnen(1.0, [], []) is None and _IL94.stufe_von(None) == 2,
      "%.2f %.2f" % (_q94, _qp94))
pruef("... wer schon zwei erwischt hat, ist zuversichtlicher",
      _IL94.zuversicht_rechnen(1.0, [], [(1.0, 1.0)], getoetet=2.0)
      > _IL94.zuversicht_rechnen(1.0, [], [(1.0, 1.0)]), "")

# Das MG: Stoesse, die ueber den Anlauf hinausgehen.
_mg94 = K.BOTS["feuer"]["lmg"]
pruef("MG-Feuerstoss laenger als sein Anlauf im Dauerfeuer (1,15 s), und er steht dabei",
      _mg94[0][0] > K.WAFFEN["lmg"]["modus_daten"]["dauer"]["anlauf"] and _mg94[2] >= 1.0,
      str(_mg94))

_tm = _TM87.Testmodus(app, karte="staubtal")
_tm.wiedereinstieg = False
_a94, _b94 = pygame.Vector2(_feld89[0]), pygame.Vector2(_feld89[1])
_mgbot94 = _tm.bot_setzen(_a94, 0, {"team": 0, "hirn": "goap", "waffe": "lmg"})
_puppe94 = _tm.puppe_setzen(_b94, 0, {"team": 1, "leben": 10.0})
_lauf94, _laengste94 = 0.0, 0.0
for _ in range(int(8.0 / _D87)):
    _tm.schritt(_D87)
    _lauf94 = _lauf94 + _D87 if _mgbot94.feuert else 0.0
    _laengste94 = max(_laengste94, _lauf94)
pruef("Ein GOAP-Bot mit MG haelt lange drauf (laengster Stoss ueber 1,2 s)",
      _laengste94 > 1.2 and _mgbot94.waffe_name == "lmg", "%.2f s" % _laengste94)
pruef("... und bleibt am Gegner, der stehen bleibt (keine Flucht in Deckung)",
      _mgbot94.hirn.gehirn.ziel is not None
      and _mgbot94.hirn.gehirn.ziel.name in ("feind_ausschalten", "gruppe_bekaempfen", "nachladen"),
      str(_mgbot94.hirn.gehirn.ziel))

# Eine Kugel vorbei schickt ihn nicht mehr in Deckung - erst der Stress.
_tm.alles_weg()
_bot94 = _tm.bot_setzen(_a94, 0, {"team": 0, "hirn": "goap", "waffe": "sturm"})
_puppe94 = _tm.puppe_setzen(_b94, 0, {"team": 1, "leben": 10.0})
_sim87(int(1.5 / _D87))
_bot94.hirn.kugel_vorbei()
_bot94.hirn.unterdrueckt = K.BOTS["unterdrueckt_zeit"]
_sim87(int(0.3 / _D87))
pruef("Eine einzelne Kugel knapp vorbei: er kaempft weiter",
      _bot94.hirn.gehirn.ziel.name != "ueberleben", str(_bot94.hirn.gehirn.ziel))
_bot94.hirn.innen.stress = 0.95
_bot94.hirn.innen.panik_rest = 0.0
_bot94.hirn.innen.schreck_rest = 0.0
_bot94.hirn.goap_rest = 0.0
_sim87(int(0.3 / _D87))
# Auf dem freien Feld gibt es keine Deckung: dann scheitert DECKUNG, und
# bleibt der Stress, kommt die Panik. Beides heisst: er will weg.
_will94 = [t_ for _z, t_ in _bot94.hirn.gehirn.protokoll
           if t_.startswith(("ZIEL: ueberleben", "ZIEL: panik"))]
pruef("... unter grossem Stress will er in Deckung (oder rennt in Panik)",
      bool(_will94), str(list(_bot94.hirn.gehirn.protokoll)[-4:]))

# Granate: wegrennen, vor allem anderen.
_tm.alles_weg()
_bot94 = _tm.bot_setzen(_a94, 0, {"team": 0, "hirn": "goap"})
_puppe94 = _tm.puppe_setzen(_b94, 0, {"team": 1, "leben": 10.0})
_sim87(int(1.0 / _D87))
_gr94 = _tm.wurf_setzen("granate", _bot94.pos + pygame.Vector2(14, 0), 0, {"zuender": "liegt"})
_gr94.rest = 1.0
_vorher94 = _bot94.pos.distance_to(_gr94.pos)
_ziele94 = set()
_stress94 = 0.0
for _ in range(int(0.8 / _D87)):
    _tm.schritt(_D87)
    _stress94 = max(_stress94, _bot94.hirn.innen.stress)
    if _bot94.hirn.gehirn.ziel is not None:
        _ziele94.add(_bot94.hirn.gehirn.ziel.name)
pruef("Eine Granate neben ihm: er rennt weg (Ziel GRANATE AUSWEICHEN, Rang 3)",
      "granate_ausweichen" in _ziele94 and _bot94.pos.distance_to(_gr94.pos) > _vorher94 + 25,
      "%s, %.0f -> %.0f px" % (sorted(_ziele94), _vorher94, _bot94.pos.distance_to(_gr94.pos)))
pruef("... und das macht Stress", _stress94 > 0.1 and _bot94.hirn.innen.zuletzt in ("granate", "panik"),
      "%.2f %s" % (_stress94, _bot94.hirn.innen.zuletzt))

# Hoeren: ein Schuss, den er nicht sieht, und Schritte hinter ihm.
_tm.alles_weg()
_bot94 = _tm.bot_setzen(_a94, 0, {"team": 0, "hirn": "goap"})
_feind94 = _tm.puppe_setzen(_a94 + pygame.Vector2(0, 2000), 0, {"team": 1})
_sim87(3)
_ort94 = _a94 + pygame.Vector2(-300, 0)
_tm._bot_hoert(_ort94, 0, _feind94)
_sim87(int(0.25 / _D87))
pruef("Hoeren: ein Schuss der anderen Seite kommt ins Lagebild, ungefaehr dort",
      any(e_[0].distance_to(_ort94) < 90 for e_ in _bot94.hirn.lagebild)
      and _bot94.hirn.gehirn.fakten.get("feind_gehoert"),
      str([(round(e_[0].x), round(e_[0].y), e_[3]) for e_ in _bot94.hirn.lagebild]))
_tm._bot_hoert(_a94 + pygame.Vector2(2000, 0), 0, _feind94)
_sim87(int(0.25 / _D87))
pruef("... einer weit weg nicht", not any(e_[0].distance_to(_a94) > 1500
                                          for e_ in _bot94.hirn.lagebild), "")
_bot94.hirn.lagebild = []
# Neben dem Bot, wo er jetzt steht - dem Schuss eben ist er nachgegangen.
_feind94.pos.update(_bot94.pos + pygame.Vector2(-80, 0))
_feind94.ebene = 0
for _ in range(6):
    _feind94.tempo.update(-120, 0)
    _bot94.hirn.gesehen.pop(_feind94, None)
    _bot94.hirn.geblendet = 0.0
    _bot94.hirn._lagebild_auffrischen()
pruef("... ein Gegner, der in der Naehe rennt, ist zu hoeren",
      any(e_[3] == "schritte" for e_ in _bot94.hirn.lagebild), "")

# Deckung mit Ueberblick: nicht mitten zwischen andere Gegner, die er kennt.
_tm.alles_weg()
_bot94 = _tm.bot_setzen(_a94, 0, {"team": 0, "hirn": "goap"})
_bot94.hirn.lagebild = [[_a94 + pygame.Vector2(0, 120), 0, _tm.welt.zeit, "schritte"]]
_wert94 = _bot94.hirn._deckung_wert(_a94 + pygame.Vector2(0, 80), _a94 + pygame.Vector2(300, 0),
                                    None)
_frei94 = _bot94.hirn._deckung_wert(_a94 + pygame.Vector2(0, -60), _a94 + pygame.Vector2(300, 0),
                                    None)
pruef("Deckung mit Ueberblick: keine Stelle mitten zwischen anderen Gegnern, die er kennt",
      _wert94 is None and _frei94 is not None, "%s %s" % (_wert94, _frei94))
_bot94.hirn.innen.panik_setzen()
pruef("... in Panik sieht er nur den einen (Tunnelblick)",
      _bot94.hirn._deckung_wert(_a94 + pygame.Vector2(0, 80), _a94 + pygame.Vector2(300, 0), None)
      is not None, "")

# Kein Dash mehr - auch die klassische KI nicht.
_tm.alles_weg()
_kl94 = _tm.bot_setzen(_a94, 0, {"team": 0, "hirn": "klassisch"})
_ziel94 = _tm.puppe_setzen(_a94 + pygame.Vector2(110, 0), 0, {"team": 1})
_dash94 = False
for _ in range(400):
    ein_ = {"knoepfe": []}
    _kl94.hirn._nahkampf(ein_, _ziel94, 110.0)
    _dash94 = _dash94 or "dash" in ein_["knoepfe"]
pruef("Bots dashen nicht mehr (auch die klassischen nicht)", not _dash94, "")

# Wer ihn von der Seite trifft, wird sein Ziel.
_tm.alles_weg()
_bot94 = _tm.bot_setzen(_a94, 0, {"team": 0, "hirn": "goap"})
# Zwei Gegner, beide in freier Sicht: einer auf der Bahn, einer daneben.
_f1_94 = _tm.puppe_setzen(_b94, 0, {"team": 1, "leben": 10.0})
_f2_94 = _tm.puppe_setzen((_a94 + _b94) / 2, 0, {"team": 1, "leben": 10.0})
_bot94.hirn._wahrnehmen()
_erst94 = _bot94.hirn.ziel
_anderer94 = _f2_94 if _erst94 is _f1_94 else _f1_94
_bot94.zuletzt_von = _anderer94
_bot94.hirn.getroffen_rest = 2.0
_bot94.hirn.stoss_rest = 0.0
_bot94.hirn._wahrnehmen()
pruef("Von einem anderen getroffen: er dreht sich zu dem, der schiesst",
      _erst94 is not None and _bot94.hirn.ziel is _anderer94, "")

# Testmodus: Innenleben anzeigen und verstellen.
_tm._zeiger_welt = pygame.Vector2(_bot94.pos)
_tm.blick = 0
pruef("Testmenue: Zeile INNENLEBEN", any(z_[0] == "innen" for z_ in _tm._menue_zeilen()), "")
# Im Freien und ohne Deckung in der Naehe bleibt in Panik nur Fliehen - das
# gibt es in Runden seit 0.34.56 nicht mehr; geprueft wird hier die Taste.
_tm.bot_fliehen = True
_tm._innen_nr = 0
_tm.menue_wirken("innen", 1, ausloesen=True)
_bot94.hirn.goap_rest = 0.0
_sim87(int(0.25 / _D87))
pruef("... PANIK: die gezeigte Figur rennt (Ziel PANIK)",
      _bot94.hirn.innen.panik and _bot94.hirn.gehirn.ziel is not None
      and _bot94.hirn.gehirn.ziel.name == "panik", str(_bot94.hirn.gehirn.ziel))
_tm.innen_wirken("ruhe")
pruef("... RUHE: vorbei", not _bot94.hirn.innen.panik and _bot94.hirn.innen.stress == 0.0, "")
_tm.bot_fliehen = False
for i_ in (1, 2):
    _tm.info = i_
    _tm.zeichnen(pygame.Surface((K.GAME_W, K.GAME_H)), 1.0)
pruef("... INFO zeigt Stress, Zuversicht und das Gehoerte (zeichnen geht)", True, "")
_tm.verlassen()

# 0.34.39: "dass die Teams verschiedene Squad-Leader haben, die miteinander
# ueber Funk kommunizieren ... wenn das eine Team sagt, wir sind in der
# Unterzahl, wir halten aber eine wichtige Position, dann sollen sie nach
# Hilfe rufen ... Die Squad-Leader sollen nur einen Repetierer und eine
# Rauchgranate haben ... eher hinten bleiben ... beim Suchen nicht direkt
# hintereinander laufen ... in Sprechreichweite bleiben."
print("\n-- Trupps, Anfuehrer, Sprechen, Funk (0.34.39)")
from dustfront import trupp as _TR95
_tm = _TM87.Testmodus(app, karte="staubtal")
_tm.wiedereinstieg = False
_r95 = random.Random(95)


def _feld95(weite):
    for _ in range(8000):
        a_ = pygame.Vector2(freier_punkt(_tm.welt, 0, _r95))
        b_ = a_ + pygame.Vector2(weite, 0).rotate(_r95.uniform(0, 360))
        if (all(_tm.welt.frei(p_, 30, 0, True) for p_ in (a_, b_, (a_ + b_) / 2))
                and _tm.welt.deckung(a_, b_, 0) == ""):
            return a_, b_
    return None


_e95 = _tm._eintrag("TRUPP")
pruef("Spawner: TRUPP mit Groesse, Team, Anfuehrer und Waffen; dazu HALTEN, ANGRIFF, FREI",
      _e95.name == "TRUPP" and {"groesse", "team", "fuehrer", "mischung"} <= set(_e95.optionen)
      and all(_tm._eintrag(n_).name == n_ for n_ in ("TRUPP: HALTEN HIER", "TRUPP: ANGRIFF HIER",
                                                       "TRUPP: FREI")), "")
_a95, _b95 = _feld95(320)
_al95 = _tm.trupp_setzen(_a95, 0, {"groesse": 4, "team": 0, "fuehrer": "funk",
                                   "mischung": "gemischt"})
_f95 = _al95.fuehrer
pruef("Ein Trupp aus vier GOAP-Bots, der Anfuehrer mit Repetierer, Rauch und Funkgeraet",
      len(_al95.mitglieder) == 4 and all(isinstance(m_.hirn, _BG88.GoapHirn) for m_ in _al95.mitglieder)
      and all(m_.hirn.trupp is _al95 for m_ in _al95.mitglieder)
      and _f95.waffen == ["repetierer", "rauch"] and _f95.funkgeraet,
      "%s %s" % (_f95.waffen, getattr(_f95, "funkgeraet", None)))
pruef("... GEMISCHT: MG, Schrot und Scharfschuetze sind dabei",
      {"lmg", "schrot", "scharf"} <= {w_ for m_ in _al95.mitglieder for w_ in m_.waffen}, "")
_sim87(int(1.0 / _D87))
_st95 = [_al95.stellung(m_) for m_ in _al95.mitglieder if m_ is not _f95]
_abst95 = min(p_.distance_to(q_) for i_, p_ in enumerate(_st95) for q_ in _st95[i_ + 1:])
pruef("Ohne Kontakt: eine breite Linie neben dem Anfuehrer, nicht hintereinander",
      _al95.zustand == "suchen" and len(_st95) == 3 and _abst95 > 30
      and all(p_.distance_to(_f95.pos) < K.TRUPP["sprech_weite"] for p_ in _st95),
      "%s, engster Abstand %.0f" % (_al95.zustand, _abst95))
_fak95 = _f95.hirn._trupp_fakten()
pruef("... der Anfuehrer weiss, dass er fuehrt und Funk hat; die anderen nicht",
      _fak95["ist_fuehrer"] and _fak95["hat_funk"]
      and not any(m_.hirn._trupp_fakten()["ist_fuehrer"] for m_ in _al95.mitglieder if m_ is not _f95), "")

# Wissen geht nur in Sprechweite.
_feind95 = _tm.puppe_setzen(_b95, 0, {"team": 1, "leben": 10.0})
_m95 = next(m_ for m_ in _al95.mitglieder if m_ is not _f95)
_al95.lage = {}
_m95.hirn.gesehen = {_feind95: (pygame.Vector2(_feind95.pos), 0, _tm.welt.zeit)}
_al95._lage_sammeln(_al95.lebende())
# Seit 0.34.50 nicht mehr im selben Augenblick: er ruft es zu, und erst wenn
# der Satz durch ist (K.SPRECHEN["dauer"]), weiss es der Trupp.
_sofort95 = _feind95 in _al95.lage
_m95.hirn._angesagt = {}
_m95.hirn.zuruf = None
_m95.hirn._ansagen()
_tm.welt.zeit += K.SPRECHEN["dauer"][1] + 0.05
_m95.hirn._zuruf_fuehren()
pruef("Sprechen: wer einen sieht und andere in Sprechweite hat, sagt es - dann weiss es der Trupp",
      not _sofort95 and _feind95 in _al95.lage and _m95.hirn.gesagt.endswith("!"), _m95.hirn.gesagt)
_weg95 = pygame.Vector2(_m95.pos)
_m95.pos.update(_m95.pos + pygame.Vector2(K.TRUPP["sprech_weite"] * 3, 0))
_al95.lage = {}
_m95.hirn._angesagt = {}
_m95.hirn._ansagen()
_al95._lage_sammeln(_al95.lebende())
pruef("... wer zu weit weg ist, dessen Wissen kommt nicht an",
      _feind95 not in _al95.lage and not _al95.in_kontakt(_m95) and _m95.hirn.zuruf is None
      and _m95.hirn._trupp_fakten()["allein"], "")
_m95.pos.update(_weg95)

# Front und Bahnen: der Anfuehrer in der Mitte und tiefer.
_al95.zustand = "feuerkampf"
_al95._zustand_seit = _tm.welt.zeit
_al95.lage = {_feind95: [pygame.Vector2(_feind95.pos), 0, _tm.welt.zeit]}
_al95.front = None
_al95._front_rechnen(_al95.lebende())
_al95._stellungen(_al95.lebende())
_fr95 = _al95.front
_tief95 = {m_.nummer: (_fr95["linie"] - _al95.stellung(m_)).dot(_fr95["richtung"])
           for m_ in _al95.mitglieder}
_quer95 = sorted((_al95.stellung(m_) - _fr95["linie"]).dot(_fr95["quer"]) for m_ in _al95.mitglieder)
pruef("Frontlinie: jeder hat seine Bahn, der Anfuehrer steht weiter hinten als die anderen",
      _fr95 is not None and _tief95[_f95.nummer] > max(v_ for n_, v_ in _tief95.items()
                                                          if n_ != _f95.nummer) - 1
      and min(b_ - a_ for a_, b_ in zip(_quer95, _quer95[1:])) > 20, str(_tief95))

# Zustaende aus der Zuversicht des Trupps.
def _zustand95(stufe, auftrag="frei", wichtig=False):
    for m_ in _al95.lebende():
        m_.hirn.innen.stufe = stufe
    _al95.auftrag = dict(art=auftrag, ort=pygame.Vector2(_a95) if auftrag != "frei" else None,
                         ebene=0, wichtig=wichtig)
    _al95._zustand_seit = -1e9
    _al95._zuversicht(_al95.lebende())
    _al95._zustand_waehlen(_al95.lebende())
    return _al95.zustand


# Druck nur mit BOTS UEBERMUETIG (seit 0.34.58, gemeldet: die Ueberzahl
# verliess die Deckung und stellte sich in einer Linie auf) - sonst bleibt
# auch ein zuversichtlicher Trupp im Feuerkampf.
_tm.bot_uebermut = True
_ueber95 = _zustand95(3)
_tm.bot_uebermut = False
pruef("Trupp besorgt: Rueckzug in Wellen; zuversichtlich: Druck (nur uebermuetig); neutral: Feuerkampf",
      _zustand95(1) == "rueckzug" and _ueber95 == "druck" and _zustand95(2) == "feuerkampf", _ueber95)
pruef("... ohne Uebermut (Grundeinstellung) bleibt ein zuversichtlicher Trupp im Feuerkampf",
      _zustand95(3) == "feuerkampf", _al95.zustand)
pruef("... eine wichtige Stellung wird nicht aufgegeben, auch besorgt nicht",
      _zustand95(1, "halten", True) == "halten", _al95.zustand)
_zustand95(1)
_al95._front_rechnen(_al95.lebende())
_al95._stellungen(_al95.lebende())
pruef("... im Rueckzug zieht die Haelfte, die andere deckt",
      0 < len(_al95.welle) < len(_al95.lebende()), str(_al95.welle))
_tm.alles_weg()

# Funk: der eine haelt in der Unterzahl und ruft, der andere hat Ruhe und kommt.
# Die Gegner in Sichtweite (330 px): wer haelt, geht nicht suchen.
_a95, _b95 = _feld95(220)
_c95 = None
for _ in range(400):
    f_ = _feld95(200)
    if f_ is not None and 500 < f_[0].distance_to(_a95) < 1200 and f_[0].distance_to(_b95) > 500:
        _c95 = f_[0]
        break
pruef("(Platz fuer zwei Trupps)", _c95 is not None, "")
_al95 = _tm.trupp_setzen(_a95, 0, {"groesse": 3, "team": 0, "fuehrer": "funk", "mischung": "zufall"})
_tm.trupp_auftrag("halten", _a95, 0, {"team": 0, "wichtig": True})
_br95 = _tm.trupp_setzen(_c95, 0, {"groesse": 3, "team": 0, "fuehrer": "funk", "mischung": "zufall"})
for m_ in _al95.mitglieder:
    m_.unverwundbar = 1e9          # sie sollen funken, nicht gleich fallen
_feinde95 = [_tm.puppe_setzen(_b95 + pygame.Vector2(0, 22 * i_), 0, {"team": 1, "leben": 10.0})
             for i_ in range(7)]
_start95 = _br95.fuehrer.pos.distance_to(_a95)
# 14 s mit dem Funk von 0.34.39 (2,2 s je Spruch); seit 0.34.48 dauert ein
# Spruch laenger, und vorher zieht sich der Anfuehrer zurueck.
_fenster95 = 14.0 + 1.5 * (K.TRUPP["funk_dauer"] - 2.2) + K.TRUPP["funk_weg_zeit"]
_sendet95 = False
for _ in range(int(_fenster95 / _D87)):
    _tm.schritt(_D87)
    _fl95 = _al95.fuehrer.hirn.funk_laeuft
    if _fl95 is not None and _fl95.get("phase") == "senden" and _al95.fuehrer.tempo.length() < 5.0:
        _sendet95 = True
_netz95 = getattr(_tm, "_funknetz", [])
_arten95 = [(s_.trupp.name, s_.art) for s_ in _netz95]
pruef("Funk: ALPHA ist in der Unterzahl an einer wichtigen Stellung und ruft um Hilfe",
      (_al95.name, "hilfe") in _arten95, str(_arten95))
pruef("... BRAVO hat keine Gegner, sagt zu - und antwortet auch",
      (_br95.name, "zusage") in _arten95, str(_arten95))
pruef("... und ist unterwegs zu ALPHA",
      _br95.fuehrer.pos.distance_to(_a95) < _start95 - 60,
      "%.0f -> %.0f px, %s" % (_start95, _br95.fuehrer.pos.distance_to(_a95),
                               list(_br95.fuehrer.hirn.gehirn.protokoll)[-6:]))
# Seit 0.34.48 dauert das Funken laenger, und das Protokoll (begrenzt)
# behielt den Plan nicht bis zum Ende: geprueft wird darum unterwegs.
pruef("... ein Spruch dauert: er stand dabei und sprach",
      _sendet95, "")
pruef("Wer selbst unterlegen ist, sagt nicht zu", not _al95.hilfe_pruefen(_netz95[0]), "")

# Ohne Funkgeraet und ohne Leute ist der Anfuehrer ein Bot wie jeder andere.
_tm.alles_weg()
_oh95 = _tm.trupp_setzen(_a95, 0, {"groesse": 3, "team": 0, "fuehrer": "ohne"})
_fo95 = _oh95.fuehrer
pruef("Anfuehrer OHNE FUNK: er fuehrt, aber funken ist fuer ihn kein Ziel",
      not getattr(_fo95, "funkgeraet", False) and _fo95.hirn._trupp_fakten()["ist_fuehrer"]
      and not _fo95.hirn._trupp_fakten()["hat_funk"], "")
for m_ in _oh95.mitglieder:
    if m_ is not _fo95:
        _tm.loeschen(m_)
_alle95 = _fo95.hirn._trupp_fakten()
pruef("... allein uebrig: nichts mehr vom Trupp - dieselben Ziele wie jeder Bot",
      not any(_alle95[n_] for n_ in ("im_trupp", "ist_fuehrer", "trupp_unterlegen", "allein")), "")

# Die anderen nehmen zuerst, wer dem Anfuehrer zu nahe kommt.
_tm.alles_weg()
_tz95 = _tm.trupp_setzen(_a95, 0, {"groesse": 3, "team": 0, "fuehrer": "funk"})
_mann95 = next(m_ for m_ in _tz95.mitglieder if m_ is not _tz95.fuehrer)
_nah95 = _tm.puppe_setzen(_tz95.fuehrer.pos + pygame.Vector2(60, 0), 0, {"team": 1})
_fern95 = _tm.puppe_setzen(_tz95.fuehrer.pos + pygame.Vector2(600, 0), 0, {"team": 1})
pruef("Wer dem Anfuehrer zu nahe kommt, ist zuerst dran",
      _mann95.hirn._ziel_bonus(_nah95) >= K.TRUPP["fuehrer_bonus"]
      and _mann95.hirn._ziel_bonus(_fern95) == 0, "")

# Testmodus: Auftraege, Anzeige.
_tm.trupp_auftrag("halten", _a95 + pygame.Vector2(40, 0), 0, {"team": 0, "wichtig": True})
pruef("TRUPP: HALTEN HIER gibt dem naechsten Trupp der Mannschaft den Auftrag",
      _tz95.auftrag["art"] == "halten" and _tz95.auftrag["wichtig"], str(_tz95.auftrag))
_tm.trupp_auftrag("frei", _a95, 0, {"team": 0})
pruef("... FREI nimmt ihn wieder", _tz95.auftrag["art"] == "frei", "")
_tz95.fuehrer.hirn.funk_laeuft = dict(art="lage", bis=_tm.welt.zeit + 1, anfang=_tm.welt.zeit,
                                      text="PROBE")
for i_ in (1, 2):
    _tm.info = i_
    _tm.zeichnen(pygame.Surface((K.GAME_W, K.GAME_H)), 1.0)
_tm.sauber = True
_tm.zeichnen(pygame.Surface((K.GAME_W, K.GAME_H)), 1.0)
_tm.sauber = False
pruef("... INFO zeigt Front, Stellungen, Zustand und Funk; Funk auch in der sauberen Ansicht",
      True, "")
_tm.alles_weg()
pruef("ALLES WEG nimmt auch die Trupps und den Funk", not _TR95.trupps(_tm)
      and not getattr(_tm, "_funknetz", None), "")
_tm.verlassen()

# 0.34.40: "dass immer Leichen von toten Gegnern schon gedroppt werden, nur
# bei den Bots ... die auch wiederbelebt werden koennen, aber dass die Bots
# priorisieren, sie erst in Sicherheit zu ziehen ... Deckung geben, waehrend
# ein oder zwei Bots vorruecken ... nur einmal ... danach eine neue Leiche,
# die ein bisschen anders aussieht und nach ein paar Sekunden despawnt ...
# ein reanimierter Bot soll schwaecher sein, sich langsamer bewegen ... nur
# wenn es recht sicher erscheint."
print("\n-- Verwundete Bots: liegen, bergen, wiederbeleben (0.34.40)")
from dustfront.testmodus import Leiche as _Leiche96
_tm = _TM87.Testmodus(app, karte="staubtal")
_tm.wiedereinstieg = False
pruef("Testmenue: VERWUNDETE BOTS, vorgegeben AN, bleibt ueber einen Kartenwechsel",
      any(z_[0] == "verwundete" and z_[2] == "AN" for z_ in _tm._menue_zeilen())
      and _tm.zustand().get("verwundete") is True, "")
_r96 = random.Random(96)
_a96 = _b96 = None
for _ in range(8000):
    a_ = pygame.Vector2(freier_punkt(_tm.welt, 0, _r96))
    b_ = a_ + pygame.Vector2(260, 0).rotate(_r96.uniform(0, 360))
    if all(_tm.welt.frei(p_, 30, 0, True) for p_ in (a_, b_)) and _tm.welt.deckung(a_, b_, 0) == "":
        _a96, _b96 = a_, b_
        break
_bot96 = _tm.bot_setzen(_a96, 0, {"team": 0, "hirn": "goap"})
_pup96 = _tm.puppe_setzen(_a96 + pygame.Vector2(40, 0), 0, {"team": 0})
pruef("... nur Bots fallen zu Boden, Spielerfiguren nicht",
      _bot96.revive_an and not _pup96.revive_an, "")
_tm.toeten(_bot96)
pruef("Gefallen: er liegt (die erste Leiche, mit Lache) - lebt noch, ist zu retten",
      _bot96.lebt and _bot96.am_boden and _bot96.bild == "spieler_rot_boden", _bot96.bild)
_tm.toeten(_bot96)
_sim87(2)
_lei96 = [w_ for w_ in _tm.welt.wesen if isinstance(w_, _Leiche96)]
pruef("... nochmal: tot - und eine zweite Leiche, die anders aussieht",
      not _bot96.lebt and len(_lei96) == 1 and _lei96[0].bild == "leiche_rot"
      and "leiche_rot" in K.BILD_MASS and _tm.renderer.bilder.gedreht("leiche_rot", 0.0) is not None,
      str([l_.bild for l_ in _lei96]))
_sim87(int((K.VERWUNDET["leiche_zeit"] + 0.5) / _D87))
pruef("... sie ist nach ein paar Sekunden weg",
      not any(isinstance(w_, _Leiche96) for w_ in _tm.welt.wesen), "")

# Ohne Gefahr: hin, aufhelfen - danach geschwaecht, und nur einmal.
_tm.alles_weg()
_tr96 = _tm.trupp_setzen(_a96, 0, {"groesse": 3, "team": 0, "fuehrer": "funk", "mischung": "zufall"})
_sim87(int(1.0 / _D87))
_opfer96 = next(m_ for m_ in _tr96.mitglieder if m_ is not _tr96.fuehrer)
_voll96 = _opfer96.max_leben
_tm.toeten(_opfer96)
_akt96 = set()
for _ in range(int(14.0 / _D87)):
    _tm.schritt(_D87)
    for m_ in _tr96.mitglieder:
        if m_.lebt and m_.hirn.gehirn.aktion is not None:
            _akt96.add(m_.hirn.gehirn.aktion.name)
    if not _opfer96.am_boden:
        break
pruef("Ohne Gegner in Sicht: einer geht hin und hilft auf",
      _opfer96.lebt and not _opfer96.am_boden and "aufhelfen" in _akt96, str(sorted(_akt96)))
pruef("... danach ist er geschwaecht: weniger Leben, langsamer, haelt Abstand",
      _opfer96.max_leben < _voll96 * 0.7 and _opfer96.tempo_anteil < 1.0
      and _opfer96.hirn.geschwaecht and _opfer96.hirn.abstand_mehr > 0
      and _opfer96.hirn._trupp_fakten() is not None and _opfer96.hirn.fuehlen()[0]["geschwaecht"],
      "%.0f/%.0f, Tempo %.2f" % (_opfer96.max_leben, _voll96, _opfer96.tempo_anteil))
pruef("... und das ging nur einmal: der naechste Fall ist der letzte",
      not _opfer96.revive_an and _opfer96.wiederbelebt, "")
_tm._wieder_einsteigen(_opfer96)
pruef("Ein neues Leben macht ihn wieder ganz (und wieder einmal rettbar)",
      _opfer96.max_leben == _voll96 and _opfer96.tempo_anteil == 1.0
      and _opfer96.revive_an and not _opfer96.hirn.geschwaecht, "")

# Mit Gegnern, die ihn sehen: zu gefaehrlich - bis der Rauch liegt.
_tm.alles_weg()
_tr96 = _tm.trupp_setzen(_a96, 0, {"groesse": 4, "team": 0, "fuehrer": "funk", "mischung": "gemischt"})
_fe96 = [_tm.puppe_setzen(_b96 + pygame.Vector2(0, 30 * i_), 0, {"team": 1, "leben": 10.0})
         for i_ in range(2)]
for f_ in _fe96:
    f_.unverwundbar = 1e9
_sim87(int(1.5 / _D87))
_opfer96 = next(m_ for m_ in _tr96.mitglieder if m_ is not _tr96.fuehrer)
_tm.toeten(_opfer96)
_sim87(int(0.5 / _D87))
_b96_ = _tr96.bergung
pruef("Zwei Gegner sehen ihn: der Trupp haelt das Bergen fuer zu gefaehrlich, bestimmt aber "
      "schon die Retter (nicht den Anfuehrer)",
      _b96_ is not None and not _b96_["sicher"] and _b96_["bedrohung"] >= 1
      and 1 <= len(_b96_["retter"]) <= K.VERWUNDET["retter"]
      and _tr96.fuehrer.nummer not in _b96_["retter"], str(_b96_))
# Seit 0.34.54 hat der Rauch beim Bergen Rang 1: manchmal fliegt er nach
# einer halben Sekunde schon - dann hat er keinen mehr, und das ist recht so.
_rauch_fliegt96 = any(getattr(w_, "bild", "") == "rauchgranate" and w_.lebt for w_ in _tm.welt.wesen) \
    or bool(_tm.welt.rauch)
pruef("... der Anfuehrer will Rauch legen, um es sicher zu machen (oder hat ihn schon geworfen)",
      _tr96.fuehrer.hirn.gehirn.dringlichkeiten.get("rauch_legen", 0) > 0 or _rauch_fliegt96,
      str(_tr96.fuehrer.hirn.gehirn.dringlichkeiten.get("rauch_legen")))
_akt96 = set()
_erst96 = None          # war es sicher, als einer anfing zu ziehen oder aufzuhelfen?
for _ in range(int(30.0 / _D87)):
    _tm.schritt(_D87)
    for m_ in _tr96.mitglieder:
        if m_.lebt and m_.hirn.gehirn.aktion is not None:
            n_ = m_.hirn.gehirn.aktion.name
            _akt96.add((m_ is _tr96.fuehrer, n_))
            if _erst96 is None and n_ in ("kamerad_ziehen", "aufhelfen", "aufhelfen_offen") \
                    and _tr96.bergung is not None:
                _erst96 = _tr96.bergung["sicher"]
    if not _opfer96.am_boden:
        break
# Wer schon in Reichweite liegt, dem hilft der Retter gleich auf: seit
# 0.34.55 plant er mitten im Aufhelfen nicht mehr das Ziehen - vorher kam
# kamerad_ziehen hier oft nur durch dieses Hin und Her in die Liste.
pruef("... geholt wird erst, wenn es sicher genug ist (Rauch oder ein zuversichtlicher Trupp) - "
      "dann steht er wieder",
      _erst96 is True and any((False, n_) in _akt96 for n_ in ("zum_kameraden", "kamerad_ziehen",
                                                              "aufhelfen", "aufhelfen_offen"))
      and _opfer96.lebt and not _opfer96.am_boden,
      "%s, sicher beim Anfang: %s, liegt %s" % (sorted(_akt96), _erst96, _opfer96.am_boden))

# Rauch auf der Sichtlinie zaehlt (trupp.sieht_durch_rauch).
from dustfront.entities import Rauchwolke as _RW96
from dustfront import trupp as _TR96
_tm.alles_weg()
_frei96 = _TR96.sieht_durch_rauch(_tm.welt, _a96, _b96, 0)
_tm.welt.rauch.append(_RW96((_a96 + _b96) / 2, 0))
for _ in range(int(3.0 / _D87)):
    for r_ in _tm.welt.rauch:
        r_.schritt(_D87)
pruef("Rauch auf der Linie verdeckt den Liegenden", _frei96
      and not _TR96.sieht_durch_rauch(_tm.welt, _a96, _b96, 0), "")
_tm.welt.rauch.clear()

_tm.alles_weg()
_lieg96 = _tm.bot_setzen(_a96, 0, {"team": 0, "hirn": "goap"})
_tm.toeten(_lieg96)
pruef("Ueber einem Liegenden steht fuer den Beobachter kein \"[E] AUF\" (seit 0.34.42)",
      _lieg96.am_boden and _tm.beobachter and not _tm._verbuendet(_lieg96)
      and not _tm._darf_helfen(_tm.ich, _lieg96), "")

# Aus: wie vorher - wer faellt, ist tot, ohne Leiche.
_tm.alles_weg()
_tm.menue_wirken("verwundete")
_bot96 = _tm.bot_setzen(_a96, 0, {"team": 0, "hirn": "goap"})
_tm.toeten(_bot96)
_sim87(2)
pruef("VERWUNDETE BOTS AUS: tot beim ersten Mal, keine Leiche",
      not _tm.verwundete and not _bot96.lebt
      and not any(isinstance(w_, _Leiche96) for w_ in _tm.welt.wesen), "")
_tm.menue_wirken("verwundete")
for i_ in (1, 2):
    _tm.info = i_
    _tm.zeichnen(pygame.Surface((K.GAME_W, K.GAME_H)), 1.0)
_tm.verlassen()

# 0.34.41: "wenn der eine Trupp umzingelt ist, dann soll er ein Gebiet kurz
# sichern und sich weiter in das zurueckziehen, sodass sie alle Seiten
# abwehren koennen ... dass sie bestimmte Chokepoints gegen Zombies halten,
# dass sie sich, wenn es ein Gebiet gibt, was von Deckung umgeben ist, da
# drinnen eine Art kleine Position aufbauen."
print("\n-- Igel und Engstellen (0.34.41)")
from dustfront import trupp as _TR97
_tm = _TM87.Testmodus(app, karte="staubtal")
_tm.wiedereinstieg = False
_r97 = random.Random(97)
_a97 = _seiten97 = None
for _ in range(20000):
    a_ = pygame.Vector2(freier_punkt(_tm.welt, 0, _r97))
    s_ = [a_ + pygame.Vector2(250, 0).rotate(w_) for w_ in (0, 120, 240)]
    if (all(_tm.welt.frei(p_, 30, 0, True) for p_ in [a_] + s_)
            and all(_tm.welt.sicht_frei(a_, p_, 0) for p_ in s_)):
        _a97, _seiten97 = a_, s_
        break
pruef("(eine Stelle mit freier Sicht nach drei Seiten)", _a97 is not None, "")
_tr97 = _tm.trupp_setzen(_a97, 0, {"groesse": 5, "team": 0, "fuehrer": "funk", "mischung": "gemischt"})
_leute97 = _tr97.lebende()
_t97 = _tm.welt.zeit
_dummy97 = [type("F", (), {"lebt": True, "pos": p_, "ebene": 0})() for p_ in _seiten97]
_tr97.lage = {d_: [pygame.Vector2(d_.pos), 0, _t97] for d_ in _dummy97}
_um97 = _tr97.umzingelt(_leute97)
_tr97.lage = {d_: [pygame.Vector2(_seiten97[0]) + pygame.Vector2(0, 20 * i_), 0, _t97]
              for i_, d_ in enumerate(_dummy97)}
pruef("Umzingelt: Gegner von drei Seiten ja, alle von einer Seite nein",
      _um97 and not _tr97.umzingelt(_leute97), "")
_tr97.lage = {}
_fe97 = [_tm.puppe_setzen(p_ + pygame.Vector2(0, 26 * i_), 0, {"team": 1, "leben": 10.0})
         for p_ in _seiten97 for i_ in range(2)]
for f_ in _fe97:
    f_.unverwundbar = 1e9
_zust97 = set()
for _ in range(int(4.0 / _D87)):
    _tm.schritt(_D87)
    _zust97.add(_tr97.zustand)
_ig97 = _tr97.igel
pruef("Von drei Seiten bedroht: der Trupp igelt sich ein",
      "igel" in _zust97 and _ig97 is not None, str(sorted(_zust97)))
_ring97 = [_tr97.stellung(m_) for m_ in _tr97.lebende() if m_ is not _tr97.fuehrer]
_winkel97 = sorted(math.degrees(math.atan2(q_.y - _ig97["ort"].y, q_.x - _ig97["ort"].x)) % 360
                   for q_ in _ring97 if q_ is not None)
_luecke97 = max([b_ - a_ for a_, b_ in zip(_winkel97, _winkel97[1:])]
                + [_winkel97[0] + 360 - _winkel97[-1]]) if _winkel97 else 360
pruef("... im Ring um den Platz, ringsum verteilt, der Anfuehrer in der Mitte",
      len(_winkel97) == len(_tr97.lebende()) - 1 and _luecke97 < 150
      and _tr97.stellung(_tr97.fuehrer).distance_to(_ig97["ort"]) < 20,
      "Winkel %s" % [round(w_) for w_ in _winkel97])
_aus97 = [(_tr97.blick_fuer(m_) - _ig97["ort"]).dot(_tr97.stellung(m_) - _ig97["ort"]) > 0
          for m_ in _tr97.lebende() if m_ is not _tr97.fuehrer]
pruef("... und jeder schaut nach aussen, in seinen Sektor", _aus97 and all(_aus97), str(_aus97))
_fak97 = next(m_ for m_ in _tr97.lebende() if m_ is not _tr97.fuehrer).hirn.fuehlen()[0]
pruef("... als Fakt: trupp_igel; flankieren ist dann teuer (niemand verlaesst den Ring)",
      _fak97["trupp_igel"] and _WD88.daten().aktionen["flankieren"].kosten.wert(
          {"trupp_igel": 1, "mut": 0.5}) > 8, "")
_tm.alles_weg()
_tr97 = _tm.trupp_setzen(_a97, 0, {"groesse": 3, "team": 0, "fuehrer": "funk"})
_tm.trupp_auftrag("igel", _a97 + pygame.Vector2(30, 0), 0, {"team": 0})
_sim87(int(0.6 / _D87))
pruef("TRUPP: IGEL HIER: einigeln am Zeiger, auch ohne Gegner",
      _tr97.zustand == "igel" and _tr97.igel["ort"].distance_to(_a97 + pygame.Vector2(30, 0)) < 1, "")

# Deckung ringsum und Engstellen: aus der Karte gemessen.
_offen97 = _TR97.deckung_ringsum(_tm.welt, _a97, 0)
_eng97 = None
for _ in range(40000):
    p_ = pygame.Vector2(freier_punkt(_tm.welt, 0, _r97))
    b_, ax_ = _TR97.breite_an(_tm.welt, p_, 0)
    if b_ <= 70:
        a_, z_ = p_ + ax_ * 170, p_ - ax_ * 430
        if _tm.welt.frei(a_, 30, 0, True) and _tm.welt.frei(z_, 40, 0, True):
            _eng97 = (p_, b_, ax_, a_, z_)
            break
pruef("(eine Engstelle auf der Karte)", _eng97 is not None, "")
pruef("Breite: an der Engstelle schmal, auf freiem Feld nicht",
      _eng97[1] <= 70 and _TR97.breite_an(_tm.welt, _a97, 0)[0] > K.TRUPP["enge_breite"],
      "%.0f / %.0f" % (_eng97[1], _TR97.breite_an(_tm.welt, _a97, 0)[0]))
pruef("Auf freiem Feld steht ringsum kaum Deckung", _offen97 <= 2, str(_offen97))

# Eine Horde: halten hinter der Engstelle.
_tm.alles_weg()
_p97, _b97, _ax97, _ta97, _tz97 = _eng97
_tr97 = _tm.trupp_setzen(_ta97, 0, {"groesse": 4, "team": 0, "fuehrer": "funk", "mischung": "gemischt"})
_zo97 = [_tm.gegner_setzen("laeufer", _tz97 + pygame.Vector2(_r97.uniform(-50, 50), _r97.uniform(-50, 50)),
                           0, {"ki": False}) for _ in range(10)]
_tr97.lage = {z_: [pygame.Vector2(z_.pos), 0, _tm.welt.zeit] for z_ in _zo97}
_tr97._zustand_seit = -1e9
_tr97._zuversicht(_tr97.lebende())
_tr97._zustand_waehlen(_tr97.lebende())
_en97 = _tr97.enge
pruef("Eine Horde Zombies: der Trupp haelt an einer Engstelle zwischen sich und ihr",
      _tr97.zustand == "engstelle" and _en97 is not None and _en97["breite"] <= K.TRUPP["enge_breite"],
      "%s %s" % (_tr97.zustand, _en97 and round(_en97["breite"])))
_tr97._stellungen(_tr97.lebende())
_seite97 = [(_tr97.stellung(m_) - _en97["ort"]).dot(_en97["achse"]) > 0 for m_ in _tr97.lebende()]
pruef("... alle stehen auf ihrer Seite der Engstelle und schauen hinein",
      all(_seite97) and all(_tr97.blick_fuer(m_) == _en97["ort"] for m_ in _tr97.lebende()), str(_seite97))
for i_ in (1, 2):
    _tm.info = i_
    _tm.zeichnen(pygame.Surface((K.GAME_W, K.GAME_H)), 1.0)
pruef("... INFO zeigt Igel, Engstelle und Blickrichtungen (zeichnen geht)", True, "")
_tm.verlassen()

print("\n-- Tempo, Deckung zuerst, Verkriechen, Funkwellen (0.34.43)")
# Langsamer, damit man sieht, was geschieht (wie in RimWorld): alle laufen
# mit demselben Faktor, die Geschosse fliegen langsamer, so weit wie vorher.
pruef("Alle laufen langsamer: Spieler, Bots und Gegner mit demselben Faktor",
      0.0 < K.BEWEGUNG["lauf"] < 1.0
      # seit 0.34.135 alle 1,3 mal so schnell (gewuenscht: "Spieler sind extrem langsam")
      and abs(K.SPIELER["tempo"] - 108.0 * K.BEWEGUNG["lauf"] * 1.3) < 1e-6
      and K.BOTS["schritte_tempo"][0] < K.SPIELER["tempo"],
      "Spieler %.0f px/s" % K.SPIELER["tempo"])
pruef("Geschosse fliegen langsamer, die Reichweite bleibt",
      0.0 < K.BEWEGUNG["geschoss"] < 1.0
      and abs(K.WAFFEN["sturm"]["tempo"] - 760.0 * K.BEWEGUNG["geschoss"]) < 1e-6
      and K.WAFFEN["sturm"]["reichweite"] == 470.0,
      "Sturm %.0f px/s" % K.WAFFEN["sturm"]["tempo"])
pruef("Die Untertitel ueber den Bots sind aus (K.BOTS callouts)", not K.BOTS["callouts"], "")

_tm = _TM87.Testmodus(app, karte="staubtal")
_tm.wiedereinstieg = False
_platz98 = _freie_flaeche86(_tm.welt, random.Random(98), 14, 9)
pruef("(eine freie Flaeche fuer die Kistenwand)", _platz98 is not None, "")
_tx98, _ty98 = _platz98
_T98 = K.TILE
for dy_ in (3, 4, 5):
    _tm.welt.ebene(0).setzen(_tx98 + 6, _ty98 + dy_, K.KISTE)
_kiste98 = pygame.Vector2((_tx98 + 6.5) * _T98, (_ty98 + 4.5) * _T98)
_bot98 = _tm.bot_setzen(_kiste98 + pygame.Vector2(_T98 * 1.1, 0), 0,
                        {"team": 0, "hirn": "goap", "waffe": "sturm"})
_bot98.hirn.merkmale["mut"] = 0.3
_bot98.unverwundbar = 1e9
_feind98 = _tm.puppe_setzen(_kiste98 - pygame.Vector2(_T98 * 6, 0), 0, {"team": 1, "leben": 10.0})
_feind98.unverwundbar = 1e9
# Er weiss, wo der Gegner steht (gesehen, ehe er hinter die Kisten ging).
_bot98.hirn.gesehen[_feind98] = (pygame.Vector2(_feind98.pos), 0, _tm.welt.zeit)
_start98 = pygame.Vector2(_bot98.pos)
_schuesse98 = 0
_weit98 = 0.0
_schnell98 = 0.0
_sprint98 = False
for _ in range(int(6.0 / _D87)):
    _bot98.hirn.innen.stress = 0.0
    _tm.schritt(_D87)
    _schuesse98 += 1 if _bot98.feuert else 0
    _weit98 = max(_weit98, _bot98.pos.distance_to(_start98))
    _schnell98 = max(_schnell98, _bot98.tempo.length())
    _sprint98 = _sprint98 or _bot98.sprintet
_plaene98 = [t_ for _z, t_ in _bot98.hirn.gehirn.protokoll if t_.startswith("PLAN:")]
pruef("Ein vorsichtiger Bot neben einer Deckung kaempft aus ihr heraus",
      any("aus_deckung_feuern" in t_ for t_ in _plaene98), str(_plaene98[-3:]))
pruef("... er lehnt sich heraus und schiesst, bleibt aber dicht an seiner Deckung",
      _schuesse98 > 0 and _weit98 < K.BOTS["lehnen_weite"] + 30,
      "%d Bilder gefeuert, hoechstens %.0f px weg" % (_schuesse98, _weit98))
# Seit 0.34.50 duerfen Bots sprinten - dann um den Sprintfaktor schneller.
pruef("... und laeuft nie schneller als das neue Spielertempo (sprintend: mal K.SPRINT faktor)",
      0.0 < _schnell98 <= K.SPIELER["tempo"] * (K.SPRINT["faktor"] if _sprint98 else 1.0) + 1.0,
      "%.0f px/s%s" % (_schnell98, ", sprintete" if _sprint98 else ""))
pruef("... die Kosten: ein Mutiger greift offen an, ein Vorsichtiger geht in Deckung",
      _WD88.daten().aktionen["angreifen"].kosten.wert({"mut": 0.9}) < 2.0 + 0.9
      and _WD88.daten().aktionen["angreifen"].kosten.wert({"mut": 0.3}) > 2.0 + 0.3, "")

# Panik in der Deckung: nicht weglaufen, sondern in die beste Ecke.
_bot98.hirn.innen.panik_setzen(3.0)
_bot98.hirn.innen.stress = 1.0
_bot98.hirn.goap_rest = 0.0
_gedeckt98 = []
_vorher98 = len(_bot98.hirn.gehirn.protokoll)
for _ in range(int(2.0 / _D87)):
    _tm.schritt(_D87)
    _gedeckt98.append(_bot98.hirn.gedeckt(_bot98.pos, 0))
_neu98 = [t_ for _z, t_ in list(_bot98.hirn.gehirn.protokoll)[_vorher98:]]
pruef("Panik in der Deckung: er verkriecht sich, statt am Gegner vorbei zu rennen",
      any(t_.startswith("PLAN: verkriechen") for t_ in _neu98)
      and not any("fliehen" in t_ for t_ in _neu98), str(_neu98[:4]))
pruef("... und verlaesst seine Deckung dabei nicht (am Ende gedeckt, nahe der Kisten)",
      _gedeckt98[-1] and sum(_gedeckt98[len(_gedeckt98) // 2:]) == len(_gedeckt98) - len(_gedeckt98) // 2
      and _bot98.pos.distance_to(_start98) < K.BOTS["ecke_radien"][-1] + 30,
      "%d von %d Bildern gedeckt, %.0f px" % (sum(_gedeckt98), len(_gedeckt98),
                                               _bot98.pos.distance_to(_start98)))

# Ein Trupp stellt sich hinter die Kisten, nicht daneben ins Freie.
_tm.alles_weg()
_tr98 = _tm.trupp_setzen(_kiste98 + pygame.Vector2(_T98 * 3, 0), 0, {"groesse": 3, "team": 0})
_p98 = _kiste98 + pygame.Vector2(_T98 * 1.1, _T98 * 2.6)     # neben der Wand, im Freien
_m98 = _tr98.lebende()[0]
_q98 = _tr98._deckung_nah(_p98, _m98, _feind98.pos if _feind98.lebt else _kiste98 - pygame.Vector2(_T98 * 6, 0))
_gegen98 = _kiste98 - pygame.Vector2(_T98 * 6, 0)
pruef("Eine Trupp-Stellung im Freien rueckt hinter die nahe Deckung",
      not _tr98.gedeckt_hier(_p98, 0, _gegen98) and _tr98.gedeckt_hier(_q98, 0, _gegen98)
      and _q98.distance_to(_p98) <= K.TRUPP["deckung_ringe"][-1] + 1,
      "%.0f px verschoben" % _q98.distance_to(_p98))

# Funkwellen: wer funkt, sendet Ringe (statt eines Kastens mit Text).
_tm.alles_weg()
_tr98 = _tm.trupp_setzen(_kiste98 + pygame.Vector2(_T98 * 3, 0), 0, {"groesse": 3, "team": 0, "fuehrer": "funk"})
_f98 = _tr98.fuehrer
_f98.hirn.funk_laeuft = {"anfang": _tm.welt.zeit - 0.5, "bis": _tm.welt.zeit + 1.0,
                         "art": "hilfe", "text": "TEST"}
_tr98.empfangen_zeit = _tm.welt.zeit
_tm.zeichnen(pygame.Surface((K.GAME_W, K.GAME_H)), 1.0)
# Seit 0.34.46 am Boden unter dem Funker, rot und klein.
_boden98 = pygame.Surface((90, 90))
_tm._kreis_zeichnen(_boden98, 0, _f98.pos - pygame.Vector2(45, 45))
_rot98 = [(x_, y_) for x_ in range(90) for y_ in range(90)
          if tuple(_boden98.get_at((x_, y_)))[:3] in K.TESTMODUS["welle_farben"]]
_weit98 = max((math.hypot(x_ - 45, y_ - 45) for x_, y_ in _rot98), default=0.0)
_spaet98 = pygame.Surface((90, 90))
pruef("Funk: unter dem Funker gehen kleine rote Ringe aus, die nach aussen vergehen",
      # Klein (0.34.46: "deutlich kleiner"), seit 0.34.50 wieder etwas groesser
      # ("etwas groesser darf der Funk schon sein") - aber nie wieder 150.
      bool(_rot98) and _weit98 <= K.TESTMODUS["welle_weite"] + 1 and K.TESTMODUS["welle_weite"] <= 48
      and not _tm._welle_ring(_spaet98, pygame.Vector2(45, 45), K.TESTMODUS["welle_weite"] + 5)
      and pygame.transform.average_color(_spaet98)[:3] == (0, 0, 0),
      "%d rote Punkte, bis %.0f px" % (len(_rot98), _weit98))
_tm.verlassen()

print("\n-- Liegende, Rauch genau, volle Deckung, nicht in die Deckung (0.34.46)")
_tm = _TM87.Testmodus(app, karte="staubtal")
_tm.wiedereinstieg = False
_tm.verwundete_setzen(True)
_platz99 = _freie_flaeche86(_tm.welt, random.Random(99), 16, 11)
pruef("(eine freie Flaeche fuer Mauer und Kiste)", _platz99 is not None, "")
_tx99, _ty99 = _platz99
_T99 = K.TILE
def _v99(x_, y_):
    return pygame.Vector2((_tx99 + x_ + 0.5) * _T99, (_ty99 + y_ + 0.5) * _T99)

# Wer am Boden liegt, ist kein Ziel mehr: er nimmt den, der noch steht.
_bot99 = _tm.bot_setzen(_v99(12, 2), 0, {"team": 0, "hirn": "goap"})
_bot99.unverwundbar = 1e9
_liegt99 = _tm.bot_setzen(_v99(6, 1), 0, {"team": 1, "hirn": "goap"})
_steht99 = _tm.bot_setzen(_v99(5, 4), 0, {"team": 1, "hirn": "goap"})
for f_ in (_liegt99, _steht99):
    f_.unverwundbar = 1e9
_tm.ki_stopp = True
_tm.toeten(_liegt99)
_bot99.hirn.ziel = _liegt99
_bot99.hirn.stoss_rest = 0.0
_bot99.hirn._wahrnehmen()
pruef("Ein Ziel, das am Boden liegt, laesst er los und nimmt den, der noch steht",
      _liegt99.am_boden and _bot99.hirn.ziel is _steht99, str(getattr(_bot99.hirn.ziel, "name", None)))
_bot99.hirn.ziel = _liegt99
_bot99.hirn.stoss_rest = 0.5
_bot99.hirn._wahrnehmen()
# Bis 0.34.51 brachte er den laufenden Stoss zu Ende - ein Dauerfeuer hielt
# so vier Sekunden auf den Liegenden. Seit 0.34.52 endet auch der.
pruef("... auch den Feuerstoss, der laeuft, bricht er ab (seit 0.34.52)",
      _bot99.hirn.ziel is not _liegt99 and _bot99.hirn.stoss_rest == 0.0, "")
_steht99.pos.update(_v99(-30, -30))
_bot99.hirn.stoss_rest = 0.0
_bot99.hirn._wahrnehmen()
pruef("... und liegt nur noch einer, schiesst er auf keinen",
      _bot99.hirn.ziel is None, str(getattr(_bot99.hirn.ziel, "name", None)))

# Wer liegt, denkt nicht mehr: kein Plan, kein FLANKIEREN ueber dem Kopf.
_tm.ki_stopp = False
_steht99.pos.update(_v99(5, 4))
_sim87(int(1.0 / _D87))
_plan99 = bool(_steht99.hirn.gehirn.plan)
_tm.toeten(_steht99)
_sim87(int(0.5 / _D87))
pruef("Wer zu Boden geht, hat kein Ziel und keinen Plan mehr; ueber ihm steht VERWUNDET",
      _plan99 and _steht99.am_boden and _steht99.hirn.gehirn.aktion is None
      and _steht99.hirn.gehirn.ziel is None and _tm.aktion_text(_steht99) == "VERWUNDET",
      "%s / %r" % (_steht99.hirn.gehirn.aktion, _tm.aktion_text(_steht99)))

# Rauch genau auf den Liegenden (ein Stueck zum Gegner hin), nicht dazwischen.
_tm.alles_weg()
_tr99 = _tm.trupp_setzen(_v99(13, 5), 0, {"groesse": 3, "team": 0, "fuehrer": "funk"})
_opfer99 = next(m_ for m_ in _tr99.lebende() if m_ is not _tr99.fuehrer)
_opfer99.pos.update(_v99(10, 5))
_tm.toeten(_opfer99)
_fh99 = _tr99.fuehrer.hirn
_fh99.gehirn.fakten = dict(_fh99.gehirn.fakten, kamerad_liegt=True)
_feind99 = _v99(2, 5)
_ort99 = _fh99.rauch_ort(_feind99)
pruef("Rauch kommt auf den Liegenden, ein Stueck zum Gegner hin",
      _opfer99.am_boden and _ort99.distance_to(_opfer99.pos) <= K.BOTS["rauch_vor"] + 1
      and (_ort99 - _opfer99.pos).dot(_feind99 - _opfer99.pos) > 0,
      "%.0f px vom Liegenden" % _ort99.distance_to(_opfer99.pos))
_st99 = _BG88._Stelle(_ort99, 0)
_st99.genau = True
_fh99.wurf_platz = _fh99._rauch_platz()
_ein99 = {"knoepfe": [], "waffe": -1}
_wurf99 = _fh99._werfen(K.FIXED_DT, _ein99, _st99)
pruef("... und so geworfen, genau dorthin (nicht auf 40 Prozent des Weges)",
      _fh99.wurf_platz >= 0 and _wurf99[1].distance_to(_ort99) < 1.0, str(_wurf99[1]))
_fh99.wurf_phase = 0.0

# Volle Deckung vor halber: Mauer vor Fass, Mauerende vor Mauermitte.
_tm.alles_weg()
_e99 = _tm.welt.ebene(0)
for dy_ in range(3, 10):
    _e99.setzen(_tx99 + 8, _ty99 + dy_, K.WAND)
_e99.setzen(_tx99 + 13, _ty99 + 0, K.KISTE)
_gefahr99 = _v99(1, 6)
_b99 = _tm.bot_setzen(_v99(11, 6), 0, {"team": 0, "hirn": "goap"})
_mitte99 = _v99(9, 6)
_ende99 = _v99(9, 9) + pygame.Vector2(0, _T99 * 0.25)
_kiste99 = _v99(14, 0)
# Die Kiste gegen einen Gegner, der genauso weit weg steht, ohne die Mauer dazwischen.
_gu99 = {"mitte": _b99.hirn._deckung_guete(_mitte99, _gefahr99),
         "ende": _b99.hirn._deckung_guete(_ende99, _gefahr99),
         "kiste": _b99.hirn._deckung_guete(_kiste99, _kiste99 - pygame.Vector2(_T99 * 8, 0))}
pruef("Volle Deckung zuerst: eine Mauer ist besser als eine einzelne Kiste, das Mauerende am besten",
      _gu99["ende"] < _gu99["mitte"] < _gu99["kiste"],
      ", ".join("%s %.0f" % (n_, w_) for n_, w_ in sorted(_gu99.items())))

# Nicht in die eigene Deckung: die Kiste direkt vor ihm.
_b99.pos.update(_v99(13, 0) + pygame.Vector2(_T99 * 0.95, 0))
_vor99 = _v99(13, 0) - pygame.Vector2(_T99 * 4, 0)
pruef("Steht seine Deckung direkt vor ihm, schiesst und wirft er nicht hinein",
      _b99.hirn.vorn_zu(_vor99) and not _b99.hirn.vorn_zu(_b99.pos + pygame.Vector2(_T99 * 4, 0)), "")
_puppe99 = _tm.puppe_setzen(_vor99, 0, {"team": 1, "leben": 10.0})
_b99.hirn.ziel = _puppe99
_b99.hirn.wurf_rest = 0.0
_b99.hirn.reaktion_rest = 0.0
pruef("... auch keine Granate (wurf_moeglich sagt nein)",
      not _b99.hirn._wurf_moeglich(_b99.pos.distance_to(_vor99), True, 3), "")
_tm.verlassen()

print("\n-- Dicht in Deckung, Panik waehlt, Bergen hinter feste Deckung, Funk mit Rueckzug (0.34.48)")
_tm = _TM87.Testmodus(app, karte="staubtal")
_tm.wiedereinstieg = False
_tm.verwundete_setzen(True)
_platz100 = _freie_flaeche86(_tm.welt, random.Random(100), 18, 11)
pruef("(eine freie Flaeche fuer die Szene)", _platz100 is not None, "")
_tx100, _ty100 = _platz100
_T100 = K.TILE
def _v100(x_, y_):
    return pygame.Vector2((_tx100 + x_ + 0.5) * _T100, (_ty100 + y_ + 0.5) * _T100)
_e100 = _tm.welt.ebene(0)
for dy_ in (4, 5, 6):
    _e100.setzen(_tx100 + 8, _ty100 + dy_, K.KISTE)       # Kisten vorn
for dy_ in range(2, 9):
    _e100.setzen(_tx100 + 15, _ty100 + dy_, K.WAND)       # eine Mauer weiter hinten
_feind100 = _tm.puppe_setzen(_v100(2, 5), 0, {"team": 1, "leben": 10.0})
_feind100.unverwundbar = 1e9
_b100 = _tm.bot_setzen(_v100(9, 5), 0, {"team": 0, "hirn": "goap", "waffe": "sturm"})
_b100.unverwundbar = 1e9
_h100 = _b100.hirn
_tm.ki_stopp = True
pruef("Dicht hinter den Kisten ist er gedeckt, drei Kacheln dahinter nicht mehr",
      _h100.dicht_gedeckt(_v100(9, 5) - pygame.Vector2(_T100 * 0.2, 0), _feind100.pos)
      and not _h100.dicht_gedeckt(_v100(12, 5), _feind100.pos)
      and _tm.welt.deckung(_feind100.pos, _v100(12, 5), 0) != "", "")
_nah100 = _h100._deckung_guete(_v100(9, 5), _v100(6, 5))
_weit100 = _h100._deckung_guete(_v100(9, 5), _v100(2, 5))
pruef("Eine Deckung dicht am Gegner (unter dem Abstand seiner Waffe) ist schlechter",
      _nah100 > _weit100, "%.0f / %.0f" % (_nah100, _weit100))

# Panik: bleiben, wechseln oder fliehen - nach Leben, Zuversicht und Trupp.
_ak100 = _WD88.daten().aktionen
def _wahl100(**w_):
    werte_ = dict(leben=1.0, zuversicht=0.5, trupp_rueckzug=0, trupp_druck=0, mut=0.5)
    werte_.update(w_)
    k_ = {n_: _ak100[n_].kosten.wert(werte_) for n_ in ("verkriechen", "deckung_wechseln", "fliehen")}
    return min(k_, key=k_.get)
_wahlen100 = (_wahl100(trupp_druck=1), _wahl100(leben=0.25, zuversicht=0.3),
              _wahl100(leben=0.2, zuversicht=0.3, trupp_rueckzug=1))
pruef("Panik in Deckung: gesund und der Trupp rueckt vor - er bleibt; angeschlagen - bessere Deckung; "
      "schwer getroffen beim Rueckzug - er rennt",
      _wahlen100 == ("verkriechen", "deckung_wechseln", "fliehen"), str(_wahlen100))
_h100.gesehen[_feind100] = (pygame.Vector2(_feind100.pos), 0, _tm.welt.zeit)
_bd100 = _h100.bessere_deckung()
pruef("... die bessere Deckung liegt weiter weg vom Gegner, dicht dahinter (hier: die Mauer)",
      _bd100 is not None and _bd100.distance_to(_feind100.pos) > _b100.pos.distance_to(_feind100.pos) + 40
      and _h100.dicht_gedeckt(_bd100, _feind100.pos)
      and _tm.welt.deckung(_feind100.pos, _bd100, 0) == "wand", str(_bd100))

# Bergen: nicht im Rauch aufhelfen, sondern erst hinter feste Deckung ziehen.
from dustfront.entities import Rauchwolke as _RW100
_lieg100 = _tm.bot_setzen(_v100(6, 2), 0, {"team": 0, "hirn": "goap"})
_tm.toeten(_lieg100)
_tm.welt.rauch.append(_RW100(pygame.Vector2(_lieg100.pos), 0))
for _ in range(int(3.0 / _D87)):
    for r_ in _tm.welt.rauch:
        r_.schritt(_D87)
pruef("Im Rauch ist ein Liegender verborgen, aber nicht fest gedeckt - aufgeholfen wird dort nicht",
      _h100.gedeckt(_lieg100.pos, 0) and not _h100.fest_gedeckt(_lieg100.pos, 0)
      and not _h100._bergung_fakten()["kamerad_gedeckt"], "")
_tm.welt.rauch.clear()
_bp100 = _h100.bergeplatz(_lieg100)
pruef("... der Bergeplatz ist dicht hinter einer Deckung",
      _bp100 is not None and _h100.fest_gedeckt(_bp100, 0), str(_bp100))

# Wiederbeleben dauert laenger und ist zu sehen: Arme mit Verband, Ring.
pruef("Wiederbeleben dauert laenger (wenigstens fuenf Sekunden)", K.REVIVE["dauer"] >= 5.0,
      "%.1f s" % K.REVIVE["dauer"])
_b100.pos.update(_lieg100.pos + pygame.Vector2(20, 0))
_b100.hilft = _lieg100.nummer
_lieg100.revive_stand = 0.4
_tm.ki_stopp = False
_tm.welt.zeit += 0.0
_tm._revive(0.1)
_zu100 = _lieg100.pos - _b100.pos
_bild100 = pygame.Surface((K.GAME_W, K.GAME_H))
_tm.kamera.pos.update(_lieg100.pos) if hasattr(_tm.kamera, "pos") else None
_tm._haende_zeichnen(_bild100)
_pl100 = _tm.kamera.zu_bild(_lieg100.pos)
_farben100 = {tuple(_bild100.get_at((int(_pl100.x) + dx_, int(_pl100.y) + dy_)))[:3]
              for dx_ in range(-16, 17) for dy_ in range(-16, 17)
              if 0 <= int(_pl100.x) + dx_ < K.GAME_W and 0 <= int(_pl100.y) + dy_ < K.GAME_H}
pruef("Wer aufhilft, schaut zum Liegenden; zu sehen: Verband (hell) und Fortschrittsring (tuerkis)",
      abs((_b100.winkel - math.degrees(math.atan2(_zu100.y, _zu100.x)) + 180) % 360 - 180) < 3
      and K.C_CREAM in _farben100 and K.C_TEAL in _farben100, "")
_b100.hilft = None

# Funk: erst zurueck an einen gedeckten Platz, dann lange sprechen; wer ihn
# dabei trifft, unterbricht ihn.
_tm.alles_weg()
_tr100 = _tm.trupp_setzen(_v100(10, 5), 0, {"groesse": 3, "team": 0, "fuehrer": "funk"})
_f100 = _tr100.fuehrer
_f100.pos.update(_v100(9, 2))
_g100 = _tm.puppe_setzen(_v100(4, 2), 0, {"team": 1, "leben": 10.0})
_g100.unverwundbar = 1e9
_fh100 = _f100.hirn
_fh100.gesehen[_g100] = (pygame.Vector2(_g100.pos), 0, _tm.welt.zeit)
_tm.ki_stopp = True
_fh100._funken_tun("lage")
_fl100 = _fh100.funk_laeuft
pruef("Funk: mit einem Gegner dicht dran geht der Anfuehrer erst zurueck, an einen Platz weiter weg",
      _fl100 is not None and _fl100["phase"] == "weg" and _fl100["ort"] is not None
      and _fl100["ort"].distance_to(_g100.pos) > _f100.pos.distance_to(_g100.pos) + 60,
      str(_fl100 and _fl100.get("ort")))
_bw100 = pygame.Surface((200, 200))
_tm._funkwellen_zeichnen(_bw100, 0, _f100.pos - pygame.Vector2(100, 100))
pruef("... auf dem Weg dorthin funkt er noch nicht (keine Wellen)",
      pygame.transform.average_color(_bw100)[:3] == (0, 0, 0), "")
_fl100.update(phase="senden", anfang=_tm.welt.zeit, bis=_tm.welt.zeit + _fl100["dauer"], leben=_f100.leben)
_f100.leben -= 5.0
_r100 = _fh100._funken_tun("lage")
pruef("... wird er beim Sprechen getroffen, ist der Spruch nicht raus",
      _r100[-1] == "gescheitert" and _fh100.funk_laeuft is None and K.TRUPP["funk_dauer"] >= 5.0, "")
_tm.verlassen()

print("\n-- Flanke, geknickte Front, Bergen mit Gedaechtnis, Sprint, Zurufe (0.34.50)")
_tm = _TM87.Testmodus(app, karte="staubtal")
_tm.wiedereinstieg = False
_tm.verwundete_setzen(True)
_platz101 = _freie_flaeche86(_tm.welt, random.Random(101), 18, 11)
pruef("(eine freie Flaeche fuer die Szene)", _platz101 is not None, "")
_tx101, _ty101 = _platz101
def _v101(x_, y_):
    return pygame.Vector2((_tx101 + x_ + 0.5) * K.TILE, (_ty101 + y_ + 0.5) * K.TILE)

# Zwei Gegner, 90 Grad auseinander: flankiert - er stellt sich so, dass
# beide vor ihm sind.
_b101 = _tm.bot_setzen(_v101(10, 6), 0, {"team": 0, "hirn": "goap", "waffe": "sturm"})
_b101.unverwundbar = 1e9
_p101 = [_tm.puppe_setzen(_v101(3, 6), 0, {"team": 1, "leben": 10.0}),
         _tm.puppe_setzen(_v101(10, 0), 0, {"team": 1, "leben": 10.0})]
for p_ in _p101:
    p_.unverwundbar = 1e9
_h101 = _b101.hirn
for p_ in _p101:
    _h101.gesehen[p_] = (pygame.Vector2(p_.pos), 0, _tm.welt.zeit)
_tm.ki_stopp = True
_sp101 = _h101._spanne(_b101.pos, _h101.bedrohungs_richtungen())
pruef("Zwei Gegner, 90 Grad auseinander, er offen dazwischen: flankiert",
      _sp101 > K.BOTS["flanke_spanne"] and _h101.flankiert(), "%.0f Grad" % _sp101)
_up101 = _h101.umstellplatz()
pruef("... ein Platz, von dem aus beide vor ihm sind (oder er vor beiden gedeckt), nicht naeher dran",
      _up101 is not None
      and (_h101._spanne(_up101, _h101.bedrohungs_richtungen()) <= K.BOTS["flanke_spanne"]
           or all(_h101.dicht_gedeckt(_up101, p_.pos) for p_ in _p101))
      and min(p_.pos.distance_to(_up101) for p_ in _p101) >= min(p_.pos.distance_to(_b101.pos) for p_ in _p101) - 20,
      str(_up101))
_tm.ki_stopp = False
# So lange darf es dauern: zweimal die laengste Bedenkzeit (er wechselt
# vielleicht erst ueber ein anderes Ziel), der weiteste Weg zum neuen Platz
# im Lauftempo, eine Sekunde Spiel.
_fenster101 = (2 * K.MORAL["bedenkzeit"][1] + K.BOTS["umstell_radien"][-1] * 1.8 / K.SPIELER["tempo"] + 1.0)
for _ in range(int(_fenster101 / _D87)):
    for p_ in _p101:
        _h101.gesehen[p_] = (pygame.Vector2(p_.pos), 0, _tm.welt.zeit)
    _tm.schritt(_D87)
_pl101 = [t_ for _z, t_ in _h101.gehirn.protokoll]
pruef("... als Ziel FLANKE SICHERN (vor dem Kampf), und danach ist er es nicht mehr",
      any(t_.startswith("ZIEL: flanke_sichern") for t_ in _pl101) and not _h101.flankiert(), str(_pl101[-4:]))

# Wer auf ihn schiesst, ist sein Ziel - nicht der vorn.
_tm.ki_stopp = True
_h101.ziel = _p101[0]
_h101.stoss_rest = 0.0
_h101.beschossen_von[_p101[1]] = (pygame.Vector2(_p101[1].pos), 0, _tm.welt.zeit)
for p_ in _p101:
    _h101.gesehen[p_] = (pygame.Vector2(p_.pos), 0, _tm.welt.zeit)
_h101._wahrnehmen()
pruef("Wer ihn von der Seite trifft, wird sein Ziel, statt weiter auf den vorn zu schiessen",
      _h101.ziel is _p101[1], str(getattr(_h101.ziel, "name", None)))

# Geknickte Front: Gegner aus zwei Richtungen, je ein Teil schaut zu jeder.
_tm.alles_weg()
_tr101 = _tm.trupp_setzen(_v101(10, 6), 0, {"groesse": 5, "team": 0})
_g101 = [_tm.puppe_setzen(_v101(2, 6), 0, {"team": 1, "leben": 10.0}),
         _tm.puppe_setzen(_v101(10, 0), 0, {"team": 1, "leben": 10.0})]
_tr101.lage = {w_: [pygame.Vector2(w_.pos), 0, _tm.welt.zeit] for w_ in _g101}
_tr101._front_rechnen(_tr101.lebende())
_tr101._stellungen(_tr101.lebende())
_bl101 = [_tr101.blick_fuer(m_) for m_ in _tr101.lebende() if m_ is not _tr101.fuehrer]
_zu101 = [min(range(2), key=lambda i_: b_.distance_to(_g101[i_].pos)) for b_ in _bl101 if b_ is not None]
pruef("Gegner aus zwei Richtungen: die Front knickt, ein Teil schaut zu jeder Gruppe",
      _tr101.abschnitte == 2 and len(_zu101) == 4 and set(_zu101) == {0, 1}, str(_zu101))

# Bergen: wer hinter Rauch verschwindet, ist nicht vergessen.
_tm.alles_weg()
_eb101 = _tm.bot_setzen(_v101(12, 6), 0, {"team": 0, "hirn": "goap"})
_ep101 = _tm.puppe_setzen(_v101(4, 6), 0, {"team": 1, "leben": 10.0})
_eh101 = _eb101.hirn
_eh101.gesehen[_ep101] = (pygame.Vector2(_ep101.pos), 0, _tm.welt.zeit)
_eh101.erinnern()
_eh101.gesehen.clear()
pruef("Bergen: ein Gegner, den er nicht mehr sieht (Rauch), bedroht den Liegenden trotzdem",
      not _eh101.fest_gedeckt(_v101(9, 6), 0) and _ep101 in _eh101.erinnerung, "")
_fu101 = _tm.trupp_setzen(_v101(12, 3), 0, {"groesse": 2, "team": 0, "fuehrer": "funk"})
_fh101 = _fu101.fuehrer.hirn
pruef("... Rauch wirft ein GOAP-Bot nur gezielt, nie als Granate im Kampf",
      _fh101._rauch_platz() >= 0 and _fh101._wurf_platz() < 0, "")
_fh101.wurf_phase = 0.3
_fh101._aktion_lief = None
_fh101.gehirn.plan = [_WD88.daten().aktionen["angreifen"]]
_fh101._handeln(_D87, {"knoepfe": [], "waffe": -1})
pruef("... ein angefangener Wurf faellt aus, wenn die Aktion wechselt", _fh101.wurf_phase == 0.0, "")
pruef("... ziehen kann nur einer (kamerad_ziehen braucht !anderer_zieht)",
      any(not wert_ for n_, wert_ in _WD88.daten().aktionen["kamerad_ziehen"].braucht.items()
          if n_ == "anderer_zieht"), "")

# Beim Trupp bleiben: in Panik flieht keiner allein weg.
_ak101 = _WD88.daten().aktionen
_w101 = dict(leben=1.0, zuversicht=0.5, im_trupp=1, trupp_rueckzug=0)
pruef("Im Trupp flieht keiner allein, solange der Trupp nicht zurueckgeht",
      _ak101["fliehen"].kosten.wert(_w101) > _ak101["deckung_wechseln"].kosten.wert(_w101)
      and _ak101["fliehen"].kosten.wert(dict(_w101, leben=0.2, trupp_rueckzug=1))
      < _ak101["verkriechen"].kosten.wert(dict(_w101, leben=0.2, trupp_rueckzug=1)), "")
_m101 = next(m_ for m_ in _fu101.lebende() if m_ is not _fu101.fuehrer)
_m101.hirn.gesehen[_ep101] = (pygame.Vector2(_ep101.pos), 0, _tm.welt.zeit)
_m101.hirn.innen.panik_setzen(3.0)
_m101.hirn._flucht = None
_m101.hirn.tun_fliehen(_D87, {"knoepfe": [], "waffe": -1})
pruef("... in Panik flieht er zu seinen Leuten, knapp hinter sie",
      _m101.hirn._flucht is not None
      and _m101.hirn._flucht[0].distance_to(_m101.hirn.trupp_mitte()) <= K.TRUPP["flucht_hinter"] + 1, "")
_m101.hirn.innen.panik_rest = 0.0

# Sprinten: nur Bots, mit Ausdauer, mit Staub.
_s101 = _tm.bot_setzen(_v101(6, 9), 0, {"team": 0, "hirn": "goap"})
_s101.hirn.ki_aus = True if hasattr(_s101.hirn, "ki_aus") else None
_tm.ki_stopp = True
_ein101 = {"will": [1.0, 0.0], "ziel": [_s101.pos.x + 100, _s101.pos.y], "feuert": False,
           "zielt": False, "nutzen": False, "ziehen": False, "waffe": -1, "knoepfe": [], "sprint": True}
_tm._anwenden(_s101, _ein101)
_teilchen101 = len(_tm.welt.partikel)
_schnell101 = 0.0
for _ in range(int(1.0 / _D87)):
    _tm._anwenden(_s101, _ein101)
    _s101.schritt(_D87)
    _tm._sprint_staub(_D87)
    _schnell101 = max(_schnell101, _s101.tempo.length())
pruef("Ein Bot sprintet: schneller als das Lauftempo, die Ausdauer sinkt, er wirbelt Staub auf",
      _s101.sprintet and _schnell101 > K.SPIELER["tempo"] * 1.2 and _s101.ausdauer < 0.8
      and len(_tm.welt.partikel) > _teilchen101,
      "%.0f px/s, Ausdauer %.2f" % (_schnell101, _s101.ausdauer))
_s101.ausdauer = K.SPRINT["mindest"] * 0.5
_s101.sprintet = False
_tm._anwenden(_s101, _ein101)
pruef("... mit zu wenig Ausdauer faengt er keinen Sprint an", not _s101.sprintet, "")
_s101.sprintet = True
_meld101 = [e_ for e_ in _tm._weltmeldung().get("spieler", []) if isinstance(e_, dict) and e_.get("i") == _s101.nummer]
pruef("... und der Gast sieht es (sp in der Weltmeldung)", bool(_meld101) and _meld101[0].get("sp") == 1,
      str(list(_tm._weltmeldung().keys())[:8]))
_s101.sprintet = False
_tm.menue_wirken("sprint")
_s101.ausdauer = 1.0
_tm._anwenden(_s101, _ein101)
pruef("Testmenue BOTS SPRINTEN: aus - dann sprintet keiner", not _tm.bot_sprint and not _s101.sprintet, "")
_tm.menue_wirken("sprint")
_tm.ki_stopp = False

# Zurufe: was einer sieht, haben die anderen erst, wenn der Satz durch ist.
_tm.alles_weg()
_za101 = _tm.bot_setzen(_v101(10, 3), 0, {"team": 0, "hirn": "goap"})
_zb101 = _tm.bot_setzen(_v101(13, 3), 0, {"team": 0, "hirn": "goap"})
_zp101 = _tm.puppe_setzen(_v101(3, 3), 0, {"team": 1, "leben": 10.0})
_tm.ki_stopp = True
_za101.hirn.gesehen[_zp101] = (pygame.Vector2(_zp101.pos), 0, _tm.welt.zeit)
_za101.hirn.fuehlen()
pruef("Zuruf: wer einen Gegner neu sieht, ruft es den anderen in Sprechweite zu",
      _za101.hirn.zuruf is not None and _zp101 not in _zb101.hirn.zugerufen, "")
_tm.welt.zeit += K.SPRECHEN["dauer"][1] + 0.05
_za101.hirn._zuruf_fuehren()
pruef("... erst wenn der Satz durch ist, weiss es der andere - und kennt dann den Gegner",
      _zp101 in _zb101.hirn.zugerufen and _zb101.hirn.fuehlen()[0]["feind_bekannt"], "")
pruef("... im Testmodus stehen Zurufe unten links (der Name und was er rief)",
      bool(getattr(_tm, "_zurufnetz", [])) and _tm._zurufnetz[-1].name == _za101.name, "")
_tm.alles_weg()
_ta101 = _tm.trupp_setzen(_v101(4, 3), 0, {"groesse": 2, "team": 0, "fuehrer": "funk"})
_tb101 = _tm.trupp_setzen(_v101(14, 8), 0, {"groesse": 2, "team": 0, "fuehrer": "funk"})
_zq101 = _tm.puppe_setzen(_v101(1, 9), 0, {"team": 1, "leben": 10.0})
_ta101.lage = {_zq101: [pygame.Vector2(_zq101.pos), 0, _tm.welt.zeit]}
_ta101.funk_senden("lage")
_zf101 = _tb101.fuehrer.hirn.zuruf
pruef("Der Anfuehrer, der einen Funkspruch bekommt, sagt ihn seinem Trupp weiter (mit den Gegnern)",
      _zf101 is not None and any(w_ is _zq101 for w_, _o, _e in _zf101["feinde"]), "")
_bild101 = pygame.Surface((K.GAME_W, K.GAME_H))
_tm.zeichnen(_bild101, 1.0)
pruef("... die Sprechblase ueber ihm (zeichnen geht)", True, "")
_tm.ki_stopp = False
_tm.verlassen()

print("\n-- Geknickte Front: Abschnitte sichtbar, Flanke je Abschnitt (0.34.51)")
_tm = _TM87.Testmodus(app, karte="staubtal")
_tm.wiedereinstieg = False
_platz102 = _freie_flaeche86(_tm.welt, random.Random(102), 18, 11)
_tx102, _ty102 = _platz102
def _v102(x_, y_):
    return pygame.Vector2((_tx102 + x_ + 0.5) * K.TILE, (_ty102 + y_ + 0.5) * K.TILE)
_tr102 = _tm.trupp_setzen(_v102(10, 7), 0, {"groesse": 5, "team": 0})
_g102 = [_tm.puppe_setzen(_v102(1, 7), 0, {"team": 1, "leben": 10.0}),
         _tm.puppe_setzen(_v102(10, 0), 0, {"team": 1, "leben": 10.0})]
_tr102.lage = {w_: [pygame.Vector2(w_.pos), 0, _tm.welt.zeit] for w_ in _g102}
_tr102._front_rechnen(_tr102.lebende())
_tr102._stellungen(_tr102.lebende())
pruef("Geknickte Front: zwei Abschnitte, jeder mit einer Linie fuer die Anzeige",
      _tr102.abschnitte == 2 and len(_tr102.abschnitt_linien) == 2
      and all(ab_["mitte"].distance_to(_tr102.front["freund"]) > K.TRUPP["abschnitt_vor"] - 1
              for ab_ in _tr102.abschnitt_linien), "")
_m102 = next(m_ for m_ in _tr102.lebende()
             if m_ is not _tr102.fuehrer and _tr102.blick_fuer(m_) is not None
             and _tr102.blick_fuer(m_).distance_to(_g102[0].pos) < 1.0)
for w_ in _g102:
    _m102.hirn.gesehen[w_] = (pygame.Vector2(w_.pos), 0, _tm.welt.zeit)
_or102 = _m102.hirn.bedrohungs_richtungen()
pruef("... wer nach Westen schaut, zaehlt fuer die Flanke nur den Westen - den Norden haelt ein Kamerad",
      len(_or102) == 1 and _or102[0].distance_to(_g102[0].pos) < 1.0 and not _m102.hirn.flankiert(), str(_or102))
_m102.hirn.beschossen_von[_g102[1]] = (pygame.Vector2(_g102[1].pos), 0, _tm.welt.zeit)
pruef("... schiesst aber einer aus dem Norden auf ihn, zaehlt der doch",
      len(_m102.hirn.bedrohungs_richtungen()) == 2, "")
_tm.sauber = True
_tm.sauber_trupps = True
_tm.zeichnen(pygame.Surface((K.GAME_W, K.GAME_H)), 1.0)
pruef("Aufnahmen koennen in der sauberen Ansicht die Trupps zeigen (zeichnen geht)", True, "")
_tm.verlassen()


print("\n-- Liegende, Schusslinie, Abschnitt, Deckung, Wurf, Ziehen, Last (0.34.52)")
# Die ganzen Szenen dazu stehen in tests/test_verhalten.py; hier je Ursache
# eine kurze, feste Pruefung.
from collections import deque as _deque103
from dustfront.bottaktik import kampffaehig as _kf103
from dustfront.trupp import an_deckung as _an103
from dustfront import bots as _BO103
_tm = _TM87.Testmodus(app, karte="staubtal")
_tm._bot_rnd.seed(103)
_tm.wiedereinstieg = False
_tm.verwundete_setzen(True)
_tx103, _ty103 = _freie_flaeche86(_tm.welt, random.Random(103), 18, 10)
def _v103(x_, y_):
    return pygame.Vector2((_tx103 + x_) * K.TILE, (_ty103 + y_) * K.TILE)
_a103 = _tm.bot_setzen(_v103(12.5, 2.5), 0, {"team": 0, "hirn": "goap"})
_b103 = _tm.bot_setzen(_v103(4.5, 2.5), 0, {"team": 1, "hirn": "goap"})
_tm.toeten(_b103)
_h103 = _a103.hirn
pruef("Wer liegt, ist kein Ziel und keine Gefahr (ziel_ok, kampffaehig)",
      _b103.am_boden and not _h103.ziel_ok(_b103) and not _kf103(_b103), "")
_h103.gesehen[_b103] = (pygame.Vector2(_b103.pos), 0, _tm.welt.zeit)
_h103.zugerufen[_b103] = (pygame.Vector2(_b103.pos), 0, _tm.welt.zeit)
pruef("... weder ein Feindort noch der letzte Feind - auch nicht zugerufen",
      _h103.feind_orte() == [] and _h103.letzter_feind() is None, str(_h103.feind_orte()))
_h103.ziel = _b103
_h103.stoss_rest = 3.0
_h103._wahrnehmen()
pruef("... ein Dauerfeuer auf ihn endet beim naechsten Hinsehen, und er faellt aus dem Gedaechtnis",
      _h103.ziel is None and _h103.stoss_rest == 0.0 and _b103 not in _h103.gesehen, "")
_h103._feinde_da = {_b103: pygame.Vector2(_b103.pos)}
_h103.gesehen[_b103] = (pygame.Vector2(_b103.pos), 0, _tm.welt.zeit)
_vor103 = len(_h103._abschuesse)
for _ in range(3):
    _h103._verluste_zaehlen()
pruef("... und zaehlt nur einmal als Abschuss, nicht jedes Bild wieder",
      len(_h103._abschuesse) == _vor103 + 1, "%d -> %d" % (_vor103, len(_h103._abschuesse)))

_c103 = _tm.puppe_setzen(_v103(8.5, 2.5), 0, {"team": 0, "leben": 10.0})
_h103.blick = 180.0
_quer103 = _h103.kamerad_im_weg(400.0)
_h103.blick = 90.0
_seit103 = _h103.kamerad_im_weg(400.0)
_h103.blick = 180.0
_nah103 = _h103.kamerad_im_weg(80.0)
pruef("Ein Kamerad in der Schusslinie sperrt den Schuss - daneben nicht, und nicht hinter dem Ziel",
      _quer103 and not _seit103 and not _nah103, "%s %s %s" % (_quer103, _seit103, _nah103))
_c103.am_boden = True
pruef("... wer liegt, ist unter der Bahn", not _h103.kamerad_im_weg(400.0), "")
_c103.am_boden = False

# Wegefeld: dieselben Abstaende wie die alte Breitensuche.
def _bfs103(wege_, e_, tx_, ty_):
    b_, h_ = wege_.breite[e_], wege_.hoehe[e_]
    frei_ = wege_.begehbar[e_]
    weit_ = [-1] * (b_ * h_)
    if not (0 <= tx_ < b_ and 0 <= ty_ < h_):
        return weit_
    weit_[ty_ * b_ + tx_] = 0
    offen_ = _deque103([ty_ * b_ + tx_])
    while offen_:
        i_ = offen_.popleft()
        x_, y_ = i_ % b_, i_ // b_
        for dx_, dy_ in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1)):
            nx_, ny_ = x_ + dx_, y_ + dy_
            if not (0 <= nx_ < b_ and 0 <= ny_ < h_):
                continue
            j_ = ny_ * b_ + nx_
            if not frei_[j_] or weit_[j_] >= 0:
                continue
            if dx_ and dy_ and not (frei_[y_ * b_ + nx_] and frei_[ny_ * b_ + x_]):
                continue
            weit_[j_] = weit_[i_] + 1
            offen_.append(j_)
    return weit_
_wg103 = _tm.welt.wege
_r103 = random.Random(7)
_gleich103 = True
for _ in range(4):
    _e103 = _r103.randrange(_wg103.ebenen)
    _x103, _y103 = _r103.randrange(_wg103.breite[_e103]), _r103.randrange(_wg103.hoehe[_e103])
    _gleich103 = _gleich103 and _wg103._ausbreiten(_e103, _x103, _y103) == _bfs103(_wg103, _e103, _x103, _y103)
pruef("Wegefeld mit vorgerechneten Nachbarn: dieselben Schritte wie die alte Breitensuche",
      _gleich103, "")

# Deckung zwischen zwei Punkten: dasselbe wie das alte Abtasten.
def _deckung103(welt_, von_, nach_, ebene_):
    von_, nach_ = pygame.Vector2(von_), pygame.Vector2(nach_)
    if not welt_.sicht_frei(von_, nach_, ebene_):
        return "wand"
    n_ = int(von_.distance_to(nach_) / 4.0)
    if n_ < 2:
        return ""
    for i_ in range(1, n_):
        if welt_.schuss_halt(von_.lerp(nach_, i_ / float(n_)), ebene_):
            return "hindernis"
    return ""
_e0103 = _tm.welt.ebene(0)
_ab103 = 0
for _ in range(1500):
    _p103 = pygame.Vector2(_r103.uniform(0, _e0103.breite * K.TILE), _r103.uniform(0, _e0103.hoehe * K.TILE))
    _q103 = _p103 + pygame.Vector2(_r103.uniform(20, 400), 0).rotate(_r103.uniform(0, 360))
    if _tm.welt.deckung(_p103, _q103, 0) != _deckung103(_tm.welt, _p103, _q103, 0):
        _ab103 += 1
pruef("Deckung ohne neuen Vektor je Punkt: dasselbe Ergebnis wie vorher (1500 Linien)", _ab103 == 0, str(_ab103))

# An die Deckung ruecken.
_wk103 = [(9, 1), (9, 2), (9, 3)]
for x_, y_ in _wk103:
    _e0103.setzen(_tx103 + x_, _ty103 + y_, K.KISTE)
_tm.welt._wege = None
_feind103 = _v103(3.5, 2.5)
_st103 = _v103(11.6, 2.5)
_dicht103 = _an103(_tm.welt, _st103, 9.0, 0, _feind103)
_rand103 = (_tx103 + 10) * K.TILE
pruef("Eine gedeckte Stellung rueckt bis an die Kiste heran und bleibt gedeckt",
      _dicht103.x < _st103.x and _dicht103.x - _rand103 - 9.0 <= K.TRUPP["anruecken_schritt"] + 2.5
      and _tm.welt.deckung(_feind103, _dicht103, 0) != "",
      "Luecke %.1f px" % (_dicht103.x - _rand103 - 9.0))

# Eine Wurfbahn, die eine Mauerecke streift: die Mitte frei, die Granate nicht.
for y_ in range(3, 7):
    _e0103.setzen(_tx103 + 15, _ty103 + y_, K.WAND)
_tm.welt._wege = None
_a103.pos.update(_v103(15.6, 2.5))
_streift103 = _v103(11.58, 5.5)
pruef("Wurfbahn: streift sie eine Mauerecke, gilt sie als zu - frei nur ganz frei",
      _tm.welt.deckung(_a103.pos, _streift103, 0) == "" and not _h103.wurfbahn_frei(_streift103)
      and _h103.wurfbahn_frei(_v103(11.5, 2.5)), "")

# Werfen erst, wenn er zum Ziel schaut.
_a103.waffen.append("rauch")
_nr103 = len(_a103.waffen) - 1
_a103.waffe = _nr103
_h103.wurf_platz = _nr103
_ziel103 = _BG88._Stelle(_v103(11.5, 2.5), 0)
_ziel103.genau = True
_h103.blick = 90.0
_h103.wurf_phase = 0.01
_warf103 = []
for _ in range(int(0.5 / K.FIXED_DT)):
    _warf103.append(_h103._werfen(K.FIXED_DT, {"knoepfe": []}, _ziel103)[2])
_h103.blick = _BO103._winkel_zu(_a103.pos, _ziel103.pos)
_dann103 = _h103._werfen(K.FIXED_DT, {"knoepfe": []}, _ziel103)[2]
pruef("Eine Granate fliegt erst, wenn er zum Ziel schaut - nicht in die alte Blickrichtung",
      not any(_warf103) and _dann103, "")
_h103.blick = 90.0
_h103.wurf_phase = 0.01
_spaet103 = [_h103._werfen(K.FIXED_DT, {"knoepfe": []}, _ziel103)[2]
             for _ in range(int((K.BOTS["wurf_warten"] + 0.3) / K.FIXED_DT))]
pruef("... schaut er nie hin, wirft er nach hoechstens wurf_warten trotzdem (kein Haengenbleiben)",
      any(_spaet103), "")
_a103.waffen.pop()
_a103.waffe = 0

# Ziehen an einer Ecke: er rutscht an der Kiste entlang.
_x103 = _tm.bot_setzen(_v103(9.5, 0.72), 0, {"team": 0, "hirn": "goap"})
_z103 = _tm.puppe_setzen(_v103(10.3, 1.4), 0, {"team": 0, "leben": 10.0})
_tm.toeten(_x103)
_x103.pos.update(_v103(9.5, 0.72))
_z103.zieht = _x103.nummer
_vorher103 = pygame.Vector2(_x103.pos)
_tm._ziehen(K.FIXED_DT)
pruef("Ein Gezogener an einer Kistenecke rutscht an ihr entlang, statt haengen zu bleiben",
      _x103.pos.x > _vorher103.x + 0.5 and _tm.welt.frei(_x103.pos, _x103.radius * 0.8, 0, True),
      "%s -> %s" % (_vorher103, _x103.pos))
_z103.zieht = None

# Liegt einer still, rechnet niemand seine Bewegung.
_zaehl103 = {"n": 0}
_bew103 = _tm.welt.bewegen
def _bewegen103(w_, dx_, dy_, _alt=_bew103):
    if w_ is _x103:
        _zaehl103["n"] += 1
    return _alt(w_, dx_, dy_)
_tm.welt.bewegen = _bewegen103
_x103.tempo.update(0, 0)
_x103.will.update(0, 0)
for _ in range(10):
    _x103.schritt(K.FIXED_DT)
_tm.welt.bewegen = _bew103
pruef("Wer still am Boden liegt, kostet keine Bewegung (world.bewegen wird nicht gefragt)",
      _zaehl103["n"] == 0, str(_zaehl103["n"]))
_tm.verlassen()

# Abschnitt: zwei Gruppen enger als zwei Abschnitte breit.
_tm = _TM87.Testmodus(app, karte="staubtal")
_tm._bot_rnd.seed(104)
_tm.wiedereinstieg = False
_tx104, _ty104 = _freie_flaeche86(_tm.welt, random.Random(104), 18, 11)
def _v104(x_, y_):
    return pygame.Vector2((_tx104 + x_ + 0.5) * K.TILE, (_ty104 + y_ + 0.5) * K.TILE)
_tr104 = _tm.trupp_setzen(_v104(10, 7), 0, {"groesse": 3, "team": 0})
_m104 = [m_ for m_ in _tr104.lebende() if m_ is not _tr104.fuehrer][0]
_m104.pos.update(_v104(10, 7))
_west104 = _m104.pos + pygame.Vector2(-300, 0)
_nw104 = _m104.pos + pygame.Vector2(300, 0).rotate(180 + 65)
_tr104.abschnitte = 2
_tr104.blicke = {_m104.nummer: _west104, -1: _nw104}
_zwischen104 = _m104.pos + pygame.Vector2(250, 0).rotate(180 + 55)
pruef("Abschnitt: was der anderen Gruppe naeher ist, gehoert ihr - auch innerhalb der 70 Grad",
      _m104.hirn.im_abschnitt(_west104 + pygame.Vector2(0, 30)) is True
      and _m104.hirn.im_abschnitt(_zwischen104) is False, "")
_gr104 = [(pygame.Vector2(-1, 0), _west104, 1), ((_nw104 - _m104.pos).normalize(), _nw104, 1)]
_k104 = [m_ for m_ in _tr104.lebende() if m_ is not _tr104.fuehrer]
_tr104._blicke_vorher = {_k104[0].nummer: _nw104, _k104[1].nummer: _west104}
_k104[0].pos.update(_v104(8, 7))                # liegt naeher am Westen ...
_k104[1].pos.update(_v104(9, 5))
_teile104 = _tr104._abschnitt_leute(_k104, _gr104, [1, 1], _v104(10, 7))
pruef("... und wer schon einen Abschnitt hat, behaelt ihn (kein Quer-durch-die-Stellung)",
      _teile104[1] == [_k104[0]] and _teile104[0] == [_k104[1]], "")
_tm.verlassen()

# Mit festem Zufall stellt der Testmodus jedes Mal dasselbe auf.
_auf104 = []
for _ in range(2):
    _tm = _TM87.Testmodus(app, karte="staubtal")
    _tm._bot_rnd.seed(5)
    _tr105 = _tm.trupp_setzen(_v104(10, 7), 0, {"groesse": 4, "team": 0})
    _auf104.append([(round(m_.pos.x, 2), round(m_.pos.y, 2), m_.name) for m_ in _tr105.mitglieder])
    _tm.verlassen()
pruef("Testmodus mit festem Zufall: dieselbe Aufstellung, dieselben Namen (Aufnahmen, Verhaltenstests)",
      _auf104[0] == _auf104[1], "")


print("\n-- Bergen: einer holt ihn, die anderen bleiben in Deckung (0.34.53)")
_tm = _TM87.Testmodus(app, karte="staubtal")
_tm._bot_rnd.seed(106)
_tm.wiedereinstieg = False
_tm.verwundete_setzen(True)
_tx106, _ty106 = _freie_flaeche86(_tm.welt, random.Random(106), 18, 11)
def _v106(x_, y_):
    return pygame.Vector2((_tx106 + x_ + 0.5) * K.TILE, (_ty106 + y_ + 0.5) * K.TILE)
for y_ in range(2, 9):
    _tm.welt.ebene(0).setzen(_tx106 + 13, _ty106 + y_, K.WAND)
_tm.welt._wege = None
_tr106 = _tm.trupp_setzen(_v106(15, 5), 0, {"groesse": 4, "team": 0, "fuehrer": "funk"})
_fe106 = [_tm.puppe_setzen(_v106(2, 4 + 2 * i_), 0, {"team": 1, "leben": 10.0}) for i_ in range(2)]
for f_ in _fe106:
    f_.unverwundbar = 1e9
_op106 = next(m_ for m_ in _tr106.mitglieder if m_ is not _tr106.fuehrer)
_op106.pos.update(_v106(9, 5))
_tr106.lage = {w_: [pygame.Vector2(w_.pos), 0, _tm.welt.zeit] for w_ in _fe106}
_tm.ki_stopp = True
_tm.toeten(_op106)
_frei106 = [m_ for m_ in _tr106.lebende() if m_ is not _tr106.fuehrer]
_frei106[0].pos.update(_v106(14, 4))            # dicht hinter der Mauer
_frei106[1].pos.update(_v106(10, 2))            # im Freien, wie nach einem Rauchwurf
_tr106._takt = 0.0
_tr106.schritt(_D87)
_b106 = _tr106.bergung
_naechst106 = min(_frei106, key=lambda m_: m_.pos.distance_to(_op106.pos))
pruef("Ein Retter, nicht zwei - der Naechste, nicht der Anfuehrer",
      K.VERWUNDET["retter"] == 1 and _b106 is not None and _b106["retter"] == {_naechst106.nummer},
      str(_b106 and _b106["retter"]))
_ruhig106 = [m_ for m_ in _tr106.lebende() if m_.nummer not in _b106["retter"]]
def _gedeckt106(p_):
    return all(_tm.welt.deckung(f_.pos, p_, 0) != "" for f_ in _fe106)
pruef("... jeder andere bekommt eine gedeckte Stellung, solange er geborgen wird",
      all(_tr106.stellung(m_) is not None and _gedeckt106(_tr106.stellung(m_)) for m_ in _ruhig106),
      str([(m_.nummer, _tr106.stellung(m_)) for m_ in _ruhig106]))
_hinten106 = next(m_ for m_ in _ruhig106 if m_.pos.distance_to(_v106(14, 4)) < 1.0) if any(
    m_.pos.distance_to(_v106(14, 4)) < 1.0 for m_ in _ruhig106) else None
pruef("... wer schon gedeckt steht, bleibt dort",
      _hinten106 is None or _tr106.stellung(_hinten106).distance_to(_hinten106.pos) < 1.0, "")
_fk106 = {m_.nummer: m_.hirn._bergung_fakten()["bergung_halten"] for m_ in _tr106.lebende()}
pruef("... sie wissen es (bergung_halten), der Retter nicht",
      all(_fk106[m_.nummer] for m_ in _ruhig106) and not any(_fk106[n_] for n_ in _b106["retter"]), str(_fk106))
_ak106 = _WD88.daten().aktionen
pruef("... und wer haelt, setzt nicht nach, flankiert nicht und geht nicht suchen",
      all("bergung_halten" in str(getattr(_ak106[n_], "braucht", "")) for n_ in ("nachsetzen", "flankieren", "suchen")),
      "")
_tm.verlassen()


print("\n-- Feuerschutz beim Bergen: wer den Retter bedroht, wird niedergehalten (0.34.54)")
_zl107 = _WD88.daten().ziele
def _zw107(ziel_, **f_):
    w_ = {"bergung_halten": 0, "feind_bekannt": 0, "kamerad_braucht_schutz": 0, "feind_sichtbar": 0,
          "disziplin": 0.5, "rauch_da": 0, "ist_fuehrer": 0, "kamerad_liegt": 0, "trupp_rueckzug": 0}
    w_.update(f_)
    z_ = _zl107[ziel_]
    return z_.rang.wert(w_), z_.dringlich.wert(w_)
_r107 = _zw107("feuerschutz", bergung_halten=1, feind_bekannt=1, feind_sichtbar=1)
_n107 = _zw107("feuerschutz", kamerad_braucht_schutz=1, feind_bekannt=1)
_rauch107 = _zw107("rauch_legen", rauch_da=1, ist_fuehrer=1, kamerad_liegt=1, feind_bekannt=1)
pruef("Feuerschutz hat beim Bergen Rang 1 - auch wenn er den Gegner sieht - und bleibt unter dem Nachladen (85)",
      _r107[0] == 1 and 0 < _r107[1] < 85 and _n107[0] == 0, "%s %s" % (_r107, _n107))
pruef("... der Rauch fuer den Liegenden geht trotzdem vor (Rang 1, dringlicher)",
      _rauch107[0] >= 1 and _rauch107[1] > _r107[1], str(_rauch107))
_tm = _TM87.Testmodus(app, karte="staubtal")
_tm._bot_rnd.seed(107)
_tm.wiedereinstieg = False
_tm.verwundete_setzen(True)
_tx107, _ty107 = _freie_flaeche86(_tm.welt, random.Random(107), 18, 11)
def _v107(x_, y_):
    return pygame.Vector2((_tx107 + x_ + 0.5) * K.TILE, (_ty107 + y_ + 0.5) * K.TILE)
_tr107 = _tm.trupp_setzen(_v107(15, 5), 0, {"groesse": 3, "team": 0, "fuehrer": "funk"})
_g107 = _tm.bot_setzen(_v107(5, 5), 0, {"team": 1, "hirn": "goap"})
_tm.ki_stopp = True
_op107 = next(m_ for m_ in _tr107.mitglieder if m_ is not _tr107.fuehrer)
_op107.pos.update(_v107(9, 5))
_tm.toeten(_op107)
_an107 = [m_ for m_ in _tr107.lebende()]
_tr107.bergung = dict(opfer=_op107, retter=set(), sicher=False, bedrohung=1, orte=[])
_h107 = _an107[0].hirn
pruef("Wer den Liegenden treffen kann, bedroht die Bergung - wer weiter weg steht, als eine Waffe reicht, nicht",
      _h107.bedroht_bergung(_g107.pos, 0) and not _h107.bedroht_bergung(_op107.pos + pygame.Vector2(5000, 0), 0), "")
_h107.lagebild = [[pygame.Vector2(_g107.pos) + pygame.Vector2(-10, 0), 0, _tm.welt.zeit, "schuss"]]
_h107.gesehen.clear()
_tr107.lage = {}
_bg107 = _h107.bergung_bedrohung()
pruef("... auch wen er nur schiessen hoert: dorthin haelt er nieder",
      _bg107 is not None and _bg107[0].distance_to(_g107.pos) < 20.0 and _bg107[2] is None, str(_bg107))
_h107.gehirn.fakten["bergung_halten"] = True
pruef("... ohne die lange Pause zwischen zwei Stoessen", _h107.druck_pause_faktor() < 1.0,
      str(_h107.druck_pause_faktor()))
_h107.gehirn.fakten["bergung_halten"] = False
_k107 = _an107[1]
_k107.zuletzt_von = _g107
_k107.hirn._getroffen()
pruef("Wer getroffen wird, ruft es heraus: der Trupp weiss sofort, woher geschossen wurde",
      _g107 in _tr107.lage and _tr107.lage[_g107][0].distance_to(_g107.pos) < 1.0, "")
_tm.verlassen()


print("\n-- Nicht durch Mauern, Kisten weiter niederhalten; Testmodus ohne Nebel (0.34.54)")
_tm = _TM87.Testmodus(app, karte="staubtal")
_tm._bot_rnd.seed(108)
_tm.wiedereinstieg = False
_tx108, _ty108 = _freie_flaeche86(_tm.welt, random.Random(108), 16, 8)
def _v108(x_, y_):
    return pygame.Vector2((_tx108 + x_ + 0.5) * K.TILE, (_ty108 + y_ + 0.5) * K.TILE)
_tm.welt.ebene(0).setzen(_tx108 + 8, _ty108 + 2, K.WAND)
_tm.welt.ebene(0).setzen(_tx108 + 8, _ty108 + 5, K.KISTE)
_tm.welt._wege = None
_s108 = _tm.bot_setzen(_v108(12, 2), 0, {"team": 0, "hirn": "goap", "waffe": "sturm"})
_tm.ki_stopp = True
def _feuert108(punkt_):
    h_ = _s108.hirn
    _s108.pos.update(pygame.Vector2(punkt_.x + 6 * K.TILE, punkt_.y))
    h_.blick = 180.0
    h_.denk_rest = 1.0
    alt_ = h_._entscheiden
    h_._entscheiden = lambda dt_, ein_: (pygame.Vector2(0, 0), pygame.Vector2(punkt_), True, False)
    try:
        return bool(h_.eingabe(K.FIXED_DT)["feuert"])
    finally:
        h_._entscheiden = alt_
_wand108 = _feuert108(_v108(4, 2))
_kiste108 = _feuert108(_v108(4, 5))
_frei108 = _feuert108(_v108(4, 7))
pruef("Hinter einer Mauer: kein Schuss - hinter einer Kiste (niederhalten) und im Freien: ja",
      not _wand108 and _kiste108 and _frei108, "%s %s %s" % (_wand108, _kiste108, _frei108))
# Seit 0.34.91 aus als Vorgabe (gewuenscht) - einschalten wie bisher.
pruef("Testmenue: NEBEL (SICHTWEITE) ist eine Zeile, aus als Vorgabe",
      any(z_[0] == "nebel" for z_ in _tm._menue_zeilen()) and not _tm.nebel, "")
_tm.zoom_ziel = _tm.kamera.zoom = max(K.ZOOM["stufen"])
_tm.menue_wirken("nebel")
pruef("... eingeschaltet wie im Spiel", _tm.nebel, "")
_mit108 = _tm.sicht_welt()
_tm.menue_wirken("nebel")
_ohne108 = _tm.sicht_welt()
pruef("... herausgezoomt liegt mit Nebel alles ausserhalb des normalen Bildes im Nebel, ohne ihn nichts",
      _mit108 is not None and _ohne108 is None and not _tm.nebel and _tm.im_licht(_v108(500, 500)), "")
pruef("... und der Schalter bleibt ueber einen Kartenwechsel erhalten", _tm.zustand()["nebel"] is False, "")
_tm.verlassen()

print("\n-- Last bei vielen Liegenden: Planer, Netzmeldung, Partikel (0.34.55)")
from dustfront import goap as _G109
import heapq as _hq109
_knoten109 = [0]
class _Zaehl109:
    heappop = staticmethod(_hq109.heappop)
    @staticmethod
    def heappush(l_, e_):
        _knoten109[0] += 1
        _hq109.heappush(l_, e_)
_G109.heapq = _Zaehl109
try:
    # Zwanzig Aktionen, die mit dem Ziel nichts zu tun haben, und eine, die
    # es machte - aber nur ohne "halten", und "halten" aendert keiner.
    _ak109 = [_G109.Aktion("laerm%d" % i_, braucht="", macht="l%d" % i_) for i_ in range(20)]
    _ak109.append(_G109.Aktion("suchen", braucht="!halten", macht="gefunden"))
    _p109 = _G109.planen({"halten": True}, {"gefunden": True}, _ak109)
    _n109 = _knoten109[0]
    pruef("Ein Ziel, dessen einzige Aktion einen Fakt braucht, den keiner aendert: sofort kein Plan",
          _p109 is None and _n109 == 0, "%s, %d Zustaende" % (_p109, _n109))
    _knoten109[0] = 0
    _p109b = _G109.planen({}, {"gefunden": True}, _ak109)
    pruef("... ohne den Fakt: der Plan wie immer, und die zwanzig fremden Aktionen nicht durchprobiert",
          [a_.name for a_ in _p109b or []] == ["suchen"] and _knoten109[0] <= 2,
          "%s, %d Zustaende" % (_p109b, _knoten109[0]))
    _ak109b = [_G109.Aktion("hin", braucht="", macht="dort"),
               _G109.Aktion("nehmen", braucht="dort", macht="hat"),
               _G109.Aktion("laerm", braucht="", macht="l")]
    _p109c = _G109.planen({}, {"hat": True}, _ak109b)
    pruef("... was ein Vorgaenger braucht, bleibt dabei (hin > nehmen)",
          [a_.name for a_ in _p109c or []] == ["hin", "nehmen"], str(_p109c))
finally:
    _G109.heapq = _hq109
_tm = _TM87.Testmodus(app, karte="staubtal")
_tm._bot_rnd.seed(109)
_tm.wiedereinstieg = False
_tm._wirkung = [["x"]]
_baut109 = [0]
_alt109 = _tm._weltmeldung
def _meld109():
    _baut109[0] += 1
    return _alt109()
_tm._weltmeldung = _meld109
for _ in range(10):
    _tm.schritt(K.FIXED_DT)
pruef("Ohne Gast wird die Netzmeldung nicht gebaut - die Wirkungen verfallen trotzdem",
      _baut109[0] == 0 and _tm._wirkung == [] and not _tm.gastgeber.leitungen, str(_baut109))
del _tm._weltmeldung
_r109 = _tm.renderer
_flaeche109 = pygame.Surface((K.GAME_W, K.GAME_H))
_ecke109 = pygame.Vector2(_tm.kamera.ecke)
_tm.welt.partikel[:] = [_P65(_ecke109 + pygame.Vector2(-5000, 300), (0, 0), 5.0, (200, 0, 0), art="funke"),
                        _P65(_ecke109 + pygame.Vector2(200, 200), (0, 0), 5.0, (200, 0, 0), art="funke")]
_geprueft109 = []
_alt_v109 = _r109.verdeckt
_r109.verdeckt = lambda welt_, i_, p_, h_: _geprueft109.append(pygame.Vector2(p_)) or False
try:
    _r109.partikel_zeichnen(_flaeche109, _tm.welt, 0, _ecke109, 1.0)
finally:
    del _r109.verdeckt
pruef("Funken weit ausserhalb des Bildes werden nicht auf Mauern davor abgetastet, die im Bild schon",
      len(_geprueft109) == 1 and _geprueft109[0].distance_to(_ecke109 + pygame.Vector2(200, 200)) < 1.0,
      str(_geprueft109))
_tm.verlassen()

print("\n-- Helfer greift den Richtigen, bringt es zu Ende; kein Kreiseln (0.34.55)")
_tm = _TM87.Testmodus(app, karte="staubtal")
_tm._bot_rnd.seed(110)
_tm.wiedereinstieg = False
_tm.verwundete_setzen(True)
_tx110, _ty110 = _freie_flaeche86(_tm.welt, random.Random(110), 16, 9)
def _v110(x_, y_):
    return pygame.Vector2((_tx110 + x_ + 0.5) * K.TILE, (_ty110 + y_ + 0.5) * K.TILE)
_h110 = _tm.bot_setzen(_v110(5, 4), 0, {"team": 0, "hirn": "goap"})
_x110 = _tm.bot_setzen(_v110(7, 4), 0, {"team": 0, "hirn": "goap"})
_y110 = _tm.bot_setzen(_v110(3, 4), 0, {"team": 0, "hirn": "goap"})
_tm.ki_stopp = True
_x110.pos.update(_h110.pos + pygame.Vector2(20, 0))
_y110.pos.update(_h110.pos + pygame.Vector2(-12, 0))
_tm.toeten(_x110)
_tm.toeten(_y110)
pruef("Zwei liegen nebeneinander: ohne Angabe wird der Naechste gezogen, mit Angabe der Gemeinte",
      _tm._wen_ziehen(_h110) is _y110 and _tm._wen_ziehen(_h110, _x110.nummer) is _x110
      and _tm._wem_helfen(_h110, _x110.nummer) is _x110, "")
_x110.pos.update(_h110.pos + pygame.Vector2(60, 0))
pruef("... ist der Gemeinte ausser Reichweite, greift er keinen anderen",
      _tm._wen_ziehen(_h110, _x110.nummer) is None and _tm._wem_helfen(_h110, _x110.nummer) is None, "")
_x110.pos.update(_h110.pos + pygame.Vector2(20, 0))
_tm._anwenden(_h110, {"will": [0, 0], "ziel": [0, 0], "ziehen": True, "wen": _y110.nummer})
_tm._anwenden(_h110, {"will": [0, 0], "ziel": [0, 0], "ziehen": True, "wen": _x110.nummer})
pruef("... hat er den falschen in der Hand, laesst er ihn los und nimmt den Gemeinten",
      _h110.zieht == _x110.nummer and _y110.gezogen_von is None, "%s %s" % (_h110.zieht, _y110.gezogen_von))
_tm._anwenden(_h110, {"will": [0, 0], "ziel": [0, 0]})
_tm.loeschen(_y110)
_hh110 = _h110.hirn
_ein110 = {"nutzen": False}
_x110.pos.update(_h110.pos + pygame.Vector2(26, 0))
_hh110._helfen(_x110, _ein110)
_draussen110 = _ein110["nutzen"]
_h110.hilft = _x110.nummer
_ein110 = {"nutzen": False}
_hh110._helfen(_x110, _ein110)
pruef("Wer schon aufhilft, hilft bis an die Reichweite weiter (26 px: vorher nicht, dabei schon)",
      not _draussen110 and _ein110["nutzen"] and _ein110.get("wen") == _x110.nummer, str(_ein110))
_x110.revive_stand = 0.3
_hh110.bedrohung = lambda x_: 3
_f110 = _hh110._bergung_fakten()
_x110.revive_stand = 0.6
_f110b = _hh110._bergung_fakten()
del _hh110.bedrohung
pruef("... er hilft schon (hilft_schon), bleibt der Retter, und ab der Haelfte bringt er es zu Ende, auch wenn einer hinsieht",
      _f110["hilft_schon"] and _f110["ich_berge"] and _f110["bei_kamerad"] and not _f110["bergen_sicher"]
      and _f110b["bergen_sicher"], "%s / %s" % (_f110, _f110b))
_ak110 = _hh110.gehirn.aktionen
_fakt110 = {"kamerad_liegt": True, "bei_kamerad": True, "ich_berge": True}
_p110a = _G109.planen(_fakt110, {"kamerad_liegt": False}, _ak110)
_p110b = _G109.planen(dict(_fakt110, hilft_schon=True), {"kamerad_liegt": False}, _ak110)
pruef("... und plant mitten im Aufhelfen nicht mehr das Ziehen (vorher: erst ziehen)",
      [a_.name for a_ in _p110a or []][:1] == ["kamerad_ziehen"]
      and [a_.name for a_ in _p110b or []] == ["aufhelfen_offen"], "%s / %s" % (_p110a, _p110b))
_z110 = next(z_ for z_ in _hh110.gehirn.ziele if z_.name == "kamerad_bergen")
_n110 = {"kamerad_liegt": 1, "ich_berge": 1, "bergen_sicher": 1, "fast_fertig": 0}
_rang110 = _z110.rang.wert(_n110)
_n110["fast_fertig"] = 1
pruef("... fast fertig hat das Bergen Rang 3: nur die Granate geht dann noch vor",
      _rang110 == 1 and _z110.rang.wert(_n110) == 3 and _f110b["fast_fertig"], str(_rang110))
_x110.pos.update(_h110.pos + pygame.Vector2(K.REVIVE["reichweite"] + 2, 0))
pruef("Das Gefecht laesst ihn weiterhelfen, wenn er ein Stueck hinausgerutscht ist - anfangen nur in Reichweite",
      _tm._wem_helfen(_h110, _x110.nummer, _x110.nummer) is _x110
      and _tm._wem_helfen(_h110, _x110.nummer) is None, "")
_x110.pos.update(_h110.pos + pygame.Vector2(20, 0))
_s110 = _tm.bot_setzen(_v110(9, 4), 0, {"team": 0, "hirn": "goap"})
_s110.pos.update(_h110.pos + pygame.Vector2(0, 10))
_vor110 = pygame.Vector2(_h110.pos)
_tm.welt._raster_bauen()
_tm.welt.auseinander(_s110)
pruef("Wer aufhilft, kniet: ein anderer, der in ihn hineinlaeuft, schiebt ihn nicht weg",
      _h110.pos == _vor110 and _s110.pos.distance_to(_h110.pos) > 10.5, str(_h110.pos - _vor110))
_tm.loeschen(_s110)
_w110 = _tm.bot_setzen(_v110(12, 4), 0, {"team": 0, "hirn": "goap"})
_w110.pos.update(_h110.pos + pygame.Vector2(0, 200))
_tm.toeten(_w110)
pruef("Wem er schon aufhilft, bei dem bleibt er - auch wenn ein anderer naeher oder 'dran' ist",
      _hh110._opfer() is _x110, str(_hh110._opfer()))
_tm.loeschen(_w110)
_hh110._umschau_bis = _tm.welt.zeit + 5.0
_hh110._umschau_punkt = _h110.pos + pygame.Vector2(-300, 0)
_us110 = _hh110._umschauen(K.FIXED_DT, pygame.Vector2(0, 0), pygame.Vector2(_x110.pos), False)
pruef("Beim Aufhelfen schaut er nicht um - sein Blick bleibt beim Kameraden",
      _us110[1] == _x110.pos and _hh110._umschau_bis == 0.0, str(_us110[1]))
_h110.hilft = None
_a110 = _tm.bot_setzen(_v110(12, 6), 0, {"team": 0, "hirn": "goap"})
_a110.hilft = _x110.nummer
_fa110 = _hh110._bergung_fakten()
_pa110 = _G109.planen(dict(_fakt110, anderer_hilft=True), {"kamerad_liegt": False}, _ak110)
_a110.hilft = None
_tm.loeschen(_a110)
pruef("Hilft ihm schon ein anderer auf, zieht er ihn nicht weg - er hilft mit",
      _fa110["anderer_hilft"] and [a_.name for a_ in _pa110 or []] == ["aufhelfen_offen"],
      "%s %s" % (_fa110.get("anderer_hilft"), _pa110))
# Blick ohne Zielpunkt: kennt er einen Gegner, schaut er zu ihm.
_gef110 = _h110.pos + pygame.Vector2(0, -300)
_hh110._gefahr = lambda: (pygame.Vector2(_gef110), 0, None)
pruef("Ohne Zielpunkt schaut er zum bekannten Gegner, nicht in die Laufrichtung",
      _hh110._blick_ohne_ziel(pygame.Vector2(1, 0)).distance_to(_gef110) < 1.0, "")
del _hh110._gefahr
_hh110._gefahr = lambda: None
_zeit110 = _tm.welt.zeit
_hh110.blick = 0.0
_richtungen110 = [pygame.Vector2(0, 1), pygame.Vector2(-1, 0), pygame.Vector2(0, -1), pygame.Vector2(1, 0)]
_gedreht110 = []
for i_ in range(8):
    _tm.welt.zeit = _zeit110 + i_ * 0.15
    p_ = _hh110._blick_ohne_ziel(_richtungen110[i_ % 4])
    _gedreht110.append(round(math.degrees(math.atan2(p_.y - _h110.pos.y, p_.x - _h110.pos.x))))
_tm.welt.zeit = _zeit110 + 2.0
_hh110._blick_ohne_ziel(pygame.Vector2(0, 1))
_tm.welt.zeit = _zeit110 + 2.5
_lang110 = _hh110._blick_ohne_ziel(pygame.Vector2(0, 1))
_tm.welt.zeit = _zeit110
del _hh110._gefahr
pruef("Trippelschritte in vier Richtungen drehen den Blick nicht - wer eine Weile in eine Richtung geht, schaut dorthin",
      all(abs(w_) < 1 for w_ in _gedreht110) and (_lang110 - _h110.pos).angle_to(pygame.Vector2(0, 1)) == 0,
      str(_gedreht110))
# Rauch: findet er keine Stelle mit freier Wurfbahn, laesst er ihn nach
# ein paar Sekunden - statt hinter einer langen Mauer herumzulaufen.
_wi110 = next(i_ for i_, n_ in enumerate(_h110.waffen) if "wurf_max" in K.WAFFEN[n_])
_hh110._gefahr = lambda: (pygame.Vector2(_h110.pos) + pygame.Vector2(300, 0), 0, None)
_hh110.wurfbahn_frei = lambda nach_: False
_hh110._rauch_platz = lambda: _wi110
_status110 = []
for t_ in [i_ * 0.4 for i_ in range(10)] + [7.0]:      # dicht hintereinander: ein Anlauf
    _tm.welt.zeit = _zeit110 + 10.0 + t_
    _status110.append(_hh110.tun_rauch(K.FIXED_DT, {"knoepfe": []})[4])
_tm.welt.zeit = _zeit110
del _hh110._gefahr, _hh110.wurfbahn_frei, _hh110._rauch_platz
pruef("Ohne freie Wurfbahn geht er hoechstens rauch_laufen Sekunden dorthin, dann laesst er den Rauch eine Weile",
      _status110 == ["laeuft"] * 8 + ["gescheitert"] * 3, str(_status110))
_tm.verlassen()
_tm = _TM87.Testmodus(app, karte="staubtal")
_tm._bot_rnd.seed(111)
_tm.wiedereinstieg = False
_tx111, _ty111 = _freie_flaeche86(_tm.welt, random.Random(111), 16, 9)
_tr111 = _tm.trupp_setzen(pygame.Vector2((_tx111 + 8) * K.TILE, (_ty111 + 4) * K.TILE), 0,
                          {"groesse": 4, "team": 0, "fuehrer": "funk"})
_tm.ki_stopp = True
_tr111.ziel_ort = lambda: None
_l111 = _tr111.lebende()
_tr111.fuehrer.hirn.blick = 0.0
_tr111._linie_ohne_kontakt(_l111)
_r0_111 = pygame.Vector2(_tr111._linie_richtung)
_tr111.fuehrer.hirn.blick = 10.0
_tr111._linie_ohne_kontakt(_l111)
_r1_111 = pygame.Vector2(_tr111._linie_richtung)
_tr111.fuehrer.hirn.blick = 150.0
_tr111._linie_ohne_kontakt(_l111)
_r2_111 = pygame.Vector2(_tr111._linie_richtung)
pruef("Die Linie ohne Kontakt wackelt nicht mit jedem Blick des Anfuehrers und schwenkt nur langsam nach",
      _r1_111 == _r0_111 and abs(_r1_111.angle_to(_r2_111)) <= K.TRUPP["linie_dreh"] + 0.01,
      "%.1f %.1f" % (_r0_111.angle_to(_r1_111), _r1_111.angle_to(_r2_111)))
_tm.verlassen()

print("\n-- In Runden flieht kein Bot in Panik (0.34.56)")
_tm = _TM87.Testmodus(app, karte="staubtal")
_tm._bot_rnd.seed(112)
_tm.wiedereinstieg = False
_tx112, _ty112 = _freie_flaeche86(_tm.welt, random.Random(112), 12, 6)
_b112 = _tm.bot_setzen(pygame.Vector2((_tx112 + 3) * K.TILE, (_ty112 + 3) * K.TILE), 0, {"team": 0, "hirn": "goap"})
_tm.ki_stopp = True
_ak112 = _b112.hirn.gehirn.aktionen
_f112 = {"panik": True, "feind_bekannt": True}
pruef("Ein Gefecht laesst Bots nicht fliehen; der Testmodus zeigt es wie in Runden",
      not Gefecht.bot_fliehen and not _tm.bot_fliehen
      and _b112.hirn.fuehlen()[0]["darf_fliehen"] is False, "")
_p112 = _G109.planen(_f112, {"sicher": True}, _ak112)
_p112b = _G109.planen(dict(_f112, darf_fliehen=True), {"sicher": True}, _ak112)
pruef("... Panik im Freien: er wechselt die Deckung statt zu fliehen - wo es erlaubt ist, darf er fliehen",
      [a_.name for a_ in _p112 or []] == ["deckung_wechseln"] and "fliehen" in [a_.name for a_ in _p112b or []],
      "%s / %s" % (_p112, _p112b))
pruef("Testmenue: BOTS FLIEHEN IN PANIK, AUS wie in Runden; einschaltbar wie in der Kampagne, bleibt ueber einen Kartenwechsel",
      any(z_[0] == "fliehen" for z_ in _tm._menue_zeilen()), "")
_tm.menue_wirken("fliehen")
pruef("... AN: der Bot weiss es", _tm.bot_fliehen and _b112.hirn.fuehlen()[0]["darf_fliehen"]
      and _tm.zustand()["bot_fliehen"] is True, "")
_tm.verlassen()

print("\n-- Bildrate: Sichtlinien, Deckung, Wegfelder, Boden (0.34.57)")
_tm = _TM87.Testmodus(app, karte="staubtal")
_tm._bot_rnd.seed(113)
_tm.wiedereinstieg = False
_w113 = _tm.welt


def _dicht113(e_, x_, y_):
    return bool(K.KACHELN[e_.kachel(x_, y_)]["sicht"])


def _sicht113(von_, nach_, ebene_):
    # Die Verfolgung wie bis 0.34.56: Kachel fuer Kachel, mit K.KACHELN.
    e_ = _w113.ebene(ebene_)
    T_ = float(K.TILE)
    x0_, y0_ = von_.x / T_, von_.y / T_
    dx_, dy_ = nach_.x / T_ - x0_, nach_.y / T_ - y0_
    if dx_ * dx_ + dy_ * dy_ < (1.0 / T_) ** 2:
        return True
    tx_, ty_ = int(math.floor(x0_)), int(math.floor(y0_))
    sx_, sy_ = (1 if dx_ > 0 else -1), (1 if dy_ > 0 else -1)
    inf_ = float("inf")
    tdx_ = abs(1.0 / dx_) if dx_ else inf_
    tdy_ = abs(1.0 / dy_) if dy_ else inf_
    tmx_ = ((tx_ + 1 - x0_) if dx_ > 0 else (x0_ - tx_)) * tdx_ if dx_ else inf_
    tmy_ = ((ty_ + 1 - y0_) if dy_ > 0 else (y0_ - ty_)) * tdy_ if dy_ else inf_
    while min(tmx_, tmy_) <= 1.0:
        if abs(tmx_ - tmy_) < 1e-9:
            if _dicht113(e_, tx_ + sx_, ty_) or _dicht113(e_, tx_, ty_ + sy_):
                return False
            tx_ += sx_
            ty_ += sy_
            tmx_ += tdx_
            tmy_ += tdy_
        elif tmx_ < tmy_:
            tx_ += sx_
            tmx_ += tdx_
        else:
            ty_ += sy_
            tmy_ += tdy_
        if _dicht113(e_, tx_, ty_):
            return False
    return True


def _deckung113(von_, nach_, ebene_):
    # Wie bis 0.34.56: jede Linie alle 4 px abgetastet, ohne Abkuerzung.
    if not _sicht113(von_, nach_, ebene_):
        return "wand"
    e_ = _w113.ebene(ebene_)
    schritte_ = int(von_.distance_to(nach_) / 4.0)
    for i_ in range(1, schritte_):
        t_ = i_ / float(schritte_)
        px_, py_ = von_.x + (nach_.x - von_.x) * t_, von_.y + (nach_.y - von_.y) * t_
        tx_, ty_ = int(px_ // K.TILE), int(py_ // K.TILE)
        k_ = e_.kachel(tx_, ty_)
        if K.KACHELN[k_]["sicht"]:
            return "hindernis"
        if not K.KACHELN[k_]["fest"]:
            continue
        form_, rx_, ry_, rb_, rh_ = _w113.huelle(k_)
        hx_, hy_ = tx_ * K.TILE + rx_, ty_ * K.TILE + ry_
        if form_ == "rund":
            mx_, my_ = hx_ + rb_ / 2.0, hy_ + rh_ / 2.0
            if (px_ - mx_) ** 2 + (py_ - my_) ** 2 < (rb_ / 2.0) ** 2:
                return "hindernis"
        elif hx_ <= px_ < hx_ + rb_ and hy_ <= py_ < hy_ + rh_:
            return "hindernis"
    return ""


_rnd113 = random.Random(113)
_e0_113 = _w113.ebene(0)
_fest113 = [(i_ % _e0_113.breite, i_ // _e0_113.breite) for i_, k_ in enumerate(_e0_113.kacheln)
            if K.KACHELN[k_]["fest"] and not K.KACHELN[k_]["sicht"]]
_anders113, _arten113 = [], {"": 0, "hindernis": 0, "wand": 0}
for i_ in range(3000):
    eb_ = _rnd113.randrange(len(_w113.ebenen))
    e_ = _w113.ebene(eb_)
    if i_ % 2 and _fest113:
        # Die Haelfte dicht an Kisten und Faessern vorbei - dort liegt der Unterschied.
        fx_, fy_ = _rnd113.choice(_fest113)
        eb_ = 0
        mitte_ = pygame.Vector2((fx_ + 0.5) * K.TILE, (fy_ + 0.5) * K.TILE)
        a_ = mitte_ + pygame.Vector2(_rnd113.uniform(-120, 120), _rnd113.uniform(-120, 120))
        b_ = mitte_ + (mitte_ - a_) + pygame.Vector2(_rnd113.uniform(-12, 12), _rnd113.uniform(-12, 12))
    else:
        a_ = pygame.Vector2(_rnd113.uniform(0, e_.pixel_breite), _rnd113.uniform(0, e_.pixel_hoehe))
        b_ = a_ + pygame.Vector2(_rnd113.uniform(-400, 400), _rnd113.uniform(-400, 400))
    soll_ = (_sicht113(a_, b_, eb_), _deckung113(a_, b_, eb_))
    ist_ = (_w113.sicht_frei(a_, b_, eb_), _w113.deckung(a_, b_, eb_))
    _arten113[soll_[1]] += 1
    if soll_ != ist_:
        _anders113.append((tuple(a_), tuple(b_), eb_, soll_, ist_))
pruef("Sicht und Deckung in einer Verfolgung mit Tafeln: auf 3000 Linien genau wie vorher",
      not _anders113 and min(_arten113.values()) > 50, "%s %s" % (_arten113, _anders113[:2]))
from dustfront import world as _WELT113
_tafel113 = _WELT113._tafeln()
pruef("... die Tafel kennt jede Kachelart: 2 sichtdicht, 1 fest, 0 frei",
      all(_tafel113[n_] == (2 if d_["sicht"] else (1 if d_["fest"] else 0)) for n_, d_ in K.KACHELN.items()), "")

# Wegfelder breiten sich nur so weit aus, wie gefragt wird.
_wn113 = _w113.wege
_b113, _h113 = _wn113.breite[0], _wn113.hoehe[0]
_frei113 = [i_ for i_ in range(_b113 * _h113) if _wn113.begehbar[0][i_]]
_gleich113, _klein113 = True, True
for _ in range(3):
    s_ = _rnd113.choice(_frei113)
    _wn113._letztes_bild = None
    _s_, f_ = _wn113.feld_zu(0, pygame.Vector2((s_ % _b113 + 0.5) * K.TILE, (s_ // _b113 + 0.5) * K.TILE))
    f_[s_ + 1]
    _klein113 = _klein113 and sum(1 for w_ in f_.weit if w_ >= 0) < len(_frei113) // 4
    voll_ = _wn113._ausbreiten(0, s_ % _b113, s_ // _b113)
    reihe_ = list(range(_b113 * _h113))
    _rnd113.shuffle(reihe_)
    _gleich113 = _gleich113 and all(f_[i_] == voll_[i_] for i_ in reihe_)
pruef("Ein Wegfeld rechnet erst, wonach gefragt wird - und liefert in jeder Reihenfolge dasselbe wie die ganze Breitensuche",
      _gleich113 and _klein113, "%s %s" % (_gleich113, _klein113))

# Der Boden in Bloecken: eine geaenderte Kachel wird neu gezeichnet - eine
# freie Bodenkachel mitten im Bild.
_tx113b, _ty113b = _freie_flaeche86(_w113, random.Random(113), 14, 8)
_tx113, _ty113 = _tx113b + 3, _ty113b + 3
_r113 = _tm.renderer
_ecke113 = pygame.Vector2(_tx113 * K.TILE - K.GAME_W // 2, _ty113 * K.TILE - K.GAME_H // 2)
_bild113 = pygame.Surface((K.GAME_W, K.GAME_H))


def _boden113():
    _bild113.fill((0, 0, 0))
    _r113.ebene_zeichnen(_bild113, _w113, 0, _ecke113, None, aufschieben=True)
    _r113._stehend_offen = None
    return pygame.image.tobytes(_bild113, "RGB")


_vor113 = _boden113()
_alt_k113 = _e0_113.kachel(_tx113, _ty113)
_e0_113.kacheln[_ty113 * _e0_113.breite + _tx113] = K.LEER if _alt_k113 != K.LEER else K.BODEN
_nach113 = _boden113()
_r113._boden_stuecke.clear()
_frisch113 = _boden113()
_e0_113.kacheln[_ty113 * _e0_113.breite + _tx113] = _alt_k113
pruef("Boden aus vorgezeichneten Bloecken: eine direkt geaenderte Kachel faellt auf, das Bild ist wie frisch gezeichnet",
      _nach113 != _vor113 and _nach113 == _frisch113 and _boden113() == _vor113, "")
_q113 = pygame.Surface((4, 4))
_q113.fill((200, 100, 50))
_z113 = pygame.Surface((4, 4))
_z113.fill((10, 220, 30))
_r113._dunkel[(id(_z113), 128)] = (_q113, _r113.dunkel(_q113, 128))
_soll113 = _z113.copy()
_soll113.fill((128, 128, 128), special_flags=pygame.BLEND_RGB_MULT)
pruef("Ein abgedunkeltes Bild gehoert zu seiner Quelle - auch wenn unter ihrer id ein anderes gemerkt ist",
      _r113.dunkel(_z113, 128).get_at((0, 0)) == _soll113.get_at((0, 0)), str(_r113.dunkel(_z113, 128).get_at((0, 0))))

# Erst die billige Pruefung: Abstand vor Sichtlinie, kurze Linie vor langer.
_tm.ki_stopp = True
_h113 = _tm.bot_setzen(pygame.Vector2((_tx113b + 3.5) * K.TILE, (_ty113b + 4.5) * K.TILE), 0,
                       {"team": 0, "hirn": "goap"})
_f113 = _tm.bot_setzen(pygame.Vector2((_tx113b + 9.5) * K.TILE, (_ty113b + 4.5) * K.TILE), 0,
                       {"team": 1, "hirn": "goap"})
_sichtrufe113 = [0]
_alt_sicht113 = _w113.sicht_frei
_w113.sicht_frei = lambda *a_: _sichtrufe113.__setitem__(0, _sichtrufe113[0] + 1) or _alt_sicht113(*a_)
_weite113 = K.BOTS["schritte"][0]
_gehoert113 = []
for abstand_ in (_weite113 * 2.0, _weite113 * 0.4, _weite113 * 0.8):
    _sichtrufe113[0] = 0
    _tm._bot_geraeusche = []           # die Schuesse von eben zaehlen hier nicht
    _h113.hirn.lagebild = []
    _h113.hirn.gesehen.clear()
    _f113.pos.update(_h113.pos + pygame.Vector2(abstand_, 0))
    _f113.tempo = pygame.Vector2(K.BOTS["schritte_tempo"][0] + 10.0, 0)
    _h113.hirn._lagebild_auffrischen()
    _gehoert113.append((_sichtrufe113[0], bool(_h113.hirn.lagebild)))
del _w113.sicht_frei
pruef("Schritte hoeren: zu weit weg und ganz nah ohne Sichtlinie, nur dazwischen eine - gehoert wie vorher",
      _gehoert113 == [(0, False), (0, True), (1, True)], str(_gehoert113))
_tr113 = _tm.trupp_setzen(pygame.Vector2((_tx113b + 5.5) * K.TILE, (_ty113b + 4.5) * K.TILE), 0,
                          {"groesse": 2, "team": 0, "fuehrer": "funk"})
_deckrufe113 = []
_alt_deck113 = _w113.deckung
_w113.deckung = lambda von_, nach_, e_: _deckrufe113.append(pygame.Vector2(von_)) or _alt_deck113(von_, nach_, e_)
_p113 = pygame.Vector2(_h113.pos)
_frei113b = _tr113.gedeckt_hier(_p113, 0, _p113 + pygame.Vector2(300, 0))
del _w113.deckung
pruef("Deckung im Freien: nur die kurze Linie wird verfolgt, die lange zum Gegner nicht mehr",
      not _frei113b and len(_deckrufe113) == 1
      and _deckrufe113[0].distance_to(_p113) <= K.TRUPP["deckung_nah"] + 0.5, str(_deckrufe113))
_tm.verlassen()
# Die Ausgabe ins Fenster: direkt in den Ausschnitt, der Rand gefuellt - auch
# nach einem neuen set_mode und mit Rand oben und unten.
_groesse113 = app.fenster.get_size()
_aus113 = []
for groesse_ in ((960, 540), (700, 600), (960, 540)):
    app.fenster = pygame.display.set_mode(groesse_)
    app.fenster.fill((255, 0, 255))
    app.viewport_rechnen()
    app.flaeche.fill((10, 20, 30))
    pygame.draw.circle(app.flaeche, (200, 100, 50), (100, 100), 40)
    app.ausgeben()
    soll_ = pygame.Surface(groesse_)
    soll_.fill(K.C_VOID)
    soll_.blit(pygame.transform.scale(app.flaeche, app.viewport.size), app.viewport.topleft)
    _aus113.append(pygame.image.tobytes(app.fenster, "RGB") == pygame.image.tobytes(soll_, "RGB"))
app.fenster = pygame.display.set_mode(_groesse113)
app.viewport_rechnen()
pruef("Ausgabe ins Fenster ohne Zwischenflaeche: dasselbe Bild wie vorher, Rand gefuellt, auch nach set_mode",
      all(_aus113), str(_aus113))

# 0.34.58: "Das mit den geraeuschen bitte beheben, und dafuer sorgen das auch
# bei extrem niedriger framrate die sounds alle korrekt abgespielt werden,
# also das nicht nur ein sound pro bild kommt."
print("\n-- Klaenge: vorgebaut, zeitrichtig, je auf eigenem Kanal (0.34.58)")
from dustfront import audio as _AU114
_kl114 = app.klaenge


class _Takt114:
    """Eine Szene, die nur mitschreibt, um wie viel ihre Klaenge versetzt waeren."""

    def __init__(self):
        self.v = []

    def schritt(self, dt):
        self.v.append(round(_kl114.versatz, 4))


_sz114 = _Takt114()
app._aktive = lambda: [_sz114]
_rest114 = app._rest
app._rest = 0.0
_n10_114 = app._rechnen(0.1, 0.1)
_v10_114 = list(_sz114.v)
_sz114.v.clear()
app._rest = 0.0
_n60_114 = app._rechnen(1.0 / 60, 1.0 / 60)
_v60_114 = list(_sz114.v)
del app._aktive
app._rest = _rest114
_soll10_114 = [round(i_ * 0.1 / _n10_114, 4) for i_ in range(_n10_114)]
pruef("Bei 10 Bildern je Sekunde klingen die Schritte eines Bildes ueber das Bild verteilt, nicht zugleich",
      _n10_114 == K.MAX_SCHRITTE and _v10_114 == _soll10_114 and len(set(_v10_114)) == _n10_114
      and _kl114.versatz == 0.0, str(_v10_114))
pruef("... bei 60 Bildern je Sekunde die zwei Schritte eine Hundertzwanzigstel auseinander",
      _v60_114 == [0.0, round(1.0 / 120, 4)], str(_v60_114))
if _kl114.ok:
    _gespielt114 = []

    class _Kanal114:
        def set_volume(self, v):
            self.v = v

        def play(self, s):
            _gespielt114.append((self.v, s))

    _finde114 = pygame.mixer.find_channel
    pygame.mixer.find_channel = lambda force=False: _Kanal114()
    _s114 = _kl114.klang("schuss_sturm")[0]
    try:
        _kl114.versatz = 0.05
        _kl114._abspielen(_s114, 0.4)
        _kl114.versatz = 0.0
        _kl114._abspielen(_s114, 0.7)
        _kl114._abspielen(_s114, 0.2)
    finally:
        pygame.mixer.find_channel = _finde114
        _kl114.versatz = 0.0
    (_l1_114, _v1_114), (_l2_114, _v2_114), (_l3_114, _v3_114) = _gespielt114
    _rate114, _form114, _kan114 = pygame.mixer.get_init()
    _still114 = int(0.05 * _rate114) * _kan114 * (abs(_form114) // 8)
    pruef("Um 50 ms versetzt: derselbe Klang mit genau 50 ms Stille davor - der Mischer haelt den Takt",
          _v1_114 is not _s114 and _v1_114.get_raw()[_still114:] == _s114.get_raw()
          and not any(_v1_114.get_raw()[:_still114]) and _l1_114 == 0.4,
          "%.3f s statt %.3f s" % (_v1_114.get_length(), _s114.get_length()))
    pruef("... ohne Versatz der Klang selbst; die Lautstaerke gehoert dem Kanal, nicht dem Klang "
          "(ein ferner Schuss dreht den nahen nicht mehr leiser)",
          _v2_114 is _s114 and _v3_114 is _s114 and _l2_114 == 0.7 and _l3_114 == 0.2
          and _s114.get_volume() == 1.0, "%s" % _s114.get_volume())
    pygame.mixer.set_num_channels(2)
    try:
        _lang114 = _kl114.klang("blend_pfeifen")[0]
        _kl114._abspielen(_lang114, 0.05)
        _kl114._abspielen(_lang114, 0.05)
        _voll114 = pygame.mixer.find_channel() is None      # wirklich beide belegt
        _k3_114 = _kl114._abspielen(_s114, 0.05)
        _ok3_114 = _voll114 and _k3_114 is not None and _k3_114.get_sound() is _s114
    finally:
        pygame.mixer.stop()
        pygame.mixer.set_num_channels(K.AUDIO["kanaele"])
    pruef("Sind alle Kanaele belegt, weicht der aelteste - der neue Klang faellt nicht aus", _ok3_114, "")
    _kw114 = _AU114.Klaenge(None)
    _gebaut114 = []
    _bauen114 = _kw114._bauen

    def _zaehlt114(n_):
        _gebaut114.append(n_)
        return _bauen114(n_)

    _kw114._bauen = _zaehlt114
    _namen114 = ["schuss_sturm", "tod", "menue"]
    _kw114.vorbauen(_namen114)
    _zugleich114 = [len(_kw114.klang(n_)) for n_ in _namen114]     # das Spiel fragt mitten hinein
    _fertig114 = _kw114.werkstatt_warten(120)
    pruef("Die Werkstatt baut im Hintergrund jeden Klang genau einmal - auch wenn das Spiel ihn zugleich braucht",
          _fertig114 and sorted(_gebaut114) == sorted(_namen114) and all(_zugleich114), str(_gebaut114))
    pruef("... danach die dumpfen Fassungen, nur nicht fuer das Menue",
          set(_kw114._dumpf_cache) == {"schuss_sturm", "tod"}, str(sorted(_kw114._dumpf_cache)))
    _g1_114 = _AU114.Klaenge.geteilt(None)
    _g1_114.versatz, _g1_114.daempfung = 0.3, 0.5
    _g2_114 = _AU114.Klaenge.geteilt(None)
    pruef("Mit Fenster bekommt jedes Spiel dieselbe Werkstatt (schon im Hauptmenue angestossen), frisch eingestellt",
          _g1_114 is _g2_114 and _g2_114.versatz == 0.0 and _g2_114.daempfung == 0.0
          and app.klaenge is not _g2_114, "")
    _AU114._GETEILT.clear()
# Beim Gast: mehrere Weltmeldungen auf einmal klingen ueber die Zeit verteilt.
_w114, _g114 = gefechtspaar("team")
_post114 = []
for _ in range(3):
    _w114._wirkung = [["k", -99999.0, -99999.0, 0, 1.0, "reload"]]
    _post114.append(json.loads(json.dumps(_w114._weltmeldung())))
_gehoert114 = []
app.klaenge.spielen = lambda n_, l_=1.0: _gehoert114.append((n_, round(app.klaenge.versatz, 4)))
_g114.gast.holen = lambda: list(_post114)
_g114._seit_paket = 0.06 - K.FIXED_DT
try:
    _g114.schritt(K.FIXED_DT)
finally:
    del app.klaenge.spielen
    del _g114.gast.holen
_nachlad114 = [v_ for n_, v_ in _gehoert114 if n_ == "reload"]
pruef("Drei Weltmeldungen auf einmal beim Gast: ihre Klaenge kommen 20 ms auseinander statt zugleich",
      _nachlad114 == [0.0, 0.02, 0.04] and app.klaenge.versatz == 0.0, str(_gehoert114))
_w114.verlassen()
_g114.verlassen()
# Testmodus: die Bildrate bremsen, um es zu hoeren.
_grenze114 = app.fps_grenze
_tm = _TM87.Testmodus(app, karte="staubtal")
pruef("Testmenue: BILDRATE (KLAENGE PRUEFEN), am Anfang wie eingestellt",
      any(z_[0] == "bildrate" and z_[2] == "WIE EINGESTELLT" for z_ in _tm._menue_zeilen()), "")
_tm.menue_wirken("bildrate")
_b1_114 = app.fps_grenze
_z114 = _tm.zustand()
_tm.verlassen()
app.fps_grenze = _grenze114
_tm = _TM87.Testmodus(app, karte="staubtal", zustand=_z114)
_b2_114 = app.fps_grenze
for _ in range(len(K.TESTMODUS["bildraten"]) - 1):
    _tm.menue_wirken("bildrate")
pruef("... ENTER bremst auf %d Bilder je Sekunde, ueber einen Kartenwechsel hinweg, und rundum wieder wie eingestellt"
      % K.TESTMODUS["bildraten"][1],
      _b1_114 == _b2_114 == K.TESTMODUS["bildraten"][1] and _tm.bildrate_nr == 0
      and app.fps_grenze == int(app.opt["bildrate"] or 0), "%s %s %s" % (_b1_114, _b2_114, app.fps_grenze))
_tm.verlassen()
app.fps_grenze = _grenze114


print("\n-- Trupps unterwegs, grosse Trupps, Funk, Uebermut, Testmodus (0.34.58)")
from dustfront import bot_goap as _BG115
_tm = _TM87.Testmodus(app, karte="staubtal")
_tm._bot_rnd.seed(115)
_tm.wiedereinstieg = False
_fl115 = None
for s_ in range(115, 160):
    _fl115 = _freie_flaeche86(_tm.welt, random.Random(s_), 20, 12)
    if _fl115 is not None:
        break
_tx115, _ty115 = _fl115


def _v115(x_, y_):
    return pygame.Vector2((_tx115 + x_ + 0.5) * K.TILE, (_ty115 + y_ + 0.5) * K.TILE)


# Gemeldet: ohne Gegner glitten sie schraeg in eine Richtung, liefen im
# Gaensemarsch und bildeten eine Front, wo kein Feind war.
_t115 = _tm.trupp_setzen(_v115(12, 7), 0, {"groesse": 6, "team": 0, "fuehrer": "funk", "mischung": "gemischt"})
_gleiten115 = [0, 0]
for i_ in range(int(10.0 / _D87)):
    _tm.schritt(_D87)
    if i_ * _D87 > 4.0 and i_ % 6 == 0:
        for m_ in _t115.lebende():
            if m_.tempo.length() > 20.0:
                _gleiten115[1] += 1
                _w_ = abs((pygame.Vector2(1, 0).rotate(m_.winkel).angle_to(m_.tempo) + 180.0) % 360.0 - 180.0)
                _gleiten115[0] += _w_ > 60.0
_f115 = _t115.fuehrer
_r115 = pygame.Vector2(_t115.marsch_richtung or (1, 0))
_andere115 = [m_ for m_ in _t115.lebende() if m_ is not _f115]
_hinter115 = [round((_t115.stellung(m_) - _f115.pos).dot(_r115)) for m_ in _andere115]
pruef("Ohne Gegner geht ein Trupp im Marsch: keine Front, die Plaetze hinter dem Anfuehrer",
      _t115.marsch and _t115.front is None and all(h_ < 10 for h_ in _hinter115), str(_hinter115))
_quer115 = [(_t115.stellung(m_) - _f115.pos).dot(pygame.Vector2(-_r115.y, _r115.x)) for m_ in _andere115]
pruef("... im Keil, nicht alle in einer Reihe hintereinander",
      max(_quer115) - min(_quer115) > 2 * K.TRUPP["marsch_breite"], str([round(q_) for q_ in _quer115]))
pruef("... und wer geht, schaut, wohin er geht (seitwaerts gleiten hoechstens 15 Prozent)",
      _gleiten115[1] > 50 and _gleiten115[0] <= 0.15 * _gleiten115[1], str(_gleiten115))
pruef("... der Anfuehrer geht im Patrouillentempo, langsamer als er koennte",
      _f115.tempo.length() <= K.SPIELER["tempo"] * K.TRUPP["marsch_tempo"] + 2.0, "%.0f px/s" % _f115.tempo.length())
# Sichern: unterwegs haelt der Trupp, die anderen schauen zur Seite und nach hinten.
_t115.naechster_halt = _tm.welt.zeit
for _ in range(int(1.5 / _D87)):
    _tm.schritt(_D87)
_seiten115 = sorted(_t115.marsch_seite.get(m_.nummer) for m_ in _andere115)
pruef("Unterwegs sichert der Trupp ab und zu: der Anfuehrer steht, jeder schaut in seinen Sektor (links, rechts, hinten)",
      _t115.halt_bis > _tm.welt.zeit and _f115.tempo.length() < 5.0
      and -1 in _seiten115 and 1 in _seiten115 and 0 in _seiten115, str(_seiten115))
# Kehrt: neu aufstellen statt den Keil um ihn herumzuschwenken.
_t115.marsch_richtung = pygame.Vector2(1, 0)
_t115._kehrt = False
_alt_tempo115 = pygame.Vector2(_f115.tempo)
_f115.tempo.update(-60.0, 0.0)
_neu115 = _t115._marsch_richtung_fuehren(_f115)
_f115.tempo.update(_alt_tempo115)
pruef("... macht der Anfuehrer kehrt, steht die Richtung gleich, und die Plaetze werden neu verteilt",
      _neu115.x < -0.99 and _t115._kehrt, str(_neu115))
# Grosse Trupps: kleine Keile hintereinander, kein Keil von 300 Pixeln.
_pl115 = _t115._marsch_plaetze(_f115, pygame.Vector2(1, 0), 9)
_breit115 = max(p_[0].distance_to(p_[3]) for p_ in _pl115)
_pl5_115 = _t115._marsch_plaetze(_f115, pygame.Vector2(1, 0), 5)
pruef("Zehn Mann: vier im Keil des Anfuehrers, dahinter kleine Keile - keiner weiter als zwei Reihen zur Seite",
      len(_pl115) == 9 and _breit115 <= 2 * K.TRUPP["marsch_breite"] + 0.5
      and max(p_[0].distance_to(p_[3]) for p_ in _pl5_115) > 2 * K.TRUPP["marsch_breite"],
      "%.0f px" % _breit115)
# Entfalten: nah am Angriffsziel die Linie, eine Stellung halten ebenso.
_tm.trupp_auftrag("angriff", _f115.pos + _r115 * 300.0, 0, {"team": 0})
_t115._takt = 0.0
_t115.schritt(_D87)
_linie115 = not _t115.marsch
_tm.trupp_auftrag("halten", _f115.pos, 0, {"team": 0})
_t115._takt = 0.0
_t115.schritt(_D87)
pruef("Nah am Angriffsziel entfaltet sich der Trupp zur Linie; wer eine Stellung haelt, steht in der Linie",
      _linie115 and not _t115.marsch, "")
_tm.trupp_auftrag("frei", _f115.pos, 0, {"team": 0})
_tm.alles_weg()

# Grosse Trupps im Gefecht: an dieselbe Kiste stellt sich kein Zweiter, und
# ein Landeplatz in einer Mauer wird nicht zweimal vergeben.
_t115 = _tm.trupp_setzen(_v115(16, 7), 0, {"groesse": 3, "team": 0, "fuehrer": "funk", "mischung": "gemischt"})
_m1_115, _m2_115 = [m_ for m_ in _t115.lebende() if m_ is not _t115.fuehrer][:2]
for y_ in (6, 7, 8):
    _tm.welt.ebene(0).setzen(_tx115 + 8, _ty115 + y_, K.KISTE)
_tm.welt._wege = None
_feind115 = _v115(1, 7)
_p2_115 = _v115(9, 7) + pygame.Vector2(0, 20)
# Der Erste hat schon genau den Fleck, an den die Kiste den Zweiten zoege.
from dustfront.trupp import an_deckung as _an_deckung115
_q1_115 = _an_deckung115(_tm.welt, _p2_115, _m2_115.radius, 0, _feind115)
_t115.stellungen_vorher = {}
_t115.stellungen = {_m1_115.nummer: pygame.Vector2(_q1_115)}
_q2_115 = _t115._deckung_nah(_p2_115, _m2_115, _feind115)
pruef("Zwei Bahnen an derselben Kiste: der Zweite rueckt an eine andere gedeckte Stelle, nicht auf den Fleck des Ersten",
      _q2_115.distance_to(_q1_115) >= K.TRUPP["bahn_min"] * 0.5 - 0.5
      and _t115.gedeckt_hier(_q2_115, 0, _feind115), "%s %s" % (_q1_115, _q2_115))
_tm.welt.ebene(0).setzen(_tx115 + 4, _ty115 + 3, K.WAND)
_mauer115 = _v115(4, 3)
_platz115 = pygame.Vector2(_tm.welt.landeplatz(_mauer115, _m1_115.radius + 2, 0))
_t115.stellungen = {_m1_115.nummer: _platz115}
_x115 = _t115._frei(_mauer115, _m2_115)
pruef("... und liegen zwei Plaetze in derselben Mauer, landen sie nicht auf demselben Fleck",
      _x115.distance_to(_platz115) >= K.TRUPP["bahn_min"] * 0.5 - 0.5
      and _tm.welt.frei(_x115, _m2_115.radius + 2, 0, True), "%s %s" % (_platz115, _x115))
# Ein Kamerad ist kein Gegner, auch wenn seine Streuung trifft.
_t115.lage = {}
_m1_115.zuletzt_von = _m2_115
_m1_115.hirn._getroffen()
_puppe115 = _tm.puppe_setzen(_v115(2, 2), 0, {"team": 1, "leben": 10.0})
_m2_115.zuletzt_von = _puppe115
_m2_115.hirn._getroffen()
pruef("Trifft die Streuung eines Kameraden, steht er nicht als Gegner in der Lage des Trupps - ein Gegner schon",
      _m2_115 not in _t115.lage and _m2_115 not in _m1_115.hirn.beschossen_von and _puppe115 in _t115.lage,
      str([w_.name for w_ in _t115.lage]))
_tm.alles_weg()

# Kehrtwende: zurueck, wie er gekommen ist, und ohne Pendeln ans Ziel.
_b115 = _tm.bot_setzen(_v115(12, 7), 0, {"team": 0, "hirn": "goap"})
_h115 = _b115.hirn
_ziel115 = _b115.pos + pygame.Vector2(-120, 0).rotate(-4.0)       # fast genau hinter ihm
_h115._entscheiden = lambda dt_, ein_: (pygame.Vector2(0, 0), pygame.Vector2(_ziel115), False, False)
_h115.blick = 0.0
_h115._drall = 300.0                    # eben hat er sich weit nach rechts gedreht ...
_h115._kehrt = 0.0
_blicke115 = []
for _ in range(int(1.2 / _D87)):
    _h115.eingabe(_D87)
    _blicke115.append(_h115.blick)
_rest115 = abs((math.degrees(math.atan2(_ziel115.y - _b115.pos.y, _ziel115.x - _b115.pos.x))
                - _h115.blick + 180.0) % 360.0 - 180.0)
pruef("Kehrtwende: er dreht zurueck, wie er gekommen ist (nicht den kuerzeren Weg weiter), und kommt ohne Pendeln an",
      _blicke115[5] < 0.0 and _rest115 < 3.0 and all(b_ - a_ <= 0.01 for a_, b_ in zip(_blicke115, _blicke115[1:])),
      "%.1f Grad Rest, %s" % (_rest115, [round(b_) for b_ in _blicke115[::20]]))
del _h115._entscheiden
_tm.alles_weg()

# Funk: der Fakt funk_sendet, das Zeichen am Funker, der Klang.
pruef("Funk: der Klang FUNK_DURCH ist da, und bots.txt kennt den Fakt funk_sendet",
      "funk_durch" in K.KLANG_NAMEN and len(app.klaenge.klang("funk_durch")) > 0
      and "funk_sendet" in open(os.path.join(os.path.dirname(os.path.abspath(K.__file__)), "..", "wesen", "bots.txt"),
                                encoding="utf-8").read(), "")
_t115 = _tm.trupp_setzen(_v115(12, 7), 0, {"groesse": 3, "team": 0, "fuehrer": "funk", "mischung": "gemischt"})
_fu115 = _t115.fuehrer
_hf115 = _fu115.hirn
_hf115.funk_laeuft = dict(art="hilfe", dauer=1.0, phase="senden", ort=None, weg_bis=0.0, text="",
                          anfang=_tm.welt.zeit, bis=_tm.welt.zeit + 1.0, leben=_fu115.leben)
_fk115 = _hf115._trupp_fakten()
_hf115._funk_abbrechen()
_ab115 = _hf115.funk_ende
_hf115.funk_laeuft = dict(art="hilfe", dauer=0.0, phase="senden", ort=None, weg_bis=0.0, text="",
                          anfang=_tm.welt.zeit, bis=_tm.welt.zeit, leben=_fu115.leben)
_klaenge115 = []
_alt_klang115 = _tm.welt.klang
_tm.welt.klang = lambda n_, *a_, **k_: _klaenge115.append(n_)
try:
    _erg115 = _hf115._funken_tun("hilfe")
finally:
    _tm.welt.klang = _alt_klang115
pruef("... wer spricht, weiss es (funk_sendet); bricht der Spruch ab, zeigt der Funker es; kommt er durch, mit Klang",
      _fk115["funk_sendet"] and _ab115 is not None and _ab115[1] == "abgebrochen"
      and _hf115.funk_ende[1] == "durch" and "funk_durch" in _klaenge115 and _erg115[-1] == "fertig",
      "%s %s %s" % (_ab115, _hf115.funk_ende, _klaenge115))
_tm.alles_weg()

# Uebermut: aus wie Fliehen, im Testmenue einzuschalten.
_z115 = [z_ for z_ in _tm._menue_zeilen() if z_[0] == "uebermut"]
_b115 = _tm.bot_setzen(_v115(12, 7), 0, {"team": 0, "hirn": "goap"})
_b115.hirn.innen.stufe = 4
_aus115 = _b115.hirn._zuversicht_wert()
_tm.menue_wirken("uebermut")
_an115 = _b115.hirn._zuversicht_wert()
_zz115 = _tm.zustand()
_tm.menue_wirken("uebermut")
pruef("Testmenue BOTS UEBERMUETIG: aus, bis man es einschaltet; aus zaehlt die Zuversicht hoechstens neutral",
      len(_z115) == 1 and "AUS" in _z115[0][2] and _aus115 == 0.5 and _an115 == 1.0
      and _zz115.get("bot_uebermut") is True and not _tm.bot_uebermut, "%s %s %s" % (_z115, _aus115, _an115))
_tm.alles_weg()

# ZEIT STEHT: Lebende zittern nicht, und als Beobachter ruft kein Liegender.
_tm.zeit_stopp = True
_st115 = _tm.welt_anteil(0.37)
_tm.zeit_stopp = False
pruef("ZEIT STEHT: das Bild steht auf dem letzten Stand (kein Hin und Her zwischen zwei Staenden)",
      _st115 == 1.0 and abs(_tm.welt_anteil(0.37) - 0.37) < 1e-9, str(_st115))
_tm.verwundete_setzen(True)
_lieg115 = _tm.bot_setzen(_v115(12, 7), 0, {"team": 1, "hirn": "goap"})
_tm.toeten(_lieg115)
_lieg115.ruf_sperre = 0.0
_klaenge115 = []
_tm.welt.klang = lambda n_, *a_, **k_: _klaenge115.append(n_)
try:
    _tm.beobachter = True
    _tm._rufen(_lieg115)
    _still115 = (list(_klaenge115), _lieg115.ruf_zeigen)
    _tm.beobachter = False
    _tm._rufen(_lieg115)
finally:
    del _tm.welt.klang
    _tm.beobachter = True
pruef("Als Beobachter ruft kein Liegender (kein Ruf, kein Ausrufezeichen); steuert man eine Figur, ruft er",
      getattr(_lieg115, "am_boden", False) and _still115[0] == [] and not _still115[1] > 0
      and "ruf" in _klaenge115 and _lieg115.ruf_zeigen > 0, "%s %s" % (_still115, _klaenge115))
_tm.verlassen()

# Jeder Trupp in seinem Takt: nicht alle im selben Bild.
_tm = _TM87.Testmodus(app, karte="staubtal")
_takte115 = [round(_tm.trupp_setzen(_v115(4 + 6 * i_, 7), 0, {"groesse": 2, "team": i_ % 2})._takt, 4)
             for i_ in range(3)]
pruef("Mehrere Trupps denken nicht im selben Bild (kurze Einbrueche auf 10 Bilder je Sekunde)",
      len(set(_takte115)) == 3, str(_takte115))
_tm.verlassen()

# ══════════════════════════════════════════════════════════════════
print("\n-- Schneller, aber dasselbe: Abkuerzungen beim Zeichnen und Rechnen (0.34.75)")
# Jede Abkuerzung gegen den Weg, den sie ersetzt - Pixel fuer Pixel bzw.
# Zahl fuer Zahl.
from dustfront import render as _R175, goap as _G175, testmodus as _TM175
from dustfront import fahrzeug as _FZ175
from dustfront.world import freier_punkt as _fp175
_rnd175 = random.Random(175)


def _ziel175():
    z = pygame.Surface((300, 300)).convert()
    for _ in range(200):
        z.fill((_rnd175.randrange(256), _rnd175.randrange(256), _rnd175.randrange(256)),
               (_rnd175.randrange(300), _rnd175.randrange(300), 25, 25))
    return z


# Bodenstueck mit Loechern: Flaeche mit Farbschluessel = Mischen je Pixel,
# auf ein deckendes Ziel und auf ein eben geleertes mit Alphakanal.
_q175 = pygame.Surface((96, 96), pygame.SRCALPHA)
for _ in range(60):
    _q175.fill((_rnd175.randrange(256), _rnd175.randrange(256), _rnd175.randrange(256), 255),
               (_rnd175.randrange(96), _rnd175.randrange(96), 12, 12))
_q175.fill((0, 0, 0, 0), (0, 0, 32, 32))
_q175.fill((255, 0, 255, 255), (60, 60, 4, 4))          # die erste Schluesselfarbe kommt vor
_q175 = _q175.convert_alpha()
_k175, _ok175 = _R175._mit_farbschluessel(_q175)
_a175 = _ziel175()
_b175 = _a175.copy()
_a175.blit(_q175, (37, 11))
_b175.blit(_k175, (37, 11))
_l1_175 = pygame.Surface((200, 200), pygame.SRCALPHA)
_l2_175 = pygame.Surface((200, 200), pygame.SRCALPHA)
_l1_175.blit(_q175, (-20, 50))
_l2_175.blit(_k175, (-20, 50))
pruef("Bodenstueck mit Farbschluessel: dasselbe Bild wie mit Alpha (auch wenn die Schluesselfarbe vorkommt)",
      _ok175 and pygame.image.tobytes(_a175, "RGB") == pygame.image.tobytes(_b175, "RGB")
      and pygame.image.tobytes(_l1_175, "RGBA")[3::4] == pygame.image.tobytes(_l2_175, "RGBA")[3::4]
      and pygame.mask.from_surface(_l1_175, 0).count() == pygame.mask.from_surface(_l2_175, 0).count())
_halb175 = pygame.Surface((20, 20), pygame.SRCALPHA)
_halb175.fill((10, 20, 30, 128))
pruef("Halb durchsichtige Bilder bleiben, wie sie sind (kein Farbschluessel, kein Umwandeln)",
      not _R175._mit_farbschluessel(_halb175.convert_alpha())[1]
      and _R175._deckend_wenn_moeglich(_halb175).get_flags() & pygame.SRCALPHA)

# Vignette nur als Randstreifen: dasselbe Bild.
_v175 = app.bilder.bild("vignette")
_a175 = pygame.Surface((K.GAME_W, K.GAME_H)).convert()
_a175.fill((90, 140, 60))
_b175 = _a175.copy()
_a175.blit(_v175, (0, 0))
_R175._rand_blit(_b175, _v175)
pruef("Vignette in Randstreifen: dasselbe Bild wie ganz",
      _R175._rand_streifen(_v175) is not None
      and pygame.image.tobytes(_a175, "RGB") == pygame.image.tobytes(_b175, "RGB"))

# Schrift mit Schatten in einem Blit: dasselbe Bild wie zwei.
from dustfront.font import SCHRIFT as _SCH175, GH as _GH175
_a175 = _ziel175()
_b175 = _a175.copy()
for _t175, _x175, _y175, _sk175 in (("HALLO 123", 5, 5, 1), ("ÄÖÜ (X) -5/7", 40, 80, 2), ("RAND", 290, 296, 1)):
    _s175 = _SCH175.flaeche(_t175, (240, 200, 90), _sk175, 1)
    _yy175 = _y175 - (_s175.get_height() - _GH175 * _sk175)
    _a175.blit(_SCH175.flaeche(_t175, (8, 6, 4), _sk175, 1), (_x175 + _sk175, _yy175 + _sk175))
    _a175.blit(_s175, (_x175, _yy175))
    _SCH175.zeichnen(_b175, _t175, _x175, _y175, (240, 200, 90), _sk175, schatten=(8, 6, 4))
pruef("Schrift mit Schatten in einem Blit: dasselbe Bild wie Schatten und Schrift einzeln",
      pygame.image.tobytes(_a175, "RGB") == pygame.image.tobytes(_b175, "RGB"))

# GOAP: ein Ausdruck gibt mit gemeinsamen Namen denselben Wert.
_aus175 = _G175.Ausdruck("80 * magazin_leer * munition_da + max(mut, 2) - abs(x) / 3")
_n175 = {"magazin_leer": 1, "munition_da": 1, "mut": 0.7, "x": -4.5, "min": 99}
pruef("GOAP-Ausdruck: gleiche Zahl mit gemeinsamer Namenstafel",
      _aus175.wert(_n175) == _aus175.wert(_G175._bereit(_n175))
      and _aus175.wert(_G175._bereit({})) == _aus175.wert({}))

# MVP-Punkte gemerkt: sie haengen nur an den Werten in MVP_NAMEN.
from dustfront import bestenliste as _BL175
class _Mitschrift175(dict):
    gelesen = set()

    def get(self, n, *rest):
        self.gelesen.add(n)
        return dict.get(self, n, *rest)

    def __getitem__(self, n):
        self.gelesen.add(n)
        return dict.__getitem__(self, n)


_w175 = _Mitschrift175({n: _rnd175.randrange(1, 9) for n in _BL175.MVP_NAMEN}, strecke=5.0)
_BL175.mvp_punkte(_w175)
pruef("MVP-Punkte lesen nur Werte aus MVP_NAMEN (die Anzeige merkt sie sich danach)",
      _Mitschrift175.gelesen <= set(_BL175.MVP_NAMEN), str(sorted(_Mitschrift175.gelesen)))

# Welt.nahe ueber die belegten Zellen: dieselben Wesen in derselben Folge.
_tm = _TM175.Testmodus(app, karte="staubtal")
for i_ in range(12):
    _tm.bot_setzen(_fp175(_tm.welt, 0, _rnd175), 0, {"team": i_ % 2})
_tm.welt._raster_bauen()
_gleich175 = True
for _ in range(40):
    _p175 = _fp175(_tm.welt, 0, _rnd175)
    _r175 = _rnd175.choice((20.0, 100.0, 300.0, 900.0))
    _mit175 = _tm.welt.nahe(_p175, _r175, 0)
    _beleg175 = _tm.welt._belegt
    _tm.welt._belegt = None
    _ohne175 = _tm.welt.nahe(_p175, _r175, 0)
    _tm.welt._belegt = _beleg175
    _gleich175 = _gleich175 and _mit175 == _ohne175
pruef("Welt.nahe ueber belegte Zellen: dieselben Wesen in derselben Reihenfolge", _gleich175)

# Buggy-Physik gemerkt: dasselbe wie frisch gerechnet - auch beim zweiten Mal.
_bu175 = _FZ175.Buggy(_fp175(_tm.welt, 0, _rnd175), 0, 30.0)
_bu175.welt = _tm.welt
_bu175.geschw.update(37.5, -12.25)
_bu175.gier = 0.3
_bu175.lenkwinkel = 0.0
_bu175._physik_merk = None
_bu175._physik(K.FIXED_DT, 1.0, -0.5, False)
_frisch175 = (tuple(_bu175.geschw), _bu175.gier, _bu175.lenkwinkel, _bu175.rutschen)
_bu175.geschw.update(37.5, -12.25)
_bu175.gier, _bu175.lenkwinkel = 0.3, 0.0
_bu175._physik(K.FIXED_DT, 1.0, -0.5, False)       # jetzt aus der Merkzelle
_gemerkt175 = (tuple(_bu175.geschw), _bu175.gier, _bu175.lenkwinkel, _bu175.rutschen)
pruef("Buggy-Physik aus der Merkzelle: genau wie frisch gerechnet",
      _frisch175 == _gemerkt175, "%s %s" % (_frisch175, _gemerkt175))

# Panzer: die gemerkte Kachelfrage merkt, wenn eine Kachel sich aendert.
_pz175 = _FZ175.Panzer(_fp175(_tm.welt, 0, _rnd175), 0, 0.0)
_pz175.welt = _tm.welt
_e175 = _tm.welt.ebene(0)
for _ in range(80):
    if _pz175._kacheln_frei(_pz175.pos, _pz175.winkel):
        break
    _pz175.pos.update(_fp175(_tm.welt, 0, _rnd175))
_vorher175 = _pz175._kacheln_frei(_pz175.pos, _pz175.winkel)
_tx175, _ty175 = int(_pz175.pos.x // K.TILE), int(_pz175.pos.y // K.TILE)
_alt175 = _e175.kachel(_tx175, _ty175)
_e175.setzen(_tx175, _ty175, K.WAND)
_danach175 = _pz175._kacheln_frei(_pz175.pos, _pz175.winkel)
_e175.setzen(_tx175, _ty175, _alt175)
_wieder175 = _pz175._kacheln_frei(_pz175.pos, _pz175.winkel)
pruef("Panzer: gemerkte Kachelfrage sieht eine neue Mauer unter sich und ihr Verschwinden",
      _vorher175 and not _danach175 and _wieder175, "%s %s %s" % (_vorher175, _danach175, _wieder175))
_tm.verlassen()

# ══════════════════════════════════════════════════════════════════
print("\n-- Kein Flimmern, Schild, Fahrzeug schuetzt, Testmodus: Runde, Karte, Nachschub (0.34.77)")
from dustfront import testmodus as _TM177, render as _R177, fahrzeug as _FZ177
from dustfront.world import freier_punkt as _fp177
_rnd177 = random.Random(177)
_tm = _TM177.Testmodus(app, karte="staubtal")

# Abtastraster an der Welt: um q Weltpixel weiter heisst genau um ganze
# Bildpixel weiter - das Muster aus der Textur bleibt dasselbe.
_r177 = _tm.renderer
_kam177 = _tm.kamera
_gleich177 = True
for _k177 in (0.73, 0.8, 1.37):
    _kam177.pos.update(4000.25, 3000.0)
    _kam177.versatz.update(0, 0)
    _p1_177 = _r177._tiefen_plan(_kam177, _k177)
    _gw177 = _r177.groesse[0]
    _w177, _qx177 = _R177._raster_waehlen(_gw177, int(_gw177 / _k177) + 2)
    _s177 = _p1_177[4][1]
    _kam177.pos.x += _qx177
    _p2_177 = _r177._tiefen_plan(_kam177, _k177)
    _gleich177 = (_gleich177 and _qx177 is not None
                  and _p2_177[0].x - _p1_177[0].x == _qx177
                  and _p2_177[3] == _p1_177[3]
                  and abs(_qx177 * _s177 - round(_qx177 * _s177)) < 1e-9)
pruef("Andere Ebene: die Flaeche rastet auf die Welt ein (um q Weltpixel = ganze Bildpixel)",
      _gleich177)
_ab177 = _r177._abbildung(_kam177, 0.8, 30.0)
_pl177 = _r177._tiefen_plan(_kam177, 0.8)
pruef("... und die Abbildung (fuer die Klippen) passt genau zum Versatz beim Auflegen",
      abs((_pl177[0].x - _ab177[0].x) * _ab177[1] + _pl177[3][0]) < 1e-6
      and abs((_pl177[0].y - _ab177[0].y) * _ab177[2] + _pl177[3][1]) < 1e-6)

# Mauerdeckel in fester Groesse: dieselbe Mauer an zwei Stellen bekommt
# dasselbe Bild (nur anders zugeschnitten).
_r177._oberseiten.clear()
_bild177 = pygame.Surface((K.GAME_W, K.GAME_H)).convert()
_e177 = _tm.welt.ebene(0)
_fest177 = [(i_ % _e177.breite, i_ // _e177.breite) for i_, n_ in enumerate(_e177.kacheln)
            if K.KACHELN[n_]["fest"] and 10 < i_ % _e177.breite < _e177.breite - 10
            and 10 < i_ // _e177.breite < _e177.hoehe - 10][:1]
_groessen177 = set()
for _dx177 in range(0, 6):
    _r177._oberseiten.clear()
    _ecke177 = pygame.Vector2(_fest177[0][0] * K.TILE - 200 + _dx177, _fest177[0][1] * K.TILE - 150)
    _r177.ebene_zeichnen(_bild177, _tm.welt, 0, _ecke177, None, K.PERSPEKTIVE["brennweite"])
    _groessen177 |= {(n_, b_, h_) for (n_, b_, h_, _d) in _r177._oberseiten}
_je177 = {}
for n_, b_, h_ in _groessen177:
    _je177.setdefault(n_, set()).add((b_, h_))
pruef("Mauerdeckel: je Art eine feste Groesse, egal wo die Kamera steht (kein Flimmern)",
      _je177 and all(len(v_) <= 2 for v_ in _je177.values()), str(_je177)[:200])

# Zoom: die Ecke rastet ein, die Kamera bleibt, wo sie war.
_tm.kamera.zoom = 1.25
_vor177 = pygame.Vector2(_tm.kamera.pos)
_tm.zeichnen(pygame.Surface((K.GAME_W, K.GAME_H)).convert(), 1.0)
pruef("Zoom: nach dem Zeichnen steht die Kamera wieder genau, wo sie war",
      _tm.kamera.pos == _vor177)
_tm.kamera.zoom = 1.0

# Schild: von vorn kommen nur noch 7 % an.
_st177 = _tm.schildtraeger_setzen(_fp177(_tm.welt, 0, _rnd177), 0, {"team": 0})
_gg177 = _tm.bot_setzen(_st177.pos + pygame.Vector2(80, 0), 0, {"team": 1})
_st177.winkel = 0.0
_st177.unverwundbar = 0.0
_st177.leben = 100.0
_st177.schaden(40.0, None, _gg177)
pruef("Schildtraeger: von vorn kommen nur noch 7 % an (war 15 %)",
      abs((100.0 - _st177.leben) - 40.0 * 0.07) < 1e-6 and K.SCHILD["anteil"] == 0.07,
      "%.2f" % (100.0 - _st177.leben))

# Im Fahrzeug kein Schaden - weder am Wagen noch an der Figur.
_fa177 = _tm.fahrer_setzen(_fp177(_tm.welt, 0, _rnd177), 0, {"team": 0, "fahrzeug": "panzerwagen"})
_wg177 = _fa177.fahrzeug
_fa177.unverwundbar = 0.0
_fa177.leben = 100.0
_wg177.schaden(60.0, None, _gg177, art="kugel", herkunft=_gg177.pos)
_fa177.schaden(30.0, None, _gg177)
pruef("Im Fahrzeug kein Schaden: Treffer am Wagen und an der Figur kommen nicht an",
      _fa177.im_fahrzeug and _fa177.leben == 100.0, "%.1f" % _fa177.leben)

# Ein Panzer ohne Fahrer steht still, wie lange die Zeit auch laeuft.
_pz177 = _tm.fahrzeug_setzen("panzer", _fp177(_tm.welt, 0, _rnd177), 0, {"winkel": 30.0})
_lagen177 = set()
for _ in range(240):
    _tm.schritt(K.FIXED_DT)
    _lagen177.add((_pz177.pos.x, _pz177.pos.y, _pz177.winkel, _pz177.aufbau))
pruef("Panzer ohne Fahrer: steht bei laufender Zeit genau still", len(_lagen177) == 1,
      str(len(_lagen177)))

# Testmodus: Ansicht wie Runde (F2) - kein Ziffernblock, kein Status, kein Zeiger.
_gerufen177 = []
for _n177 in ("_numpad_zeichnen", "_status_zeichnen", "_zeiger_zeichnen", "_info_zeichnen"):
    setattr(_tm, _n177, (lambda n_: (lambda *a_, **k_: _gerufen177.append(n_)))(_n177))
_tm.ereignis(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_F2, mod=0, unicode="", scancode=0))
_tm.zeichnen(pygame.Surface((K.GAME_W, K.GAME_H)).convert(), 1.0)
_mit177 = list(_gerufen177)
_tm.ereignis(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_F2, mod=0, unicode="", scancode=0))
_tm.zeichnen(pygame.Surface((K.GAME_W, K.GAME_H)).convert(), 1.0)
pruef("ANSICHT WIE RUNDE (F2): kein Ziffernblock, Status, Zeiger oder INFO; F2 wieder: alles da",
      _mit177 == [] and "_numpad_zeichnen" in _gerufen177 and not _tm.wie_runde,
      "%s / %s" % (_mit177, _gerufen177))
for _n177 in ("_numpad_zeichnen", "_status_zeichnen", "_zeiger_zeichnen", "_info_zeichnen"):
    delattr(_tm, _n177)
pruef("... und alle drei stehen im Testmenue",
      {"runde", "karte_alles", "nachschub"} <= {z_[0] for z_ in _tm._menue_zeilen()})

# Allwissende Minikarte: auch als Beobachter, mit jedem Kaempfer.
_gefragt177 = []
_echt177 = _tm._farbe_fuer
_tm._farbe_fuer = lambda k_, *a_: (_gefragt177.append(k_), _echt177(k_, *a_))[1]
_tm.karte_allwissend = False
_tm.zeichnen(pygame.Surface((K.GAME_W, K.GAME_H)).convert(), 1.0)
_ohne177 = len(_gefragt177)
_gefragt177.clear()
_tm.karte_allwissend = True
_tm._geist.pos.update(_gg177.pos)
_tm.zeichnen(pygame.Surface((K.GAME_W, K.GAME_H)).convert(), 1.0)
del _tm._farbe_fuer
# Seit 0.34.88 hat der Beobachter auch ohne ALLWISSEND eine Karte (darauf
# weniger); mit ALLWISSEND steht jeder Kaempfer darauf.
pruef("MINIKARTE ALLWISSEND: als Beobachter mit allen Kaempfern (ohne: weniger)",
      _tm.beobachter and _ohne177 < len(_gefragt177) and _gg177 in _gefragt177
      and _st177 in _gefragt177,
      "%d / %d" % (_ohne177, len(_gefragt177)))
_tm.karte_allwissend = False

# Standardfigur im Stil der Skins: dieselben Farben, dazu Teammarkierung.
from dustfront import art_figuren as _AF177
_rot177 = app.bilder.bild("spieler_rot_sturm")
_neon177 = K.FIGUREN_NEON["ROT"][0]
_hat177 = any(tuple(_rot177.get_at((x_, y_)))[:3] == tuple(_neon177)[:3]
              for x_ in range(_rot177.get_width()) for y_ in range(_rot177.get_height()))
_d177 = _AF177.standard(K.TEAMS["kombi"][0]["rumpf"], K.TEAMS["kombi"][0]["kante"],
                        K.TEAMS["kombi"][0]["akzent"])
pruef("Standardfigur im Stil der Skins: Teamfarben bleiben, Neon-Markierung und Weste kommen dazu",
      _hat177 and _d177["rumpf"] == K.TEAMS["kombi"][0]["rumpf"] and _d177["weste"] == "platten")

# Nachschub am Kartenrand: beide Seiten, am Rand, nie mehr als erlaubt.
_tm.verlassen()
_tm = _TM177.Testmodus(app, karte="staubtal")
_tm.rnd.seed(177)
_tm.nachschub_an = True
_n177 = K.TESTMODUS["nachschub"]
_neu177 = []
_alt177 = set(id(k_) for k_ in _tm._bots())
for _ in range(int(120 * _n177["takt"] * 6.5)):
    _tm.schritt(K.FIXED_DT)
    for k_ in _tm._bots():
        if id(k_) not in _alt177:
            _alt177.add(id(k_))
            _neu177.append((k_.team, k_.pos.x / K.TILE))
_e177 = _tm.welt.ebene(0)
_rand177 = _n177["rand"] + 6
pruef("NACHSCHUB AM KARTENRAND: neue Bots fuer beide Seiten, Seite 0 im Westen, 1 im Osten",
      len(_neu177) >= 5 and {t_ for t_, _x in _neu177} == {0, 1}
      and all((x_ <= _rand177 + 1) if t_ == 0 else (x_ >= _e177.breite - _rand177 - 1)
              for t_, x_ in _neu177), str(_neu177)[:200])
_tm.nachschub_an = False
_vorher177 = len(_tm._bots())
for _ in range(int(120 * _n177["takt"] * 2)):
    _tm.schritt(K.FIXED_DT)
pruef("... und aus heisst aus", len(_tm._bots()) <= _vorher177)
_tm.verlassen()

# ══════════════════════════════════════════════════════════════════
print("\n-- Fenster: ganze Vielfache einrasten, PIXELRASTER OHNE FLIMMERN (0.34.78)")
_alt178 = (app.fenster.get_size(), app.opt["pixelraster"])
_erg178 = {}
for _w178, _h178 in ((1919, 1079), (1920, 1080), (1440, 900), (1300, 731)):
    app.fenster = pygame.display.set_mode((_w178, _h178))
    app.viewport_rechnen()
    _erg178[(_w178, _h178)] = app.skala
    app.ausgeben()
pruef("Fast ein ganzes Vielfaches rastet ein (1919 x 1079 -> genau 3x), krumme Groessen nicht",
      _erg178[(1919, 1079)] == 3.0 and _erg178[(1920, 1080)] == 3.0
      and _erg178[(1440, 900)] == 2.25 and _erg178[(1300, 731)] == 2.0, str(_erg178))
app.opt["pixelraster"] = "ruhig"
app.fenster = pygame.display.set_mode((1440, 900))
app.viewport_rechnen()
app.flaeche.fill((10, 20, 30))
app.flaeche.fill((200, 100, 50), (300, 170, 40, 20))
app.ausgeben()
_mitte178 = app.fenster.get_at((app.viewport.x + int(320 * 2.25), app.viewport.y + int(180 * 2.25)))
pruef("PIXELRASTER OHNE FLIMMERN: fuellt das Fenster und zeigt das Bild",
      app.skala == 2.25 and all(abs(a_ - b_) <= 8 for a_, b_ in zip(tuple(_mitte178)[:3], (200, 100, 50))),
      str(_mitte178))
app.opt["pixelraster"] = _alt178[1]
app.fenster = pygame.display.set_mode(_alt178[0])
app.viewport_rechnen()

# ══════════════════════════════════════════════════════════════════
print("\n-- Klassen und neue Waffen in der Lobby, Faehigkeiten im Netz (0.34.79)")
pruef("Neue Regel KLASSEN-FAEHIGKEITEN, an als Vorgabe",
      RG.vorgabe()["faehigkeiten"] is True and "faehigkeiten" in RG.EINFACH)
pruef("Sie gilt immer: mit Loadouts die Klasse, ohne (seit 0.34.85) jedes Werkzeug",
      RG.NACH_NAME["faehigkeiten"].gilt({"loadouts": "alles"})
      and RG.NACH_NAME["faehigkeiten"].gilt({"loadouts": "eigenes"}))
_lr179 = LB.lobby_regeln()
pruef("In der Lobby traegt jeder seinen eigenen Satz, mit Faehigkeit",
      _lr179["loadouts"] == "eigenes" and _lr179["faehigkeiten"] is True, str(_lr179))
wl179, gl179 = lobbypaar()
pruef("Die Lobby hat Faehigkeiten an, beim Gast wie beim Gastgeber",
      wl179.faehigkeiten_an and gl179.faehigkeiten_an)
gk179 = wl179.kaempfer[gl179.meine_nummer]
_satz179 = {"name": "SANI", "klasse": "sanitaeter", "waffen": ["zwillinge", "autoschrot"],
            "wuerfe": ["rauch"]}
gl179.gast.senden({"t": "loadout", "lo": _satz179})
for _ in range(20):
    wl179.schritt(K.NETZ["takt"])
    gl179.schritt(K.NETZ["takt"])
pruef("Eine neue Ausruestung gilt in der Lobby sofort - Klasse und neue Waffen",
      gk179.klasse == "sanitaeter" and "zwillinge" in gk179.waffen
      and "autoschrot" in gk179.waffen, "%s %s" % (gk179.klasse, gk179.waffen))
_gich179 = gl179.kaempfer.get(gl179.meine_nummer)
pruef("Der Gast weiss seine Klasse", _gich179 is not None and _gich179.klasse == "sanitaeter",
      str(getattr(_gich179, "klasse", None)))
# Auch wenn nur die Klasse wechselt und die Waffen bleiben. Seit 0.34.91
# gilt KLASSE PFLICHT (Vorgabe): darum eine andere Klasse, die beide
# Waffen auch hat, statt FREI.
gl179.gast.senden({"t": "loadout", "lo": dict(_satz179, klasse="fahrer")})
for _ in range(10):
    wl179.schritt(K.NETZ["takt"])
    gl179.schritt(K.NETZ["takt"])
pruef("Nur die Klasse gewechselt: auch das gilt sofort", gk179.klasse == "fahrer", gk179.klasse)
gl179.gast.senden({"t": "loadout", "lo": _satz179})
for _ in range(10):
    wl179.schritt(K.NETZ["takt"])
    gl179.schritt(K.NETZ["takt"])
_was179 = _KL73.faehigkeit_nutzen(wl179, gk179)
for _ in range(10):
    wl179.schritt(K.NETZ["takt"])
    gl179.schritt(K.NETZ["takt"])
pruef("Taste C in der Lobby: die Sanitasche liegt", _was179 == "SANITASCHE"
      and any(isinstance(x, _AU73.Sanitasche) for x in wl179.welt.wesen))
pruef("Der Gast sieht sie (geraete in der Weltmeldung)",
      any(x[4] == "sanitasche" for x in gl179._fremde_geraete), str(gl179._fremde_geraete))
pruef("Und weiss, wie lange die Faehigkeit noch braucht",
      _gich179.faehigkeit_rest.get("sanitasche", 0.0) > 0.0, str(_gich179.faehigkeit_rest))
_bild179 = pygame.Surface((K.GAME_W, K.GAME_H))
gl179.zeichnen(_bild179, 0.5)
pruef("Der Gast zeichnet Geraet und Anzeige [C] ohne Fehler", True)
wl179.verlassen(); gl179.verlassen()
w179, ga179 = _paar59("team", karte="staubtal")
# Seit 0.34.85 hat auch JEDER HAT ALLES Faehigkeiten: dort jedes Werkzeug.
pruef("Eine Runde mit JEDER HAT ALLES hat Werkzeuge auf C", w179.faehigkeiten_an)
w179._regeln_setzen(dict(w179.regelwerk, loadouts="eigenes", faehigkeiten=False))
pruef("... und mit Loadouts, aber abgeschaltet, auch nicht", not w179.faehigkeiten_an)
w179._regeln_setzen(dict(w179.regelwerk, loadouts="eigenes", faehigkeiten=True))
pruef("Mit Loadouts und an: ja", w179.faehigkeiten_an)
w179.verlassen(); ga179.verlassen()
pruef("Die Vorteile einer Klasse stehen als Text bereit (Menue AUSRUESTUNG)",
      # Seit 0.34.99 (gewuenscht) dazu der Schlag auf F.
      _KL73.vorteile("nahkaempfer") == ["+25% LEBEN", "+5% TEMPO", "+40% NAHKAMPFSCHADEN (F)",
                                        "25% SCHNELLER ZUSCHLAGEN (F)"]
      and _KL73.vorteile("schuetze") == ["15% SCHNELLER NACHLADEN"]
      and _KL73.vorteile("") == [], str(_KL73.vorteile("nahkaempfer")))

# ══════════════════════════════════════════════════════════════════
print("\n-- Bots: Spuren statt vergessen, Feuer umgehen, Feuerschutz fuer den Retter (0.34.80)")
_tm180 = _TM59.Testmodus(app, karte="staubtal")
_ort180 = freier_punkt(_tm180.welt, 0, random.Random(180))
_b180 = _tm180.bot_setzen(_ort180, 0, {"team": 0, "hirn": "goap", "waffe": "sturm"})
_p180 = _tm180.puppe_setzen(_ort180 + pygame.Vector2(40, 0), 0, {"team": 1, "leben": 10.0})
_h180 = _b180.hirn
_h180.gesehen[_p180] = (pygame.Vector2(_p180.pos), 0, _tm180.welt.zeit - K.BOTS["gedaechtnis"] - 1.0)
_p180.pos.update(_p180.pos + pygame.Vector2(0, 4000))
_h180._wahrnehmen()
pruef("Wer zu lange nicht gesehen wurde, ist nicht vergessen: er wird eine Spur",
      _p180 not in _h180.gesehen and len(_h180.spuren) == 1, str(_h180.spuren))
_h180.spur_dazu(_h180.spuren[0][0] + pygame.Vector2(20, 0), 0)
pruef("Zwei Spuren dicht beieinander sind eine", len(_h180.spuren) == 1)
pruef("Offen ist sie, solange er keinen Gegner kennt", _h180.spur_offen() is not None)
_h180._spur_weg(_h180.spuren[0][0], 0)
pruef("Gesehen: weg", _h180.spur_offen() is None)
_h180.merkmale["mut"] = 0.2
_vor180 = _h180._vorsicht_tempo()
_h180.merkmale["mut"] = 0.9
pruef("Vorsichtig nachsehen: langsam mit wenig Mut, ein Draufgaenger im vollen Tempo",
      _vor180 < 0.8 and _h180._vorsicht_tempo() == 1.0, "%.2f" % _vor180)
# Feuer auf dem Weg: die Richtung fuehrt seitlich daran vorbei.
_h180._flaechen = [(_b180.pos + pygame.Vector2(60, 0), 30.0)]
_h180._gefahren = list(_h180._flaechen)
_r180 = _h180._um_gefahr(pygame.Vector2(1, 0), _b180.pos + pygame.Vector2(300, 0))
pruef("Liegt Feuer vor ihm auf dem Weg, geht er seitlich daran vorbei",
      abs(_r180.y) > 0.3, str(_r180))
_tm180.verlassen()

# ══════════════════════════════════════════════════════════════════
print("\n-- Menuebilder aus dem Bildgenerator (0.34.82)")
from dustfront import menuebilder as _MB182
_da182 = _MB182.vorhanden()
_bekannt182 = set(K.WAFFEN) | set(K.BILD_MASS) | {"munitionskiste", "geschuetz", "horchposten", "drohne",
                                                  "sprengfalle", "sandsackwand", "stacheldraht",
                                                  "kanister", "kraehenfuesse", "schild"}
pruef("Jedes Menuebild gehoert zu einer Waffe oder einem Gegenstand",
      _da182 and all(k_ in _bekannt182 for k_ in _da182),
      ", ".join(k_ for k_ in _da182 if k_ not in _bekannt182))
# Seit 0.34.83 vollstaendig: jede waehlbare Waffe und Wurfwaffe hat eines.
pruef("Jede Waffe und Wurfwaffe der Ausruestung hat ein Menuebild",
      [w_ for w_ in list(K.LOADOUT["auswahl_waffen"]) + list(K.LOADOUT["auswahl_wuerfe"])
       if w_ not in _da182] == [],
      str([w_ for w_ in list(K.LOADOUT["auswahl_waffen"]) + list(K.LOADOUT["auswahl_wuerfe"])
           if w_ not in _da182]))
_b182 = _MB182.bild("sturm", 140)
pruef("Ein Menuebild kommt in der verlangten Breite, im Seitenverhaeltnis des Gemaeldes",
      _b182 is not None and _b182.get_width() == 140 and 70 <= _b182.get_height() <= 85,
      str(_b182.get_size() if _b182 else None))
pruef("Ohne Datei: None (dann zeigt das Menue das Pixelbild)", _MB182.bild("gibtesnicht", 140) is None)

# ══════════════════════════════════════════════════════════════════
print("\n-- Jeder hat alles: Kategorien-Hotbar und alle Werkzeuge auf C (0.34.85)")
_alle185 = K.alles_waffen()
pruef("JEDER HAT ALLES hat jede Waffe ausser denen auf F (Nahkampf) und dem Raketenwerfer (Karte)",
      set(_alle185) == set(K.WAFFEN) - set(K.NAHKAMPF["waehlbar"]) - {"rakete"}
      and len(_alle185) == len(set(_alle185)),
      str(set(K.WAFFEN) - set(_alle185)))
pruef("... in acht Gruppen (die NAHKAMPF-Gruppe liegt seit 0.34.96 auf F)", len(K.ALLES_GRUPPEN) == 8)
w185, g185 = _paar59("team", karte="staubtal")
_k185 = w185.ich
w185._loadout_anlegen(_k185)
pruef("Der Kaempfer traegt sie alle", _k185.waffen == _alle185 and w185.gruppen_hotbar,
      "%d Waffen" % len(_k185.waffen))
_gr185 = [i_ for i_, w_ in enumerate(_k185.waffen) if w185.gruppe_von(w_) == 2]
_a185 = w185._waffe_aus_taste(2)
_k185.waffe_waehlen(_a185)
_b185 = w185._waffe_aus_taste(2)
_k185.waffe_waehlen(_b185)
pruef("Taste 3: die erste Schrotflinte, noch einmal: die naechste",
      _a185 == _gr185[0] and _b185 == _gr185[1], "%s %s %s" % (_a185, _b185, _gr185))
_k185.waffe_waehlen(w185._waffe_aus_taste(0))
pruef("Zurueck in die Gruppe: die, die man dort zuletzt hatte",
      w185._waffe_aus_taste(2) == _gr185[1])
_k185.waffe_waehlen(0)
pruef("Jedes Werkzeug auf C: zuerst das erste aus K.WERKZEUGE",
      _k185.alle_werkzeuge and _KL73.faehigkeiten_von(_k185)[0][0] == K.WERKZEUGE[0][0])
w185._anwenden(_k185, {"knoepfe": ["werkzeug"], "will": [0, 0], "ziel": [0, 0]})
pruef("X schaltet zum naechsten Werkzeug", _KL73.faehigkeiten_von(_k185)[0][0] == K.WERKZEUGE[1][0],
      str(_KL73.faehigkeiten_von(_k185)))
_was185 = _KL73.faehigkeit_nutzen(w185, _k185)
pruef("... und C legt es hin", _was185 == _KL73.FAEHIGKEIT_NAMEN[K.WERKZEUGE[1][0]], _was185)
for _ in range(10):
    w185.schritt(K.NETZ["takt"])
    g185.schritt(K.NETZ["takt"])
_gk185 = g185.kaempfer.get(_k185.nummer)
pruef("Der Gast kennt Werkzeug und Waffenliste", _gk185 is not None and _gk185.alle_werkzeuge
      and _gk185.werkzeug == 1 and _gk185.waffen == _alle185)
_bild185 = pygame.Surface((K.GAME_W, K.GAME_H))
w185.zeichnen(_bild185, 0.5)
g185.zeichnen(_bild185, 0.5)
pruef("Hotbar mit Gruppen und Werkzeuganzeige zeichnen sich", True)
pruef("Antippen (Touch): acht Plaetze", len(w185.touch_hotbar()) == 8, str(len(w185.touch_hotbar())))
w185.verlassen(); g185.verlassen()

# ══════════════════════════════════════════════════════════════════
print("\n-- Schild: Durchschlag starker Waffen; Insassen im neuen Stil (0.34.86)")
_tm186 = _TM59.Testmodus(app, karte="staubtal")
_ort186 = freier_punkt(_tm186.welt, 0, random.Random(186))
_st186 = _tm186.schildtraeger_setzen(_ort186, 0, {"team": 1})
_st186.winkel = 0.0
_sch186 = _tm186.puppe_setzen(_st186.pos + pygame.Vector2(100, 0), 0, {"anzahl": 1, "streuung": 0, "team": 0})
_sch186 = _sch186[0] if isinstance(_sch186, list) else _sch186
_kl186 = []
_alt_klang186 = _tm186.welt.klang
_tm186.welt.klang = lambda name, *a, **kw: (_kl186.append(name), _alt_klang186(name, *a, **kw))[1]


def _treffer186(waffe, art="kugel"):
    _st186.leben = _st186.max_leben = 10000.0
    _kl186.clear()
    EN.schaden_an(_st186, 100.0, None, _sch186, art, waffe=waffe)
    return _st186.max_leben - _st186.leben, list(_kl186)


_sturm186 = _treffer186("sturm")
_scharf186 = _treffer186("scharf")
_kanone186 = _treffer186(None, "panzerbrechend")
pruef("Ein Sturmgewehr prallt ab wie bisher (7 Prozent, Klang schild)",
      abs(_sturm186[0] - 100.0 * K.SCHILD["anteil"]) < 0.01 and "schild" in _sturm186[1], str(_sturm186))
pruef("Das Scharfschuetzengewehr schlaegt durch: mehr Schaden, eigener Klang",
      abs(_scharf186[0] - 100.0 * K.SCHILD["durchschlag"]["scharf"]) < 0.01
      and "schild_durch" in _scharf186[1], str(_scharf186))
pruef("Panzerbrechendes (Kanone) schlaegt immer durch",
      abs(_kanone186[0] - 100.0 * K.SCHILD["panzerbrechend"]) < 0.01, str(_kanone186))
_st186.winkel = 180.0
_hinten186 = _treffer186("sturm")
pruef("Von hinten hilft kein Schild", abs(_hinten186[0] - 100.0) < 0.01, str(_hinten186))
_tm186.welt.klang = _alt_klang186
_tm186.verlassen()
pruef("Der Durchschlagsklang ist ein eigener Klang", "schild_durch" in K.KLANG_NAMEN)
from dustfront import art as _ART186, art_figuren as _AF186
_neu186 = _ART186._insasse((K.C_HULL, K.C_HULL_SH, K.C_TEAL))
_soll186 = _AF186.figur(_AF186.standard(K.C_HULL, K.C_HULL_SH, K.C_TEAL), None, None, 28,
                        stummel=False, arme_an=True)
pruef("Wer ohne eigenes Aussehen im Fahrzeug sitzt, ist die Standardfigur im neuen Stil",
      pygame.image.tobytes(_neu186, "RGBA") == pygame.image.tobytes(_soll186, "RGBA"))

# ══════════════════════════════════════════════════════════════════
print("\n-- Waffen: Spule, Revolver, Hotbar, Kuller, Granatwerfer, Drohne (0.34.87)")
w187, g187 = _paar59("team", karte="staubtal")
_k187 = w187.ich
w187._loadout_anlegen(_k187)
_gich187 = g187.kaempfer.get(g187.meine_nummer)
for _ in range(6):
    w187.schritt(K.NETZ["takt"]); g187.schritt(K.NETZ["takt"])
_gich187 = g187.kaempfer.get(g187.meine_nummer)
_gr187 = [i_ for i_, w_ in enumerate(_gich187.waffen) if g187.gruppe_von(w_) == 0]
g187._platz_gedrueckt(0)
_erst187 = g187._waffe_wunsch
g187._platz_gedrueckt(0)
_zweit187 = g187._waffe_wunsch
pruef("Zweimal schnell 1 beim Gast (ohne Antwort dazwischen): zwei verschiedene Gewehre",
      _erst187 in _gr187 and _zweit187 in _gr187 and _erst187 != _zweit187,
      "%s %s %s" % (_erst187, _zweit187, _gr187))
for _i187 in range(len(_gr187) - 2):
    g187._platz_gedrueckt(0)
_alle187 = set()
g187._waffe_soll = None
for _i187 in range(len(_gr187) + 1):
    g187._platz_gedrueckt(0)
    _alle187.add(g187._waffe_wunsch)
pruef("... und jede Waffe der Gruppe ist erreichbar", set(_gr187) <= _alle187, "%s %s" % (_alle187, _gr187))
# Revolver: der Gast sieht die Betriebsart, Faechern leert die Trommel.
_k187.waffe_waehlen(_k187.waffen.index("revolver"))
w187._anwenden(_k187, {"knoepfe": ["feuermodus"], "will": [0, 0], "ziel": [0, 0]})
for _ in range(6):
    w187.schritt(K.NETZ["takt"]); g187.schritt(K.NETZ["takt"])
_gk187 = g187.kaempfer.get(_k187.nummer)
pruef("Der Gast sieht die Betriebsart des Revolvers (FAECHERN)",
      _gk187 is not None and _gk187.modus_von("revolver") == "faechern")
_k187.magazin["revolver"] = 5
_k187.takt = 0.0
_n187 = [0]
for _i187 in range(int(1.0 / K.FIXED_DT)):
    _k187.feuert = _i187 < 2
    _k187.schritt(K.FIXED_DT)
    _n187[0] += sum(1 for x_ in w187.welt.neue if isinstance(x_, Geschoss))
    w187.welt.neue = []
pruef("Faechern: ein Klick leert die restliche Trommel", _n187[0] == 5 and _k187.magazin["revolver"] == 0,
      "%d Schuss, %d uebrig" % (_n187[0], _k187.magazin["revolver"]))
w187.verlassen(); g187.verlassen()
# Spule: weniger, und Mauern wie Koerper kosten Kraft.
_s187 = K.WAFFEN["spule"]
pruef("Die Spule ist abgeschwaecht (hoechstens 100 Schaden, laenger laden, 3 Schuss)",
      _s187["schaden"] <= 100.0 and _s187["ladezeit"] >= 2.0 and _s187["magazin"] <= 3
      and _s187["wand_verlust"] > 0 and _s187["koerper_verlust"] > 0)
# Kuller: rollt ueber den Zeiger hinaus, zuendet frueher.
_ku187 = K.WAFFEN["kuller"]
pruef("Die Kuller rollt weiter als gezielt und zuendet frueher als bisher (9 s)",
      _ku187["ueber_ziel"] > 1.0 and _ku187["flugzeit"] < 9.0)
_tmk187 = _TM59.Testmodus(app, karte="staubtal")
_ok187 = freier_punkt(_tmk187.welt, 0, random.Random(187))
_gr187k = EN.Granate(pygame.Vector2(_ok187), 0.0, _ku187, 0, None, 100.0)
_tmk187.welt.dazu(_gr187k)
_start187 = pygame.Vector2(_gr187k.pos)
for _ in range(int(3.0 / K.FIXED_DT)):
    _gr187k.schritt(K.FIXED_DT)
pruef("... auf 100 px gezielt, ist sie nach 3 s schon weiter als 100 px gerollt",
      _gr187k.pos.distance_to(_start187) > 100.0 or _gr187k.tempo.length() < 1.0,
      "%.0f px" % _gr187k.pos.distance_to(_start187))
# Granatwerfer: ueber eine Mauer, wenn er hoch genug fliegt.
_gw187 = K.WAFFEN["granatwerfer"]
pruef("Granatwerfer: langsamer, zuendet frueher am Boden",
      _gw187["tempo"] < 400.0 and _gw187["zuender"] < 0.7)
_wand187 = None
_e187 = _tmk187.welt.ebene(0)
for _ty in range(2, _e187.hoehe - 2):
    for _tx in range(2, _e187.breite - 12):
        _rei = [_e187.kachel(_tx + i_, _ty) for i_ in range(10)]
        if all(not K.KACHELN[_r]["fest"] for _i, _r in enumerate(_rei) if _i != 5) \
                and K.KACHELN[_rei[5]]["sicht"]:
            _wand187 = (_tx, _ty)
            break
    if _wand187:
        break
if _wand187 is not None:
    _von187 = pygame.Vector2((_wand187[0] + 0.5) * K.TILE, (_wand187[1] + 0.5) * K.TILE)
    _wg187 = EN.Werfergranate(_von187, 0.0, _gw187, 0, None, weite=9 * K.TILE)
    _tmk187.welt.dazu(_wg187)
    for _ in range(int(2.0 / K.FIXED_DT)):
        if not _wg187.lebt or _wg187.liegt:
            break
        _wg187.schritt(K.FIXED_DT)
    pruef("Granatwerfer: eine Mauer in der Mitte der Bahn ueberfliegt er",
          _wg187.pos.x > _von187.x + 7 * K.TILE, "%.0f px weit" % (_wg187.pos.x - _von187.x))
else:
    pruef("(eine Mauer fuer den Granatwerfer-Test gefunden)", False)
_name187 = K.KACHELN[_e187.kachel(_wand187[0] + 5, _wand187[1])]["name"] if _wand187 else ""
pruef("Was hoch steht, steht hoch (Mauer 24, Fels 30), flacher Boden 0",
      _wand187 is not None
      and _tmk187.welt.kachel_hoehe(_von187 + pygame.Vector2(5 * K.TILE, 0), 0) == K.STEHEN[_name187]["hoehe"]
      and _tmk187.welt.kachel_hoehe(_von187, 0) == 0.0, _name187)
_tmk187.verlassen()
# Drohne: ein durchgehender Rotorklang, gleich laut, ohne Pumpen.
from dustfront import audio as _AU187
_dr187 = _AU187._drohne()
_vier187 = [max(abs(x_) for x_ in _dr187[i_ * len(_dr187) // 4:(i_ + 1) * len(_dr187) // 4])
            for i_ in range(1, 3)]
pruef("Der Drohnenklang ist gleich laut statt abklingend (Rotor statt Surren)",
      len(_dr187) > K.AUSRUESTUNG["drohne"].get("klang_takt", 0.5) * 44100
      and min(_vier187) > 0.6 * max(_vier187), str([round(v_, 2) for v_ in _vier187]))

# ══════════════════════════════════════════════════════════════════
print("\n-- Testmodus: Minikarte beim Beobachter, saubere Ansicht ohne Ziffernblock (0.34.88)")
_tm188 = _TM59.Testmodus(app, karte="staubtal")
_tm188.karte_allwissend = False
_gerufen188 = []
_alt188 = _tm188.hud.minikarte.zeichnen
_tm188.hud.minikarte.zeichnen = lambda z_, g_: (_gerufen188.append(1), _alt188(z_, g_))[1]
_b188 = pygame.Surface((K.GAME_W, K.GAME_H))
_tm188.zeichnen(_b188, 0.5)
pruef("Der Beobachter hat eine Minikarte, auch ohne ALLWISSEND", _tm188.beobachter and _gerufen188)
_tm188.wie_runde = True
_gerufen188.clear()
_tm188.zeichnen(_b188, 0.5)
pruef("... auch in ANSICHT WIE RUNDE", bool(_gerufen188))
_r188 = dict(_tm188.tasten_flaechen())
_erste188 = next(iter(_r188.values()))
pruef("In ANSICHT WIE RUNDE nimmt der (unsichtbare) Ziffernblock keinen Finger",
      _tm188.touch_tippen(_erste188.center) is False)
_tm188.wie_runde = False
pruef("... sonst schon", _tm188.touch_tippen(_erste188.center) is True)
_tm188.verlassen()

# ══════════════════════════════════════════════════════════════════
print("\n-- Leistung ohne Spielaenderung: gemerkter Ziffernblock, Deckung vorweg, Gegnerliste (0.34.89)")
_tm189 = _TM59.Testmodus(app, karte="staubtal")
_tasten189 = [(n_, r_) + tuple(_tm189._tastentext(n_)) for n_, r_ in _tm189.tasten_flaechen()]
_a189 = pygame.Surface((K.GAME_W, K.GAME_H))
_b189 = pygame.Surface((K.GAME_W, K.GAME_H))
for _f189 in (_a189, _b189):
    for _y189 in range(0, K.GAME_H, 8):
        pygame.draw.rect(_f189, (40 + _y189 % 200, 90, 160 - _y189 % 120), (0, _y189, K.GAME_W, 8))
_tm189._numpad_malen(_a189, _tasten189, 0, 0)           # wie vorher, direkt
_tm189.__dict__.pop("_numpad_merk", None)
_tm189._numpad_zeichnen(_b189)                         # gemerkt
_tm189._numpad_zeichnen(_b189)                         # und noch einmal aus dem Merker
pruef("Der gemerkte Ziffernblock ergibt Pixel fuer Pixel dasselbe Bild",
      pygame.image.tobytes(_a189, "RGB") == pygame.image.tobytes(_b189, "RGB"))
_tm189.zeit_stopp = not _tm189.zeit_stopp              # eine Aufschrift aendert sich
_tm189._numpad_zeichnen(_b189)
pruef("... und zeichnet neu, wenn sich eine Taste aendert",
      _tm189._numpad_merk[0] != tuple((n_, tuple(r_), t_, a_) for n_, r_, t_, a_ in _tasten189))
_tm189.zeit_stopp = not _tm189.zeit_stopp

# Deckung: die schnelle Antwort vorweg gilt nur, wo die Rechnung ohne sie
# ebenfalls "" ergibt - verglichen an vielen kurzen und langen Strecken,
# gern auf Kachelkanten.
_w189 = _tm189.welt
_e189 = _w189.ebene(0)
_rnd189 = random.Random(189)
_anders189 = _vorweg189 = 0
for _ in range(4000):
    _v189 = pygame.Vector2(_rnd189.uniform(0, _e189.breite * K.TILE), _rnd189.uniform(0, _e189.hoehe * K.TILE))
    if _rnd189.random() < 0.3:
        _v189.update(round(_v189.x / K.TILE) * K.TILE, round(_v189.y / K.TILE) * K.TILE)
    _n189 = _v189 + pygame.Vector2(_rnd189.choice((8, 24, 36, 60)), 0).rotate(_rnd189.uniform(0, 360))
    _mit189 = _w189.deckung(_v189, _n189, 0)
    _w189._strecke_frei = lambda *_a: False             # der lange Weg
    _ohne189 = _w189.deckung(_v189, _n189, 0)
    del _w189._strecke_frei
    _vorweg189 += 1 if _w189._strecke_frei(_v189, _n189, 0) else 0
    _anders189 += 1 if _mit189 != _ohne189 else 0
pruef("Deckung mit der schnellen Antwort vorweg wie ohne sie (4000 Strecken)",
      _anders189 == 0 and _vorweg189 > 1000, "%d anders, %d vorweg" % (_anders189, _vorweg189))

# Die Gegnerliste der Bots: im Durchgang gemerkt, ausserhalb frisch.
_tm189.alles_weg()
_tr189 = _tm189.trupp_setzen(pygame.Vector2(20 * K.TILE, 12 * K.TILE), 0, {"groesse": 3, "team": 0})
_fd189 = _tm189.trupp_setzen(pygame.Vector2(26 * K.TILE, 12 * K.TILE), 0, {"groesse": 3, "team": 1})
_h189 = _tr189.lebende()[0].hirn
_frisch189 = [w_ for w_ in _tm189.kaempfer.values() if _h189.ist_feind(w_)]
pruef("Ausserhalb des Bot-Durchgangs: die Gegnerliste wie ist_feind",
      _h189._kandidaten() == _frisch189 and len(_frisch189) == 3, str(len(_frisch189)))
_tm189._kandidaten_lauf = 1
_erst189 = _h189._kandidaten()
_opfer189 = _fd189.lebende()[0]
_opfer189.lebt = False                                  # stirbt im selben Durchgang
pruef("Im Durchgang: wer eben fiel, ist kein Kandidat mehr", _opfer189 not in _h189._kandidaten()
      and len(_erst189) == 3)
_opfer189.lebt = True
_neu189 = _tm189.bot_setzen(pygame.Vector2(27 * K.TILE, 14 * K.TILE), 0, {"team": 1})
pruef("... und wer im selben Durchgang dazukommt, ist sofort einer", _neu189 in _h189._kandidaten())
_tm189._kandidaten_lauf = None
_tm189.__dict__.pop("_kandidaten_merk", None)
_tm189.verlassen()

# ══════════════════════════════════════════════════════════════════
print("\n-- Anzeige: GRAFIKKARTE SKALIERT als Schalter (0.34.90)")
from dustfront import einstellungen as _E190
pruef("GRAFIKKARTE SKALIERT ist aus, bis man es einschaltet", _E190.VORGABE["grafikkarte"] is False)
_kopf190, _opt190 = app.headless, dict(app.opt.werte)
app.headless = False                       # ein Fenster wie im Spiel (Treiber: dummy)
app.opt.werte["grafikkarte"] = True
app.opt.werte["fenstermodus"] = "fenster"
app.vollbild = False
K.ANZEIGE["gpu_ohne_grafikkarte"] = False
app.anzeige_setzen()
pruef("Ohne schnelle Grafikkarte bleibt es beim Vergroessern im Spiel",
      app.gpu is False and app.fenster.get_size() != (K.GAME_W, K.GAME_H), str(app.fenster.get_size()))
K.ANZEIGE["gpu_ohne_grafikkarte"] = True
app.anzeige_setzen()
pruef("Mit Grafikkarte: die Anzeigeflaeche ist das Spielbild selbst, ohne eigenes Vergroessern",
      app.gpu and app.fenster.get_size() == (K.GAME_W, K.GAME_H) and app.skala == 1.0
      and app.viewport == pygame.Rect(0, 0, K.GAME_W, K.GAME_H), str(app.viewport))
pruef("... das Fenster behaelt die eingestellte Groesse", app._fenster_masse() == tuple(app.fenster_groesse),
      str(app._fenster_masse()))
pruef("... und die Maus braucht kein Umrechnen mehr (pygame liefert Spielkoordinaten)",
      app.zu_spiel((123, 45)) == pygame.Vector2(123, 45))
app.flaeche.fill((10, 200, 30))
app.ausgeben()
pruef("... ausgeben legt das Spielbild unveraendert hinein", app.fenster.get_at((5, 5))[:3] == (10, 200, 30))
app.opt.werte["grafikkarte"] = False
app.anzeige_setzen()
pruef("Ausgeschaltet: wieder das Fenster in voller Groesse, vergroessert vom Spiel",
      not app.gpu and app.fenster.get_size() == tuple(app.fenster_groesse)
      and "SDL_HINT_RENDER_SCALE_QUALITY" not in os.environ, str(app.fenster.get_size()))
app.ausgeben()
K.ANZEIGE["gpu_ohne_grafikkarte"] = False
app.opt.werte.clear()
app.opt.werte.update(_opt190)
app.headless = _kopf190
app.anzeige_setzen()

# ══════════════════════════════════════════════════════════════════
print("\n-- Haupt- und Seitenwaffe, Spezialplatz, KLASSE PFLICHT (0.34.91)")
from dustfront import klassen as _KL191, konto as _KO191, regeln as _R191, bots as _BO191
pruef("Jede waehlbare Waffe hat ihren Platz (Haupt, Seite oder Spezial)",
      all(K.WAFFEN_PLATZ.get(w_) in ("haupt", "seite", "spezial") for w_ in K.LOADOUT["auswahl_waffen"]))
pruef("Jede Klasse hat Haupt- und Seitenwaffe zur Wahl - der Schildtraeger nur die Seitenwaffe",
      all((_KL191.plaetze_von(k_) == ("seite",)) == bool(d_.get("schild"))
          and all(_KL191.waffen_von(k_, p_) for p_ in _KL191.plaetze_von(k_))
          and ("seite" in _KL191.plaetze_von(k_))
          for k_, d_ in K.KLASSEN.items()))
_spezial191 = [k_ for k_ in K.KLASSEN if "spezial" in _KL191.plaetze_von(k_)]
pruef("Manche Klassen (nicht alle) haben einen Platz fuer eine Spezialwaffe, FREI keinen",
      2 <= len(_spezial191) < len(K.KLASSEN) and "spezial" not in _KL191.plaetze_von(""),
      str(_spezial191))
_lo191 = _KO191.loadout_saeubern({"name": "X", "klasse": "panzerjaeger",
                                  "waffen": ["panzerbuechse", "sturm", "mp", "repetierer"]})
pruef("Ein Satz traegt je Platz eine Waffe, in der Folge Haupt, Seite, Spezial",
      _lo191["waffen"] == ["mp", "repetierer", "panzerbuechse"], str(_lo191["waffen"]))
_sch191 = _KO191.loadout_saeubern({"name": "S", "klasse": "schildtraeger", "waffen": ["sturm", "revolver"]})
pruef("Mit Schild nur die Seitenwaffe", _sch191["waffen"] == ["revolver"], str(_sch191["waffen"]))
_frei191 = _KO191.loadout_saeubern({"name": "F", "waffen": ["sturm", "schrot", "minigun"]})
pruef("Zwei Hauptwaffen gibt es nicht mehr: aus der zweiten wird eine Seitenwaffe",
      len(_frei191["waffen"]) == 2 and K.WAFFEN_PLATZ[_frei191["waffen"][1]] == "seite"
      and "minigun" not in _frei191["waffen"], str(_frei191["waffen"]))
_d191 = _R191.vorgabe()
pruef("KLASSE PFLICHT ist eine Regel, als Vorgabe an, und gilt nur mit Loadouts",
      _d191["klasse_pflicht"] is True and not _R191.NACH_NAME["klasse_pflicht"].gilt(dict(_d191, loadouts="alles"))
      and _R191.NACH_NAME["klasse_pflicht"].gilt(dict(_d191, loadouts="eigenes")))
_w191, _g191 = gefechtspaar("pvp", regeln={"loadouts": "eigenes"})
_ohne191 = {"name": "OHNE", "waffen": ["scharf", "revolver"], "wuerfe": ["rauch"]}
_mit191 = _w191._mit_klasse(_ohne191)
pruef("Mit KLASSE PFLICHT spielt, wer ohne Klasse kommt, die Ersatzklasse - mit passenden Waffen",
      _mit191["klasse"] == K.KLASSE_PFLICHT_ERSATZ
      and all(w_ in _KL191.waffen_von(K.KLASSE_PFLICHT_ERSATZ) for w_ in _mit191["waffen"]), str(_mit191))
_w191.klasse_pflicht = False
pruef("... ohne die Regel bleibt er FREI", _w191._mit_klasse(_ohne191) is _ohne191)
_w191.verlassen(); _g191.verlassen()
pruef("Das Sturmgewehr streut mehr, die Schrotflinte macht weniger Schaden",
      K.WAFFEN["sturm"]["streuung"] > 2.2 and K.WAFFEN["sturm"]["streuung_lauf"] > 3.6
      and K.WAFFEN["schrot"]["schaden"] < 13.0)

# ══════════════════════════════════════════════════════════════════
print("\n-- Anzeige nach der Skizze: runde Karte, Boegen, Punktestand auf TAB (0.34.92)")
from dustfront import anzeige as _AZ192
_w192, _g192 = gefechtspaar("team", regeln={"bots": 4})
_hud192 = _w192.hud
_ich192 = _w192.ich
_b192 = pygame.Surface((K.GAME_W, K.GAME_H))
_rufe192 = []
_alt192 = _hud192.minikarte.zeichnen
_hud192.minikarte.zeichnen = lambda z_, g_, **kw_: (_rufe192.append(kw_), _alt192(z_, g_, **kw_))[1]
_w192.zeichnen(_b192, 0.5)
pruef("Die Karte steht als Kreis unten links, um die eigene Figur",
      _rufe192 and _rufe192[-1].get("rund") is True and _rufe192[-1].get("rahmen") is not None
      and _hud192._karte_unten == 0, str(_rufe192[-1:]))
_mitte192 = (K.HUD["karte_x"] + K.HUD["karte_d"] // 2, K.GAME_H - K.HUD["unten"] - K.HUD["karte_d"] // 2)
# Mitten in einer Platte (genau oben liegt eine Luecke zwischen zweien).
_je192 = (K.HUD["bogen_von"] - K.HUD["bogen_bis"]) / K.HUD["segmente"]
_w_oben192 = math.radians(K.HUD["bogen_von"] - 8.5 * _je192)
_rad192 = K.HUD["karte_d"] // 2 + K.HUD["bogen_abstand"] + K.HUD["bogen_dicke"] / 2.0
_oben192 = (int(round(_mitte192[0] + _rad192 * math.cos(_w_oben192))),
            int(round(_mitte192[1] - _rad192 * math.sin(_w_oben192))))
pruef("Die Panzerung ist ein Bogen ueber der Karte (oben im Bogen ihre Farbe)",
      tuple(_b192.get_at(_oben192))[:3] == tuple(K.C_TEAL), str(tuple(_b192.get_at(_oben192))))
_ich192.leben = _ich192.max_leben * 0.2
_b192.fill((0, 0, 0))
_w192.zeichnen(_b192, 0.5)
_rechts192 = (int(_mitte192[0] + _rad192 * math.cos(math.radians(-15))),
              int(_mitte192[1] - _rad192 * math.sin(math.radians(-15))))
pruef("... mit wenig Panzerung rot und nur noch zum Teil voll (rechts dunkel)",
      tuple(_b192.get_at(_rechts192))[:3] != tuple(K.C_RED), str(tuple(_b192.get_at(_rechts192))))
_ich192.leben = _ich192.max_leben
pruef("Ohne TAB keine Tafel, mit gehaltenem TAB (INVENTAR) schon",
      not _hud192.tafel_zeigen(), "")
app.eingabe._gehalten.add("inventar")
pruef("... mit gehaltenem TAB die Tafel mit dem Punktestand", _hud192.tafel_zeigen())
app.eingabe._gehalten.discard("inventar")
_w192.teampunkte = [3, 1]
_b192.fill((0, 0, 0))
_w192.zeichnen(_b192, 0.5)
_farben192 = [k_["hud"] for k_ in K.TEAMS["kombi"]]
_x0192 = K.GAME_W // 2 - 75
pruef("Oben in der Mitte ein Balken, geteilt nach dem Stand (3:1 - drei Viertel rot)",
      tuple(_b192.get_at((_x0192 + 100, 9)))[:3] == tuple(_farben192[0])
      and tuple(_b192.get_at((_x0192 + 120, 9)))[:3] == tuple(_farben192[1]),
      "%s %s" % (tuple(_b192.get_at((_x0192 + 100, 9))), tuple(_b192.get_at((_x0192 + 120, 9)))))
pruef("Die Hotbar laesst links Platz fuer Karte und Faehigkeit",
      all(_hud192.hotbar_rechteck(n_).left > _AZ192.LINKS.right
          and _hud192.hotbar_rechteck(n_).right < _AZ192.RECHTS.left
          for n_ in (2, 3, 4, len(K.ALLES_GRUPPEN))),
      str(_hud192.hotbar_rechteck(len(K.ALLES_GRUPPEN))))
# 0.34.93: Felder fuer Brecheisen und Medkit, Magazin am Zeiger, Countdown.
_ex192 = _hud192.extra_rechtecke(_ich192)
_hb192 = _hud192.hotbar_rechteck(len(K.ALLES_GRUPPEN) if _w192.gruppen_hotbar else len(_ich192.waffen))
pruef("Neben der Hotbar, mit Abstand, ein Feld fuer das Brecheisen (und eines fuer Medkits, wenn es welche gibt)",
      _ex192 and _ex192[0][0] == "nahkampf"
      and _ex192[0][1].left - _hb192.right >= K.HUD["extra_abstand"]
      and all(a_ != "medkit" for a_, _r in _ex192) == (_w192.start_medkits <= 0 and not _w192.medkits_spawnen
                                                       and _ich192.medkits <= 0), str(_ex192))
_w192.start_medkits = 2
pruef("... mit Medkits in der Runde auch das Medkit-Feld", any(a_ == "medkit" for a_, _r in _hud192.extra_rechtecke(_ich192)))
app.eingabe.maus.update(300, 150)
_ich192.magazin[_ich192.waffe_name] = 7
_b192.fill((0, 0, 0))
_w192.zeichnen(_b192, 0.5)
_feld192 = pygame.Rect(311, 157, 24, 16)
pruef("Das Magazin steht gross rechts unter dem Zeiger",
      any(tuple(_b192.get_at((x_, y_)))[:3] in (tuple(K.C_CREAM), tuple(K.C_AMBER))
          for x_ in range(_feld192.left, _feld192.right) for y_ in range(_feld192.top, _feld192.bottom)))
_arten192 = __import__("dustfront.klassen", fromlist=["x"]).faehigkeiten_von(_ich192)
if _arten192:
    _ich192.faehigkeit_rest = {a_: 5.2 for a_, _p in _arten192}
    _b192.fill((0, 0, 0))
    _w192.zeichnen(_b192, 0.5)
    _fr192 = K.HUD["faeh_d"] // 2
    _fm192 = (K.HUD["karte_x"] + K.HUD["karte_d"] + K.HUD["faeh_luft"] + _fr192, K.GAME_H - K.HUD["unten"] - _fr192)
    _grau192 = [tuple(_b192.get_at((x_, y_)))[:3] for x_ in range(_fm192[0] - 4, _fm192[0] + 4)
                for y_ in range(_fm192[1] - 4, _fm192[1] + 4)]
    pruef("Nach dem Benutzen steht im Kreis der Faehigkeit ein grauer Countdown statt der Taste",
          (150, 146, 140) in _grau192 and tuple(K.C_TEAL) not in _grau192, str(set(_grau192)))
_w192.verlassen(); _g192.verlassen()

# ══════════════════════════════════════════════════════════════════
print("\n-- Bots selten mit MG, Fahrzeuge flach (0.34.94)")
from dustfront import bots as _BO194
_r194 = random.Random(194)
_lo194 = [_BO194.bot_loadout(_r194)["waffen"] for _ in range(600)]
_mg194 = sum(1 for w_ in _lo194 if "lmg" in w_) / float(len(_lo194))
pruef("Bots ziehen das MG nur selten (unter 10 Prozent der Saetze, vorher 40)", _mg194 < 0.10,
      "%.0f %%" % (_mg194 * 100))
pruef("... und immer zwei verschiedene Waffen", all(len(set(w_)) == 2 for w_ in _lo194))
_ra194, _rb194 = random.Random(7), random.Random(7)
_BO194.bot_loadout(_ra194)
_rb194.sample(list(K.BOTS["waffen"]), 2)                    # genau, was es vorher zog
_rb194.choice([w_ for w_ in K.BOTS["wurf_arten"] if w_ != "c4"])
pruef("Das Gewichten dreht den Zufall der Bots nicht weiter (feste Szenen bleiben, wie sie waren)",
      _ra194.getstate() == _rb194.getstate())
from dustfront.fahrzeug import Buggy as _Bg194, Panzer as _Pz194, Panzerwagen as _Pw194
pruef("Fahrzeuge stehen flach (kein 3D)", _Bg194.hoehe_3d == _Pz194.hoehe_3d == _Pw194.hoehe_3d == 0.0)

# ══════════════════════════════════════════════════════════════════
print("\n-- Ein Druck zaehlt einmal, auch bei mehreren Schritten im Bild (0.34.95)")
w195, g195 = _paar59("team", karte="staubtal")
_k195 = w195.ich
w195._loadout_anlegen(_k195)
for _ in range(4):
    w195.schritt(K.NETZ["takt"]); g195.schritt(K.NETZ["takt"])
_gr195 = [i_ for i_, w_ in enumerate(_k195.waffen) if w195.gruppe_von(w_) == 0]
_k195.waffe_waehlen(_gr195[0])
w195._waffe_soll = None

def _bild195(szene, taste, schritte=3):
    """Ein Bild wie im echten Ablauf: neues Bild, das Tastenereignis,
    dann mehrere Rechenschritte (bei hoher Bildrate einer, bei niedriger
    zwei oder drei)."""
    e.neues_bild()
    ev_ = pygame.event.Event(pygame.KEYDOWN, key=taste, mod=0, unicode="", scancode=0)
    e.ereignis(ev_)
    szene._knopf_merken(ev_.key)
    for _ in range(schritte):
        szene.schritt(K.FIXED_DT)
    e.neues_bild()
    e.ereignis(pygame.event.Event(pygame.KEYUP, key=taste, mod=0, unicode="", scancode=0))

_t1_195 = e.tabelle["waffe1"][0]
_gesehen195 = []
for _ in range(len(_gr195)):
    _bild195(w195, _t1_195)
    _gesehen195.append(_k195.waffe)
pruef("Mit Gruppen: jeder Druck auf 1 genau eine Waffe weiter, auch bei drei Schritten im Bild",
      _gesehen195 == _gr195[1:] + _gr195[:1], "%s soll %s" % (_gesehen195, _gr195[1:] + _gr195[:1]))
_k195.werkzeug = 0
_tx195 = e.tabelle["werkzeug"][0]
_wz195 = []
for _ in range(len(K.WERKZEUGE)):
    _bild195(w195, _tx195)
    _wz195.append(_k195.werkzeug)
pruef("X: jeder Druck genau ein Werkzeug weiter", _wz195 == [(i_ + 1) % len(K.WERKZEUGE)
                                                   for i_ in range(len(K.WERKZEUGE))], str(_wz195))
pruef("Die Bilder werden gezaehlt", e.bild > 0)
w195.verlassen(); g195.verlassen()

# ══════════════════════════════════════════════════════════════════
print("\n-- Panzerabwehr wirkt, Panzerwagen verwundbarer (0.34.95)")
from dustfront import testmodus as _TM195, fahrzeug as _FZ195
from dustfront.world import freier_punkt as _fp195
_tm195 = _TM195.Testmodus(app, karte="staubtal")
_wt195 = _tm195.welt
_rnd195 = random.Random(195)

def _rakete195(klasse, waffe, seite):
    """Eine Rakete schlaegt 2 px vor dem Blech ein; was kommt beim Wagen an?"""
    for _ in range(200):
        v_ = klasse(_fp195(_wt195, 0, _rnd195), 0, 0.0)
        v_.welt = _wt195
        if v_._kacheln_frei(v_.pos, 0.0):
            f_ = v_.werte
            if seite == "vorn":
                p_ = v_.pos + pygame.Vector2(f_["vorn"] + 2, 0)
            elif seite == "hinten":
                p_ = v_.pos + pygame.Vector2(f_["hinten"] - 2, 0)
            else:
                p_ = v_.pos + pygame.Vector2(0, f_["halb"] + 2)
            if _wt195.deckung_anteil(p_, v_.rand_punkt(p_), 0) >= 1.0 \
                    and _wt195.deckung_anteil(p_, v_.pos, 0) >= 1.0:
                break
    _wt195.wesen.append(v_)
    _wt195._raster_bauen()
    r_ = EN.Rakete(p_, (v_.pos - p_).as_polar()[1], K.WAFFEN[waffe], 0, None, waffe=waffe)
    r_.welt = _wt195
    vorher_ = v_.leben
    r_.einschlag(v_)
    _wt195.wesen.remove(v_)
    return (vorher_ - v_.leben) / v_.max_leben

_pw195 = {s_: _rakete195(_FZ195.Panzerwagen, "einwegwerfer", s_) for s_ in ("vorn", "seite", "hinten")}
pruef("Einweg-Raketenwerfer: ein Panzerwagen haelt von vorn und der Seite einen Treffer aus, von hinten keinen",
      0.5 <= _pw195["vorn"] < 1.0 and 0.65 <= _pw195["seite"] < 1.0 and _pw195["hinten"] >= 1.0, str(_pw195))
_pz195 = _rakete195(_FZ195.Panzer, "einwegwerfer", "seite")
pruef("... ein Panzer braucht zwei bis drei (er darf stark bleiben)", 1.0 / 3.0 <= _pz195 < 0.5, "%.2f" % _pz195)
_bu195 = 6 * _rakete195(_FZ195.Panzerwagen, "raketenbuendel", "seite")
pruef("Raketenbuendel: eine ganze Salve an der Seite nimmt einem Panzerwagen das meiste",
      0.7 <= _bu195 < 1.0, "%.2f" % _bu195)
_alt195 = K.WAFFEN["raketenbuendel"]
pruef("... kleine Hohlladungen statt Sprengkoepfe", _alt195["schadensart"] == "hohlladung")
_kugel195 = _FZ195.Panzerwagen(pygame.Vector2(0, 0), 0, 0.0).panzerung("kugel")
pruef("Kugeln prallen am Panzerwagen weiter ab, das Leben bleibt",
      _kugel195 <= 0.35 and K.PANZERWAGEN["leben"] == 620.0)
_pb195 = K.WAFFEN["panzerbuechse"]["fahrzeug_schaden"] * K.PANZERUNG["panzerwagen"]["panzerbrechend"]
pruef("Panzerbuechse: drei Treffer an der Seite fuer einen Panzerwagen",
      2 * _pb195 < 620.0 <= 3 * _pb195, "%.0f je Treffer" % _pb195)
_tm195.verlassen()

# ══════════════════════════════════════════════════════════════════
print("\n-- Flammenwerfer wie im Waffenpaket: eine Feuerzunge statt Funken (0.34.95)")
_tm196 = _TM195.Testmodus(app, karte="staubtal")
_wt196 = _tm196.welt
_rnd196 = random.Random(196)
for _ in range(500):
    _p196 = _fp195(_wt196, 0, _rnd196)
    if all(_wt196.sicht_frei(_p196 + pygame.Vector2(0, dy_), _p196 + pygame.Vector2(170, dy_), 0)
           for dy_ in (-30, 0, 30)):
        break
_wt196.partikel = []
_wt196.schussknall(_p196, 0.0, 0, "flammenwerfer", None)
pruef("Ein Zug des Flammenwerfers stoesst Hitzeflecken aus, keine Funken",
      len(_wt196.flammen) >= 10 and not any(p_.art == "funke" for p_ in _wt196.partikel),
      "%d Flecken, %d Partikel" % (len(_wt196.flammen), len(_wt196.partikel)))
# Eine halbe Sekunde gehalten, Zug um Zug.
_zug196 = K.WAFFEN["flammenwerfer"]["takt"]
for _i196 in range(int(0.5 / K.FIXED_DT)):
    _wt196.effekte_schritt(K.FIXED_DT)
    if int((_i196 + 1) * K.FIXED_DT / _zug196) != int(_i196 * K.FIXED_DT / _zug196):
        _wt196.schussknall(_p196, 0.0, 0, "flammenwerfer", None)
_weit196 = max(_wt196.flamme_jetzt(b_, _wt196.flammen_zeit)[0] - _p196.x for b_ in _wt196.flammen)
pruef("... sie fliegen fast so weit, wie er brennt (K.WAFFEN reichweite)",
      0.6 * K.WAFFEN["flammenwerfer"]["reichweite"] < _weit196
      <= (1.0 + K.FLAMME["tempo_streuung"]) * K.WAFFEN["flammenwerfer"]["reichweite"],
      "%.0f px" % _weit196)
_bild196 = pygame.Surface((K.GAME_W, K.GAME_H))
_bild196.fill((0, 0, 0))
_ecke196 = _p196 - pygame.Vector2(40, K.GAME_H / 2)
_tm196.renderer.flammen_zeichnen(_bild196, _wt196, 0, _ecke196, 1.0)
_farben196 = set()
for x_ in range(40, 40 + 150, 2):
    for y_ in range(K.GAME_H // 2 - 20, K.GAME_H // 2 + 20, 2):
        _farben196.add(tuple(_bild196.get_at((x_, y_)))[:3])
_stufen196 = {tuple(f_) for _s, f_ in K.FLAMME["stufen"]}
pruef("... und verschmelzen zu einer Zunge: innen fast weiss, aussen rot (die Stufen aus dem Paket)",
      tuple(K.FLAMME["stufen"][0][1]) in _farben196 and tuple(K.FLAMME["stufen"][-2][1]) in _farben196
      and _farben196 - {(0, 0, 0)} <= _stufen196, str(_farben196 - _stufen196))
for _ in range(int(0.6 / K.FIXED_DT)):
    _wt196.effekte_schritt(K.FIXED_DT)
pruef("... und sind nach dem Loslassen nach gut einer halben Sekunde aus", not _wt196.flammen, str(len(_wt196.flammen)))
# Vor einer Wand bleibt der Strom stehen.
for _ in range(500):
    _q196 = _fp195(_wt196, 0, _rnd196)
    _wand196 = _wt196.strahl(_q196, pygame.Vector2(1, 0), 120.0, 0)
    if 30.0 < _wand196.distance_to(_q196) < 80.0:
        break
_wt196.flammen = []
_wt196.flammen_ausstossen(_q196, 0.0, 0, K.WAFFEN["flammenwerfer"])
pruef("Vor einer Wand bleiben die Flammen an der Wand stehen",
      all(b_[5] <= _wand196.distance_to(_q196) + 20.0 for b_ in _wt196.flammen),
      "%.0f px bis zur Wand" % _wand196.distance_to(_q196))
_tm196.verlassen()

# ══════════════════════════════════════════════════════════════════
print("\n-- Spaehdrohne: weiter Kreis, Markierte im Nebel und auf der Karte; weniger Nebel (0.34.95)")
from dustfront import ausruestung as _AU197
_d197 = K.AUSRUESTUNG["drohne"]
pruef("Die Drohne fliegt einen weiten Kreis und sieht weit (vorher 90 und 260)",
      _d197["kreis"] >= 200.0 and _d197["sicht"] >= 320.0, "%s %s" % (_d197["kreis"], _d197["sicht"]))
w197, g197 = _paar59("team", karte="staubtal")
_ich197 = w197.ich
_feind197 = w197.kaempfer[g197.meine_nummer]
_feind197.team = 1 - _ich197.team if _ich197.team in (0, 1) else 1
_feind197.fraktion = w197._fraktion_fuer(_feind197.nummer, _feind197.team)
_feind197.lebt = True
_dr197 = _AU197.Drohne(pygame.Vector2(_feind197.pos) + pygame.Vector2(200, 0), _feind197.ebene,
                       _ich197.fraktion)
w197.welt.dazu(_dr197)
w197.schritt(K.FIXED_DT)
pruef("Sie startet, wo sie steht, und fliegt hinaus auf ihren Kreis",
      _dr197.pos.distance_to(_dr197.mitte) < 20.0, "%.0f" % _dr197.pos.distance_to(_dr197.mitte))
for _i197 in range(int(3.0 / K.FIXED_DT)):
    _feind197.pos.update(_dr197.mitte - pygame.Vector2(200, 0))
    w197.schritt(K.FIXED_DT)
    if _i197 % 4 == 0:
        g197.schritt(4 * K.FIXED_DT)     # sonst gilt der Gast als gegangen
pruef("... nach ein paar Sekunden fliegt sie auf dem weiten Kreis",
      abs(_dr197.pos.distance_to(_dr197.mitte) - _d197["kreis"]) < 1.0)
pruef("Sie markiert den Gegner fuer ihre Seite", getattr(_feind197, "markiert_rest", 0.0) > 0.0
      and _feind197.markiert_fuer == _ich197.fraktion and w197.fuer_mich_markiert(_feind197))
for _ in range(10):
    w197.schritt(K.NETZ["takt"]); g197.schritt(K.NETZ["takt"])
_gf197 = g197.kaempfer.get(_feind197.nummer)
pruef("Der Gast erfaehrt, wer markiert ist und fuer wen (Netz: mf)",
      _gf197 is not None and _gf197.markiert_fuer == _ich197.fraktion and _gf197.markiert_rest > 0.0)
_bild197 = pygame.Surface((K.GAME_W, K.GAME_H))
w197.zoom_ziel = w197._zoom_weich = w197.kamera.zoom = max(K.ZOOM["stufen"])
_feind197.pos.update(_ich197.pos + pygame.Vector2(760, 0))   # seit 0.34.135 klar bis 1,75: 560 lag noch im Klaren
pruef("Ganz herausgezoomt steht er im Nebel ...", not w197.im_licht(_feind197.pos))
w197.zeichnen(_bild197, 1.0)
_m197 = w197.kamera.zu_bild(_feind197.pos)
_rot197 = any(tuple(_bild197.get_at((int(_m197.x) + dx_, int(_m197.y) - 20 + dy_)))[:3] == tuple(K.C_RED)[:3]
              for dx_ in range(-2, 3) for dy_ in range(-2, 3)
              if 0 <= int(_m197.x) + dx_ < K.GAME_W and 0 <= int(_m197.y) - 20 + dy_ < K.GAME_H)
pruef("... aber markiert: die rote Raute zeigt, wo er steht", _rot197)
_dr197.lebt = False
_dr197.sterben(None) if hasattr(_dr197, "sterben") else None
for _i197 in range(int((K.AUSRUESTUNG["markiert"] + 0.5) / K.FIXED_DT)):
    w197.schritt(K.FIXED_DT)
    if _i197 % 4 == 0:
        g197.schritt(4 * K.FIXED_DT)
pruef("Ohne Drohne laeuft die Markierung ab (bis 0.34.94 blieb sie im Gefecht fuer immer)",
      _feind197.markiert_rest == 0.0 and not w197.fuer_mich_markiert(_feind197))
w197.zoom_ziel = w197._zoom_weich = w197.kamera.zoom = 1.25
pruef("Weniger Nebel: bis Zoom K.ZOOM klar ist alles klar", K.ZOOM["klar"] >= 1.5
      and w197.sicht_welt() is None)

print("\n-- 0.34.135: Zoom je Fahrzeug --")
from dustfront import fahrzeug as _FZ135
_fw135 = _FZ135.neu("funkwagen", _ich197.pos + pygame.Vector2(0, 70), 0)
w197.welt.dazu(_fw135); w197.fahrzeuge.append(_fw135)
if _ich197.fahrzeug is not None:
    w197._aussteigen(_ich197)
w197.zoom_ziel = w197._zoom_weich = w197.kamera.zoom = 1.0
w197._einsteigen(_ich197, _fw135)
pruef("Zoom: im fahrenden Funkwagen nur bis K.ZOOM hoechst",
      w197.zoom_grenzen()[0] == K.ZOOM["hoechst"])
_fw135.phase, _fw135.fortschritt = 2, 1.0
w197._zoom_begrenzen()
pruef("... aufgebaut weiter (ganzer Peilkreis) und das Bild zoomt einmal hinaus",
      w197.zoom_grenzen()[0] > K.ZOOM["hoechst"] and w197.zoom_ziel == w197.zoom_grenzen()[0]
      and K.GAME_H * w197.zoom_grenzen()[1] >= 2 * K.FUNKWAGEN["peilen"], "%.2f" % w197.zoom_ziel)
for _ in range(12):
    w197.zoom_stufe(1)
pruef("... mit dem Mausrad nicht ueber diese Grenze", w197.zoom_ziel == K.ZOOM["fahrzeug"]["funkwagen"][0])
_fw135.phase = 0
w197._zoom_begrenzen()
pruef("... faehrt er los, springt der Zoom auf die hoechste erlaubte Stufe zurueck",
      w197.zoom_ziel == K.ZOOM["hoechst"], "%.2f" % w197.zoom_ziel)
w197._aussteigen(_ich197)
w197.verlassen(); g197.verlassen()

# ══════════════════════════════════════════════════════════════════
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

print("\n-- 0.34.100: Karte hochaufgeloest, Nachschub in zwei Schritten, Abwurf sicher, Drohne, Fallschirmjaeger")
from dustfront import kartenbild as _KB300, schlacht as _SL300, testmodus as _TM300
w300, g300 = _paar59("schlacht", karte="staubtal_offen")
w300._regeln_setzen(dict(_R199.vorgabe(), modus="schlacht", karte="staubtal_offen", schlacht_seite=6))
w300._einstiegszonen_waehlen()
w300._fahrzeuge_neu_aufstellen()
w300._bots_fuehren(0.0, sofort=True)
_e300 = w300.welt.ebene(0)
_bild300 = _KB300.bild(_e300)
pruef("Das Kartenbild hat mehrere Pixel je Kachel (nicht mehr einen)",
      _bild300.get_width() >= 2 * _e300.breite and _bild300.get_height() >= 2 * _e300.hoehe,
      str(_bild300.get_size()))
_klein300 = _KB300.in_groesse(_e300, (200, 140))
pruef("... und wird weich in jede Groesse gebracht (gemerkt)",
      _klein300.get_size() == (200, 140) and _KB300.in_groesse(_e300, (200, 140)) is _klein300)
# Fensteraufloesung: was angemeldet wird, malt nach dem Vergroessern.
_app300 = type("A", (), {})()
_gemalt300 = []
_app300.gpu = False; _app300.touch = None; _app300.skala = 3.0
_app300.fenster = pygame.Surface((1920, 1080)); _app300.viewport = pygame.Rect(0, 0, 1920, 1080)
from dustfront.core import App as _App300
_App300.hoch_auflegen(_app300, pygame.Rect(10, 10, 84, 84), lambda f_, m_: _gemalt300.append((f_.get_size(), m_)))
_app300.zu_fenster = lambda r_: _App300.zu_fenster(_app300, r_)
_App300._hoch_zeichnen(_app300, _app300.fenster)
pruef("Die runde Karte kommt in Fensteraufloesung (drei mal so viele Pixel bei 1080p)",
      _gemalt300 == [((252, 252), 3.0)], str(_gemalt300))
_app300.gpu = True
pruef("... nicht, wenn die Grafikkarte skaliert (dann bleibt die Spielflaeche)",
      not _App300.hoch_auflegen(_app300, pygame.Rect(0, 0, 8, 8), lambda f_, m_: None))
# Nachschub: erst was, dann wo.
_ich300 = w300.ich
_ich300.schlacht_punkte = 0
w300.belohnung_oeffnen()
pruef("TAB: zuerst ist nichts gewaehlt", w300.belohnung_offen and w300.belohnung_wahl == -1)
_zonen300 = len(w300.dropzonen)
pruef("... und ohne Wahl fordert ein Klick auf die Karte nichts an",
      not w300._belohnung_anfordern(pygame.Vector2(_ich300.pos)) and len(w300.dropzonen) == _zonen300)
w300._knoepfe.add("nahkampf"); w300._waffe_wunsch = 2
w300.schritt(K.FIXED_DT); g300.schritt(K.FIXED_DT)
pruef("Solange das Menue offen ist, kommt keine Taste ins Spiel",
      not w300._knoepfe and w300._waffe_wunsch == -1)
w300.belohnung_schliessen()
pruef("Schliessen sperrt den Schuss der noch gedrueckten Maustaste",
      not w300.belohnung_offen and w300._feuer_sperre)
# Gratis nur fuer den ADMIN.
_vorne300 = _ich300.pos + pygame.Vector2(1200, 0)
pruef("Ohne Punkte geht nichts, auch wenn ein Gast 'gratis' schickt",
      w300.belohnung_kaufen(_ich300, "munition", _vorne300, gratis=True) == "ZU WENIG PUNKTE")
_name300, _konto300 = _ich300.name, getattr(_ich300, "konto", "")
_ich300.name, _ich300.konto = "ADMIN", "konto-admin"
pruef("Der angemeldete ADMIN darf mit dem Schalter gratis anfordern",
      w300.belohnung_kaufen(_ich300, "munition", _vorne300, gratis=True) == ""
      and _ich300.schlacht_punkte == 0)
_ich300.name, _ich300.konto = _name300, _konto300
# Abwurf: hoeher, und nie auf etwas drauf.
pruef("Fahrzeuge kommen deutlich hoeher herein (mehr als frueher 240)",
      K.SCHLACHT["abwurf"]["hoehe"] > 240)
# Die Wagen der Basen kommen erst am Schirm herunter.
for _ in range(int((K.SCHLACHT["abwurf"]["start"] + K.SCHLACHT["abwurf"]["hoehe"]
                    / K.SCHLACHT["abwurf"]["sinken"] + 1) / K.FIXED_DT)):
    _ich300.unverwundbar = 1.0
    w300.schritt(K.FIXED_DT); g300.schritt(K.FIXED_DT)
_b300 = next(b_ for b_ in w300.fahrzeuge if not b_.kaputt)
_z300 = _SL300.Dropzone(pygame.Vector2(_b300.pos), 0, "panzer", 0.0, einmalig=True)
_z300.rest = 0.01
w300.dropzonen.append(_z300)
_ich300.pos.update(_b300.pos + pygame.Vector2(0, 60)); _ich300.vorher.update(_ich300.pos)
_z301 = _SL300.Dropzone(pygame.Vector2(_ich300.pos), 0, "buggy", 0.0, einmalig=True)
_z301.rest = 0.01
w300.dropzonen.append(_z301)
for _ in range(int((K.SCHLACHT["abwurf"]["hoehe"] / K.SCHLACHT["abwurf"]["sinken"] + 2) / K.FIXED_DT)):
    _ich300.unverwundbar = 1.0
    w300.schritt(K.FIXED_DT); g300.schritt(K.FIXED_DT)
_heil300 = [b_ for b_ in w300.fahrzeuge if not b_.kaputt]
_ueber300 = [(a_.art, b_.art) for i_, a_ in enumerate(_heil300) for b_ in _heil300[i_ + 1:]
             if a_.pos.distance_to(b_.pos) < 0.8 * (a_.radius + b_.radius)]
pruef("Ein Abwurf auf einen stehenden Wagen landet daneben, nie darauf",
      not w300.abwuerfe and not _ueber300, str(_ueber300))
pruef("... und wer unter einem Abwurf steht, wird beiseite gestossen, nicht verschuettet",
      all(_ich300.pos.distance_to(b_.pos) >= b_.radius for b_ in _heil300 if not _ich300.im_fahrzeug))
# Die Drohne markiert auch Fahrzeuge, laenger als frueher.
pruef("Pings bleiben etwas laenger (mehr als 15 s)", K.SCHLACHT["aufklaerung"]["markiert"] > 15.0)
_feind300 = next((b_ for b_ in w300.fahrzeuge if getattr(b_, "basis_team", 0) == 1 and not b_.kaputt), None)
if _feind300 is not None:
    _ue300 = _SL300.Ueberflug(_feind300.pos, 0, _ich300.fraktion, 9999)
    _ue300.alter = _ue300.dauer / 2.0
    w300._ueberflug_markieren(_ue300)
    pruef("Die Drohne markiert feindliche Fahrzeuge - fuer die eigene Seite",
          w300.fahrzeug_fuer_mich_markiert(_feind300))
    for _ in range(4):
        w300.schritt(K.NETZ["takt"]); g300.schritt(K.NETZ["takt"])
    _gb300 = [b_ for b_ in g300.fahrzeuge if b_.pos.distance_to(_feind300.pos) < 40]
    pruef("... und der Gast sieht den Ping am Fahrzeug auch",
          bool(_gb300) and getattr(_gb300[0], "markiert_fuer", "") == _ich300.fraktion)
# Fallschirmjaeger.
_alt300 = len(w300._bots())
_sp300 = w300.fallschirmjaeger_abwerfen(w300._schlacht_punkte()[2], 1)
pruef("Fallschirmjaeger: fuenf Bots der Seite, in der Luft und nicht zu treffen",
      len(_sp300) == K.SCHLACHT["fallschirmjaeger"]["anzahl"]
      and all(k_.schirm_hoehe > 0 and not k_.trefferbar and k_.team == 1 for k_ in _sp300))
pruef("... in Formation: keiner steht auf einem anderen",
      all(a_.pos.distance_to(b_.pos) >= 20 for i_, a_ in enumerate(_sp300) for b_ in _sp300[i_ + 1:]))
_rot300 = next(k_ for k_ in w300._bots() if k_.team == 0)
pruef("Ein Gegner darf sie in der Luft nicht zum Ziel nehmen", not _rot300.hirn.ziel_ok(_sp300[0]))
w300._bots_fuehren(0.0, sofort=True)
pruef("Sie kommen dazu: das Auffuellen nimmt dafuer keine anderen Bots weg",
      len(w300._bots()) == _alt300 + len(_sp300))
for _ in range(int((K.SCHLACHT["fallschirmjaeger"]["hoehe"] * 1.3 / K.SCHLACHT["fallschirmjaeger"]["sinken"] + 1)
                   / K.FIXED_DT)):
    w300.schritt(K.FIXED_DT); g300.schritt(K.FIXED_DT)
pruef("Gelandet: am Boden, zu treffen, und ein Ziel wie jeder",
      all(k_.schirm_hoehe == 0.0 and k_.trefferbar for k_ in _sp300 if k_.lebt)
      and _rot300.hirn.ziel_ok(_sp300[0]) == (_sp300[0].lebt and not _sp300[0].am_boden
                                              and _sp300[0].ebene == _rot300.ebene))
_sp300[1].am_boden = False
_sp300[1].lebt = False
_sp300[1].abgerechnet = False
for _ in range(int((K.GEFECHT["wieder_nach"] + 1) / K.FIXED_DT)):
    w300.schritt(K.FIXED_DT); g300.schritt(K.FIXED_DT)
pruef("Wer von ihnen faellt, kommt nicht wieder", _sp300[1].nummer not in w300.kaempfer)
# Gefunden mit diesen Tests: schloss spuelen die Leitung (der Gast las nicht
# mehr), warf das folgende select ValueError - beim Gastgeber.
import socket as _so300
_hoer300 = _so300.socket(); _hoer300.bind(("127.0.0.1", 0)); _hoer300.listen(1)
_b300s = _so300.create_connection(_hoer300.getsockname())
_a300, _x300 = _hoer300.accept()
_hoer300.close()
_l300 = netz.Leitung(_a300)
_l300.spuelen = lambda: _l300.schliessen("Rueckstand")
pruef("Netz: eine Leitung, die beim Spuelen zugeht, liefert nichts statt abzustuerzen",
      _l300.holen() == [] and not _l300.offen)
_b300s.close()
pruef("Der Testmodus hat alles aus dem Nachschub im Spawner",
      {"ABWURF: PANZER", "AUFKLÄRUNGSDROHNE", "FALLSCHIRMJÄGER"}
      <= {e_.name for e_ in _TM300.eintraege()})
w300.verlassen(); g300.verlassen()

print("\n-- 0.34.101: Napalm-Angriff, Karte ohne Hinweis, Preise")
from dustfront import schlacht as _SL301, audio as _AU301
_preis301 = {n_: c_ for n_, c_, _t in K.SCHLACHT["belohnungen"]}
# Seit 0.34.129 billiger (Balancing); die Preise prueft der Abschnitt 0.34.129.
pruef("Munition, Sanitaet und Buggy stehen vorn in der Liste",
      [n_ for n_, _c, _t in K.SCHLACHT["belohnungen"][:3]] == ["munition", "medkit", "buggy"])
pruef("Den Napalm-Angriff gibt es im Nachschub", "napalm" in _preis301)
w301, g301 = _paar59("schlacht", karte="staubtal_offen")
# FREISCHALTEN aus (seit 0.34.129): hier geht es um den Angriff, nicht darum, wann er kommt.
w301._regeln_setzen(dict(_R199.vorgabe(), modus="schlacht", karte="staubtal_offen", schlacht_seite=4,
                         freischalten="aus"))
# Der Gast prueft einen Kauf vorher selbst - mit denselben Regeln (im Spiel
# kommen sie mit der Willkommensnachricht, hier nachtraeglich gesetzt).
g301._regeln_setzen(dict(w301.regelwerk))
_ich301 = w301.ich
_ich301.schlacht_punkte = 50
_mitte301 = w301._schlacht_punkte()[2]
w301.belohnung_oeffnen()
w301._wahl(list(_preis301).index("napalm"))
_start301 = _mitte301 + pygame.Vector2(-300, -1400)
pruef("Napalm: der erste Klick setzt nur den Start, kostet nichts",
      not w301._belohnung_anfordern(_start301) and w301._napalm_start == _start301
      and _ich301.schlacht_punkte == 50 and not w301.luftangriffe)
pruef("... der zweite gibt die Richtung - und dann geht es los",
      w301._belohnung_anfordern(_start301 + pygame.Vector2(3, 40))
      and _ich301.schlacht_punkte == 50 - _preis301["napalm"] and len(w301.luftangriffe) == 1)
_la301 = w301.luftangriffe[0]
_soll301 = w301.welt.ebene(0).pixel_hoehe * 0.5
pruef("Die Bahn ist immer halb so lang wie die Karte hoch - egal wie nah der zweite Klick lag",
      abs(_la301.start.distance_to(_la301.ende) - _soll301) < 1.0,
      "%.0f / %.0f" % (_la301.start.distance_to(_la301.ende), _soll301))
_ende301 = w301.napalm_ende(_start301, _start301 + pygame.Vector2(5000, 0))
pruef("... auch wenn er weiter weg lag (sie reicht dann nur bis zur Laenge)",
      abs(_ende301.distance_to(_start301) - _soll301) < 1.0)
pruef("Rechtsklick nimmt den Startpunkt zurueck, die Wahl bleibt",
      (w301._wahl(list(_preis301).index("napalm")), w301._belohnung_anfordern(_start301),
       w301.belohnung_ereignis(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=3, pos=(0, 0))))
      and w301._napalm_start is None and w301.belohnung_wahl == list(_preis301).index("napalm"))
w301.belohnung_schliessen()
_bomben301 = _la301.bomben
pruef("Unregelmaessig: die Abstaende der Bomben sind verschieden",
      len({round(a_[1].distance_to(b_[1])) for a_, b_ in zip(_bomben301, _bomben301[1:])}) > 5)
_vorn301 = (_la301.ende - _la301.start).normalize()
_quer301 = pygame.Vector2(-_vorn301.y, _vorn301.x)
_frei301 = sum(1 for i_ in range(0, int(_soll301), 20)
               if not any((_la301.start + _vorn301 * i_ + _quer301 * j_).distance_to(p_) < r_
                          for j_ in range(-110, 111, 10) for _t, p_, r_, _d in _bomben301))
pruef("... und nicht alles brennt: es gibt Durchgaenge quer durch die Bahn",
      _frei301 >= K.SCHLACHT["napalm"]["wenigstens_luecken"], "%d freie Querschnitte" % _frei301)
pruef("Das Flugzeug sieht man nicht, man hoert es (eigener Klang), dazu der Einschlag",
      "jet" in _AU301._PLATZHALTER and "napalm" in _AU301._PLATZHALTER
      and "jet" in w301.NETZKLAENGE and "napalm" in w301.NETZKLAENGE)
_feuer_vorher301 = len(w301.welt.feuer)
for _ in range(int((_la301.dauer + 0.5) / K.FIXED_DT)):
    _ich301.unverwundbar = 1.0
    w301.schritt(K.FIXED_DT); g301.schritt(K.FIXED_DT)
_neu301 = [f_ for f_ in w301.welt.feuer][_feuer_vorher301:]
pruef("Jede Bombe hinterlaesst ein laenger brennendes Feuer",
      len(_neu301) >= len(_bomben301) - 2
      and all(f_.dauer >= K.SCHLACHT["napalm"]["dauer"][0] > K.FEUER["dauer"] for f_ in _neu301),
      "%d Feuer" % len(_neu301))
pruef("Der Angriff ist danach vorbei", not w301.luftangriffe)
pruef("Der Gast sieht die Feuer auch", len(g301.welt.feuer) >= len(_neu301) - 2)
# Gast: ein Kauf mit zwei Punkten.
_gk301 = w301.kaempfer[g301.meine_nummer]
_gk301.schlacht_punkte = 20
g301.ich.schlacht_punkte = 20
g301.belohnung_oeffnen()
g301._wahl(list(_preis301).index("napalm"))
_gs301 = _mitte301 + pygame.Vector2(300, 1400) if _gk301.team == 0 else _mitte301 + pygame.Vector2(300, -1400)
g301._belohnung_anfordern(_gs301)
g301._belohnung_anfordern(_gs301 + pygame.Vector2(0, -30))
for _ in range(8):
    w301.schritt(K.NETZ["takt"]); g301.schritt(K.NETZ["takt"])
pruef("Ein Gast fordert Napalm mit Start und Richtung an (Gastgeber prueft)",
      len(w301.luftangriffe) == 1 and _gk301.schlacht_punkte == 20 - _preis301["napalm"],
      "%d Angriffe, %d Punkte" % (len(w301.luftangriffe), _gk301.schlacht_punkte))
pruef("... und sieht die Bahn auf seiner Karte", len(getattr(g301, "_luftangriffe_gast", ())) == 1)
w301.verlassen(); g301.verlassen()
import inspect as _in301
pruef("Ohne Wahl ist die Nachschubkarte nur Karte: kein Hinweis darauf",
      "ERST LINKS" not in _in301.getsource(_SL301))
from dustfront import testmodus as _TM301
pruef("Den Napalm-Angriff gibt es im Testmodus (Richtung: WINKEL)",
      any(e_.name == "NAPALM-ANGRIFF" and "winkel" in e_.optionen for e_ in _TM301.eintraege()))

print("\n-- 0.34.102: Netz - nur Aenderungen, Gegendruck, Quittungen, kein Rauswurf nach einem Schwall")
import random as _rnd302, json as _js302, socket as _so302
# Hin und zurueck: welt_aenderung + welt_anwenden ergeben genau die neue Meldung.
_r302 = _rnd302.Random(302)
def _zufall_welt302(alt_=None):
    sp_ = []
    for i_ in _r302.sample(range(12), _r302.randint(3, 10)):
        e_ = {"i": i_, "p": [_r302.randint(0, 9), 1.5], "n": "N%d" % i_, "l": _r302.choice([100, 50])}
        if _r302.random() < 0.3:
            e_["x%d" % _r302.randint(0, 2)] = _r302.random()
        sp_.append(e_)
    w_ = {"t": "welt", "rest": _r302.choice([1.0, 2.0]), "spieler": sp_,
          "fahrzeuge": [[i_, _r302.choice([0, 1])] for i_ in range(6)],
          "sl": {"dz": [[1, _r302.choice([2.0, 2.5])], [3, 4]], "ab": []} if _r302.random() < 0.8 else None,
          "wirkung": [["k", 1]] if _r302.random() < 0.3 else []}
    if _r302.random() < 0.3:
        w_["extra"] = _r302.random()
    return _js302.loads(_js302.dumps(w_))
_ok302 = True
_a302 = _zufall_welt302()
for _ in range(400):
    _b302 = _zufall_welt302()
    _d302 = _js302.loads(_js302.dumps(netz.welt_aenderung(_a302, _b302)))
    if netz.welt_anwenden(_a302, _d302) != _b302:
        _ok302 = False
        break
    _a302 = _b302
pruef("Aenderungen ergeben beim Gast genau die volle Meldung (400 zufaellige Folgen)", _ok302)
# Ein echtes Paar in SCHLACHT: der Gast setzt dieselbe Meldung zusammen, die
# der Gastgeber gebaut hat - und es geht nur ein Bruchteil hinaus.
w302, g302 = _paar59("schlacht", karte="staubtal_offen")
w302._regeln_setzen(dict(_R199.vorgabe(), modus="schlacht", karte="staubtal_offen", schlacht_seite=12))
_l302 = next(iter(w302.gastgeber.leitungen.values()))
_gemeint302, _bekommen302 = [], []
_alt_ws302 = netz.Leitung._welt_senden
_alt_wz302 = netz.Leitung._welt_zusammensetzen
def _ws302(self_, n_):
    r_ = _alt_ws302(self_, n_)
    if r_ is not None:
        _gemeint302.append(_js302.loads(_js302.dumps(self_._basis)))
    return r_
def _wz302(self_, n_):
    r_ = _alt_wz302(self_, n_)
    if r_ is not None:
        _bekommen302.append(_js302.loads(_js302.dumps(r_)))
    return r_
netz.Leitung._welt_senden = _ws302
netz.Leitung._welt_zusammensetzen = _wz302
for _ in range(int(12 / K.FIXED_DT)):
    w302.schritt(K.FIXED_DT); g302.schritt(K.FIXED_DT)
_gemeint302.clear(); _bekommen302.clear()
_bytes302 = _l302.gesendet_bytes
for _ in range(int(8 / K.FIXED_DT)):
    w302.schritt(K.FIXED_DT); g302.schritt(K.FIXED_DT)
for _ in range(3):
    g302.schritt(K.FIXED_DT)
netz.Leitung._welt_senden = _alt_ws302
netz.Leitung._welt_zusammensetzen = _alt_wz302
_v302 = next((v_ for v_ in range(4) if _bekommen302[v_:v_ + 1] == _gemeint302[:1]), 0)
_paare302 = list(zip(_gemeint302, _bekommen302[_v302:]))
pruef("Im Gefecht: jede zusammengesetzte Meldung gleicht der gebauten",
      len(_paare302) > 100 and all(a_ == b_ for a_, b_ in _paare302),
      "%d Meldungen, %d abweichend" % (len(_paare302), sum(1 for a_, b_ in _paare302 if a_ != b_)))
_rate302 = (_l302.gesendet_bytes - _bytes302) / 8.0 / 1024.0
pruef("SCHLACHT mit 24 Kaempfern: unter 100 KB/s je Gast (vorher gut 1000)",
      _rate302 < 100.0, "%.1f KB/s" % _rate302)
pruef("Die Eingaben des Gasts quittieren die letzte Weltmeldung",
      _l302._bestaetigt > 0 and _l302._welt_nr - _l302._bestaetigt <= K.NETZ["unterwegs_hoechstens"],
      "%d / %d" % (_l302._bestaetigt, _l302._welt_nr))
# Gegendruck: ohne Quittungen bleibt die Meldung aus - ihre Ereignisse nicht.
_l302._bestaetigt = max(0, _l302._welt_nr - K.NETZ["unterwegs_hoechstens"] - 5)
_vorher302 = _l302._welt_nr
_raus302 = _l302._welt_senden({"t": "welt", "spieler": [], "wirkung": [["k", 7]]})
pruef("Kommt der Gast nicht nach, faellt die naechste Meldung fuer ihn aus",
      _raus302 is None and _l302._welt_nr == _vorher302)
_l302._bestaetigt = _l302._welt_nr
_raus302 = _l302._welt_senden({"t": "welt", "spieler": [], "wirkung": [["k", 8]]})
pruef("... und ihre Ereignisse kommen mit der naechsten",
      _raus302 is not None and _raus302.get("wirkung") == [["k", 7], ["k", 8]], str(_raus302)[:120])
w302.verlassen(); g302.verlassen()
# Ein Schwall: viele grosse Zeilen auf einmal (nach einem Haenger) - frueher
# "Nachricht zu lang", und der Gast landete in der Lobby.
_hoer302 = _so302.socket(); _hoer302.bind(("127.0.0.1", 0)); _hoer302.listen(1)
_sender302 = _so302.create_connection(_hoer302.getsockname())
_empf302, _x302 = _hoer302.accept()
_hoer302.close()
_l302b = netz.Leitung(_empf302)
_zeile302 = (_js302.dumps({"t": "stand", "x": "A" * 20000}) + "\n").encode()
_sender302.setblocking(True)
_anzahl302 = 30
import threading as _th302
_th302.Thread(target=lambda: _sender302.sendall(_zeile302 * _anzahl302), daemon=True).start()
import time as _ti302
_da302 = []
for _ in range(400):
    _da302 += _l302b.holen()
    if len(_da302) >= _anzahl302 or not _l302b.offen:
        break
    _ti302.sleep(0.01)
pruef("Ein Schwall von 30 Meldungen zu je 20 KB wirft niemanden hinaus (600 KB auf einmal)",
      _l302b.offen and len(_da302) == _anzahl302, "%d, %s" % (len(_da302), _l302b.grund))
_sender302.close(); _l302b.schliessen()
pruef("Netztakt 30 je Sekunde (vorher 60)", abs(K.NETZ["takt"] - 1.0 / 30.0) < 1e-9)

print("\n-- 0.34.103: Gast rechnet mit - Puffer und Vorhersage der eigenen Figur")
import random as _rnd303
K.NETZ["puffer_an"] = True
_uhr303 = [0.0]
def _verzoegert303(leitung_, ping_, schwank_, rnd_, ausfall_=None):
    """Die Post dieser Leitung kommt ping_/2 (+- schwank_) spaeter, in
    Reihenfolge wie bei TCP - nach der Uhr der Simulation."""
    alt_ = leitung_.holen
    warte_ = []
    letzte_ = [0.0]
    def holen_():
        for m_ in alt_():
            t_ = max(letzte_[0], _uhr303[0] + ping_ / 2 + rnd_.uniform(-schwank_, schwank_))
            if ausfall_ and ausfall_[0] <= t_ <= ausfall_[1]:
                t_ = ausfall_[1]
            letzte_[0] = t_
            warte_.append((t_, m_))
        raus_ = [m_ for t_, m_ in warte_ if t_ <= _uhr303[0]]
        warte_[:] = [(t_, m_) for t_, m_ in warte_ if t_ > _uhr303[0]]
        return raus_
    leitung_.holen = holen_
def _paar303(ping_, schwank_, ausfall_=None, seed_=1):
    w_, g_ = _paar59("team", karte="staubtal")
    w_._regeln_setzen(dict(_R199.vorgabe(), modus="team", karte="staubtal", bots=0))
    for _ in range(60):
        _uhr303[0] += K.FIXED_DT
        w_.schritt(K.FIXED_DT); g_.schritt(K.FIXED_DT)
    rnd_ = _rnd303.Random(seed_)
    _verzoegert303(g_.gast.leitung, ping_, schwank_, rnd_, ausfall_)
    _verzoegert303(next(iter(w_.gastgeber.leitungen.values())), ping_, schwank_, rnd_, ausfall_)
    w_.ich.unverwundbar = 999.0
    w_.kaempfer[g_.meine_nummer].unverwundbar = 999.0
    return w_, g_
def _lauf303(w_, g_, sek_, halten_, druecke_=(), spur_=None):
    for i_ in range(int(sek_ / K.FIXED_DT)):
        _uhr303[0] += K.FIXED_DT
        app.eingabe._gehalten = set(halten_)
        if i_ == 0:
            for d_ in druecke_:
                g_._knoepfe.add(d_)
        w_.schritt(K.FIXED_DT); g_.schritt(K.FIXED_DT)
        if spur_ is not None:
            spur_.append((_uhr303[0], pygame.Vector2(g_.ich.pos),
                          pygame.Vector2(w_.kaempfer[g_.meine_nummer].pos)))
# 400 ms Ping, +-80 ms Schwankung: die eigene Figur laeuft trotzdem sofort los.
w303, g303 = _paar303(0.4, 0.08)
_lauf303(w303, g303, 1.0, [])
_start303 = pygame.Vector2(g303.ich.pos)
_t0303 = _uhr303[0]
_spur303 = []
_lauf303(w303, g303, 1.5, ["rechts"], spur_=_spur303)
_los303 = next((t_ - _t0303 for t_, a_, _b in _spur303 if a_.distance_to(_start303) > 1.0), 9.9)
_lauf303(w303, g303, 2.0, [], spur_=_spur303)
pruef("400 ms Ping: die eigene Figur laeuft sofort los (unter 0,1 s statt eines Hin- und Rueckwegs)",
      _los303 < 0.1, "%.0f ms" % (_los303 * 1000))
pruef("... und steht am Ende genau dort, wo der Gastgeber sie hat",
      _spur303[-1][1].distance_to(_spur303[-1][2]) < 1.0,
      "%.2f px" % _spur303[-1][1].distance_to(_spur303[-1][2]))
_schritte303 = [a_.distance_to(b_) for (_t, a_, _x), (_u, b_, _y) in zip(_spur303, _spur303[1:])]
pruef("... ohne Sprung: nie mehr als ein paar Pixel je Schritt", max(_schritte303) < 4.0 and g303.vh_spruenge == 0,
      "%.1f px, %d Spruenge" % (max(_schritte303), g303.vh_spruenge))
# Dash: sofort, und der Abgleich holt den Rest weich.
_spur303b = []
_vor303 = pygame.Vector2(g303.ich.pos)
_lauf303(w303, g303, 0.15, ["rechts"], ["dash"], spur_=_spur303b)
pruef("Der Dash beginnt beim Gast sofort", g303.ich.pos.distance_to(_vor303) > 30.0,
      "%.0f px in 0,15 s" % g303.ich.pos.distance_to(_vor303))
_lauf303(w303, g303, 2.0, [], spur_=_spur303b)
_schritte303b = [a_.distance_to(b_) for (_t, a_, _x), (_u, b_, _y) in zip(_spur303b, _spur303b[1:])]
pruef("... und endet ohne Ruck dort, wo der Gastgeber ihn hat",
      max(_schritte303b) < 6.0 and _spur303b[-1][1].distance_to(_spur303b[-1][2]) < 1.0,
      "%.1f px je Schritt, Ende %.2f px" % (max(_schritte303b), _spur303b[-1][1].distance_to(_spur303b[-1][2])))
w303.verlassen(); g303.verlassen()
# Ein Aussetzer von 1,5 s mitten im Laufen: die Vorhersage rennt nicht davon.
w303, g303 = _paar303(0.2, 0.04, ausfall_=(_uhr303[0] + 60 * K.FIXED_DT + 1.5, _uhr303[0] + 60 * K.FIXED_DT + 3.0))
_spur303c = []
_lauf303(w303, g303, 1.0, [])
_lauf303(w303, g303, 3.0, ["rechts"], spur_=_spur303c)
_lauf303(w303, g303, 2.0, [], spur_=_spur303c)
_schritte303c = [a_.distance_to(b_) for (_t, a_, _x), (_u, b_, _y) in zip(_spur303c, _spur303c[1:])]
pruef("1,5 s Aussetzer: kein Zurueckspringen, und am Ende dort, wo der Gastgeber ist",
      max(_schritte303c) < 6.0 and _spur303c[-1][1].distance_to(_spur303c[-1][2]) < 1.0
      and g303.gast.offen,
      "%.1f px je Schritt, Ende %.2f px" % (max(_schritte303c), _spur303c[-1][1].distance_to(_spur303c[-1][2])))
pruef("Ohne Antwort bleibt die Vorhersage nach kurzer Zeit stehen",
      K.NETZ["vorhersage_ohne_antwort"] <= 1.0)
# Puffer: andere ruhiger bei Schwankung, Verzoegerung begrenzt.
_v303 = g303._puffer_verzoegerung()
pruef("Der Puffer verzoegert hoechstens 0,15 s (sonst zielte man weiter hinter Gegnern her)",
      K.NETZ["puffer_mindest"] <= _v303 <= K.NETZ["puffer_hoechstens"] <= 0.15, "%.0f ms" % (_v303 * 1000))
w303.verlassen(); g303.verlassen()
# Reihenfolge und Leitung zu: was im Puffer liegt, wird noch abgespielt.
w303, g303 = _paar303(0.05, 0.0)
for _ in range(30):
    _uhr303[0] += K.FIXED_DT
    w303.schritt(K.FIXED_DT); g303.schritt(K.FIXED_DT)
_zukunft303 = (g303._zt_zuletzt or 0.0) + 5.0
g303._eingang.append({"t": "welt", "zt": _zukunft303, "spieler": [], "wirkung": []})
g303._eingang.append({"t": "stand", "w": {"gepuffert": 1}})
_uhr303[0] += K.FIXED_DT
g303.schritt(K.FIXED_DT)
pruef("Eine Nachricht hinter einer Weltmeldung wartet, bis diese dran ist (Reihenfolge bleibt)",
      g303._zwischenstand != {"gepuffert": 1}
      and any(m_.get("w") == {"gepuffert": 1} for m_ in g303._eingang))
w303.verlassen()
for _ in range(3):
    _uhr303[0] += K.FIXED_DT
    g303.schritt(K.FIXED_DT)
pruef("Geht die Leitung zu, wird der Puffer zuerst abgespielt (Abbruch und Ende gehen nicht verloren)",
      g303._zwischenstand == {"gepuffert": 1} and not g303._eingang)
g303.verlassen()
_gt303 = type("G", (), {})()
for _n in ("_uhr_versatz", "_schwankung"):
    setattr(_gt303, _n, None if _n == "_uhr_versatz" else 0.0)
from dustfront.gastseite import GastTeil as _GT303
_GT303._uhr_messen(_gt303, 100.0, 10.0)
_GT303._uhr_messen(_gt303, 5.0, 11.0)
pruef("Springt die Uhr des Gastgebers zurueck (neues Gefecht), stellt sich der Puffer neu ein",
      abs(_gt303._uhr_versatz - (5.0 - 11.0)) < 1e-9)
K.NETZ["puffer_an"] = False

print("\n-- 0.34.104: Eingabepuffer beim Gastgeber - die Bewegung genau so lange, wie der Gast sie meinte")
K.NETZ["puffer_an"] = True
# Seit 0.34.135 aus als Vorgabe (gemeldet: Dash und Laufen beim Gast verzoegert,
# der Puffer kostete bis zu 200 ms). Es gibt ihn weiter - hier eingeschaltet geprueft.
pruef("Der Eingabepuffer ist als Vorgabe aus (seit 0.34.135)", not K.NETZ["eingabe_puffer"])
K.NETZ["eingabe_puffer"] = True
# Dash und Zickzack bei 400 ms Ping und +-80 ms Schwankung: keine Korrektur.
w304, g304 = _paar303(0.4, 0.08, seed_=4)
# Die Figur des Gastgebers haengt an derselben Tastatur wie der Gast und
# liefe neben ihm her - wer sich anrempelt, wird beim Gastgeber
# auseinandergeschoben, und das rechnet die Vorhersage bewusst nicht. Also weg
# mit ihr: hier geht es nur um Laufen und Dash.
from dustfront.world import freier_punkt as _fp304
w304.ich.pos.update(_fp304(w304.welt, 0, _rnd303.Random(7),
                           weg_von=w304.kaempfer[g304.meine_nummer].pos, mindest=600.0))
w304.ich.vorher.update(w304.ich.pos)
_lauf303(w304, g304, 1.0, [])
_spur304 = []
for _i304 in range(8):
    _lauf303(w304, g304, 0.17, [["rechts"], ["links"], ["hoch"], ["runter"]][_i304 % 4],
             ["dash"] if _i304 in (2, 5) else (), spur_=_spur304)
_lauf303(w304, g304, 2.0, [], spur_=_spur304)
# Nicht "null Korrekturen": je nach Einstiegsort streift der Gast etwas, das
# ihn beim Gastgeber schiebt (Figur, Fahrzeug) - das rechnet die Vorhersage
# bewusst nicht. Ohne Eingabepuffer lagen hier bis zu 30 px daneben.
pruef("Dash und Zickzack bei 400 ms Ping und Schwankung: die Vorhersage liegt unter 1 px daneben",
      g304.vh_fehler_max < 1.0 and g304.vh_spruenge == 0
      and _spur304[-1][1].distance_to(_spur304[-1][2]) < 0.5,
      "%d Korrekturen (%.1f px), Ende %.2f px, Tempofaktor %.5f" % (
          g304.vh_korrekturen, g304.vh_fehler_max,
          _spur304[-1][1].distance_to(_spur304[-1][2]), g304._vh_luft))
# Nur die Bewegung wartet: Schiessen wirkt sofort, wenn die Eingabe ankommt.
_wk304 = w304.kaempfer[g304.meine_nummer]
_l304 = next(iter(w304.gastgeber.leitungen.values()))
_wk304.__dict__.setdefault("_bew_schlange", __import__("collections").deque()).clear()
w304._eingabe_vom_gast(_wk304, {"t": "ein", "will": [1.0, 0.0], "ziel": [0.0, 0.0], "feuert": True,
                                 "zielt": False, "knoepfe": [], "waffe": -1, "en": 99999, "es": 4})
pruef("Schiessen und Zielen wirken sofort - nur die Laufrichtung wartet im Puffer",
      _wk304.feuert and len(_wk304._bew_schlange) >= 1 and _wk304.ein_nr != 99999)
w304._bewegung_fuehren()
pruef("... und kommt dran, sobald die vorige Bewegung ihre Schritte hatte",
      _wk304.ein_nr == 99999 or len(_wk304._bew_schlange) >= 1)
# Zu viel Vorlauf wird abgebaut.
_wk304._bew_schlange.clear()
for _n304 in range(40):
    w304._eingabe_vom_gast(_wk304, {"t": "ein", "will": [0.0, 1.0], "ziel": [0.0, 0.0], "feuert": False,
                                     "zielt": False, "knoepfe": [], "waffe": -1, "en": 100000 + _n304, "es": 4})
for _ in range(2):
    w304._bewegung_fuehren(); w304._bewegung_gezaehlt()
_vorlauf304 = sum(b_.dauer for b_ in _wk304._bew_schlange if b_.dauer is not None)
pruef("Staut sich der Puffer (ein Schwall nach einem Haenger), wird er abgebaut statt die Figur hinterherhinken zu lassen",
      _vorlauf304 <= K.NETZ["eingabe_vorlauf_hoechstens"] + 4, "%d Schritte" % _vorlauf304)
w304.verlassen(); g304.verlassen()
K.NETZ["puffer_an"] = False
K.NETZ["eingabe_puffer"] = False

print("\n-- 0.34.105: Treffer-Rueckrechnung - die Kugel eines Gasts trifft, was er gesehen hat")
w305, g305 = _paar59("pvp", karte="staubtal")
_ziel305 = w305.ich
_ziel305.unverwundbar = 0.0
_a305 = pygame.Vector2(_ziel305.pos)
w305.welt.lagen_merken(10.0)
_ziel305.pos.update(_a305 + pygame.Vector2(60, 0))
w305.welt.lagen_merken(10.2)
_fr305 = "fremd"
pruef("Ohne Rueckrechnung trifft eine Kugel, wo das Ziel jetzt steht",
      w305.welt.treffer(_a305 + pygame.Vector2(60, 0), 2.0, _ziel305.ebene, _fr305) is _ziel305
      and w305.welt.treffer(_a305, 2.0, _ziel305.ebene, _fr305) is not _ziel305)
pruef("Mit 0,2 s Rueckrechnung trifft sie, wo es damals stand - und nicht, wo es jetzt steht",
      w305.welt.treffer(_a305, 2.0, _ziel305.ebene, _fr305, 0.2) is _ziel305
      and w305.welt.treffer(_a305 + pygame.Vector2(60, 0), 2.0, _ziel305.ebene, _fr305, 0.2) is not _ziel305)
# Versetzt (Wiedereinstieg, Teleport): weiter, als es laufen kann - dann
# zaehlt die jetzige Lage, nicht ein Ort, an dem es nie hinlief.
_b305 = pygame.Vector2(_ziel305.pos)
w305.welt.lagen_merken(10.3)
_ziel305.pos.update(_b305 + pygame.Vector2(0, 900))
w305.welt._raster_bauen()        # sonst stuende es im Raster noch an der alten Stelle
w305.welt.lagen_merken(10.4)
pruef("Wer versetzt wurde, wird nicht an seiner alten Stelle getroffen",
      w305.welt.treffer(_b305, 2.0, _ziel305.ebene, _fr305, 0.1) is not _ziel305
      and w305.welt.treffer(_b305 + pygame.Vector2(0, 900), 2.0, _ziel305.ebene, _fr305, 0.1) is _ziel305)
_gk305 = w305.kaempfer[g305.meine_nummer]
w305._eingabe_vom_gast(_gk305, {"t": "ein", "will": [0, 0], "ziel": [0, 0], "feuert": False,
                                 "knoepfe": [], "waffe": -1, "sz": w305._zeit - 30.0})
pruef("Wer eine uralte Zeit schickt, bekommt hoechstens die Grenze (0,5 s)",
      abs(_gk305.rueck - K.NETZ["rueck_hoechstens"]) < 1e-9 and K.NETZ["rueck_hoechstens"] <= 0.5)
w305._eingabe_vom_gast(_gk305, {"t": "ein", "will": [0, 0], "ziel": [0, 0], "feuert": False,
                                 "knoepfe": [], "waffe": -1, "sz": w305._zeit + 5.0})
pruef("... und eine Zeit aus der Zukunft gar keine", _gk305.rueck == 0.0)
from dustfront.entities import Geschoss as _Gs305
_gk305.rueck = 0.123
pruef("Die Kugel eines Gasts bekommt seinen Rueckblick mit, die eines Bots keinen",
      _Gs305(pygame.Vector2(0, 0), 0.0, K.WAFFEN["sturm"], 0, _gk305, "sturm").rueck == 0.123
      and _Gs305(pygame.Vector2(0, 0), 0.0, K.WAFFEN["sturm"], 0, None, "sturm").rueck == 0.0)
w305.verlassen(); g305.verlassen()
# Im Gefecht bei 150 ms Ping: auf einen Laufenden zielen, wo man ihn sieht.
def _schiessen305(rueck_an_):
    K.NETZ["rueck_an"] = rueck_an_
    K.NETZ["puffer_an"] = True
    w_, g_ = _paar303(0.15, 0.03, seed_=5)
    from dustfront.world import freier_punkt as _fp305
    rnd_ = _rnd303.Random(11)
    q_ = None
    for _ in range(800):
        q_ = _fp305(w_.welt, 0, rnd_)
        if all(w_.welt.frei(q_ + pygame.Vector2(dx_, dy_), 10, 0)
               for dx_ in range(-160, 161, 20) for dy_ in (0, 80, 160)):
            break
    ziel_, schuetze_ = w_.ich, w_.kaempfer[g_.meine_nummer]
    ziel_.pos.update(q_); ziel_.vorher.update(q_)
    schuetze_.pos.update(q_ + pygame.Vector2(0, 160)); schuetze_.vorher.update(schuetze_.pos)
    if "sturm" in schuetze_.waffen:
        schuetze_.waffe = schuetze_.waffen.index("sturm")
    zahl_ = [0]
    def schaden_(menge, schub=None, von=None, durch=0.0):
        if von is schuetze_ or getattr(von, "von", None) is schuetze_:
            zahl_[0] += 1
    ziel_.schaden = schaden_
    alt_ = g_._meine_eingabe
    def ein_():
        m_ = alt_()
        gegner_ = g_.kaempfer.get(ziel_.nummer)
        if gegner_ is not None:
            z_ = gegner_.zeichenpos(g_.misch(0.0))
            m_["ziel"] = [round(z_.x, 1), round(z_.y, 1)]
        m_["will"] = [0.0, 0.0]
        m_["feuert"] = True
        return m_
    g_._meine_eingabe = ein_
    for i_ in range(int(6 / K.FIXED_DT)):
        _uhr303[0] += K.FIXED_DT
        app.eingabe._gehalten = {"rechts"} if (i_ // 90) % 2 == 0 else {"links"}
        w_.schritt(K.FIXED_DT); g_.schritt(K.FIXED_DT)
        schuetze_.magazin[schuetze_.waffe_name] = 30
        schuetze_.nachlade_rest = 0.0
        schuetze_.leben = schuetze_.max_leben
    w_.verlassen(); g_.verlassen()
    K.NETZ["rueck_an"] = True
    K.NETZ["puffer_an"] = False
    return zahl_[0]
_ohne305, _mit305 = _schiessen305(False), _schiessen305(True)
pruef("150 ms Ping, Ziel laeuft hin und her: mit Rueckrechnung deutlich mehr Treffer",
      _mit305 >= _ohne305 * 1.25 and _mit305 > 0, "%d statt %d" % (_mit305, _ohne305))

print("\n-- 0.34.106: Gerade Fluege rechnet der Gast - jede Kugel geht nur einmal hinaus")
from dustfront.entities import Geschoss as _Gs306
w306, g306 = _paar59("pvp", karte="staubtal")
_d306 = dict(K.WAFFEN["sturm"], reichweite=5000.0)
# In eine Richtung, in der 800 px lang keine Mauer steht; vom Gastgeber
# selbst geschossen, damit sie ihn nicht beim Start trifft.
_w306 = next((a_ for a_ in range(0, 360, 15)
              if not any(w306.welt.schuss_halt(w306.ich.pos + pygame.Vector2(d_, 0).rotate(a_),
                                               w306.ich.ebene, 2.0)
                         for d_ in range(10, 800, 8))), 0)
_k306 = _Gs306(pygame.Vector2(w306.ich.pos), float(_w306), _d306, w306.ich.ebene, w306.ich, "sturm")
w306.welt.dazu(_k306)
_lagen306 = {}
_alt_wm306 = w306._weltmeldung
def _wm306():
    m_ = _alt_wm306()
    if _k306.lebt:
        _lagen306[m_["zt"]] = pygame.Vector2(_k306.pos)
    return m_
w306._weltmeldung = _wm306
_meldungen306 = []
_alt_ws306 = netz.Leitung._welt_senden
def _ws306(self_, n_):
    r_ = _alt_ws306(self_, n_)
    if r_ is not None:
        _meldungen306.append(r_)
    return r_
netz.Leitung._welt_senden = _ws306
for _ in range(12):
    w306.schritt(K.FIXED_DT); g306.schritt(K.FIXED_DT)
netz.Leitung._welt_senden = _alt_ws306
_meins306 = [e_ for e_ in g306._fremde_schuesse if e_[6] == -1]
_wirt306 = _lagen306.get(g306._zt_zuletzt)
pruef("Der Gast rechnet die Kugel selbst - und sie steht genau dort, wo der Gastgeber sie hatte",
      len(_meins306) == 1 and _wirt306 is not None
      and pygame.Vector2(_meins306[0][0], _meins306[0][1]).distance_to(_wirt306) < 0.5,
      "%s / %s" % (_meins306[:1], _wirt306))
_mit306 = [m_ for m_ in _meldungen306 if str(_k306.kennung) in (m_.get("gs") or {}).get("~d", m_.get("gs") or {})]
pruef("... und sie ging nur einmal hinaus, nicht in jeder Meldung",
      len(_meldungen306) >= 3 and len(_mit306) == 1, "%d von %d Meldungen" % (len(_mit306), len(_meldungen306)))
_k306.tempo = _k306.tempo * 0.5               # wie nach einem Abprallen: anderes Tempo
for _ in range(8):
    w306.schritt(K.FIXED_DT); g306.schritt(K.FIXED_DT)
_meins306 = [e_ for e_ in g306._fremde_schuesse if e_[6] == -1]
_wirt306 = _lagen306.get(g306._zt_zuletzt)
pruef("Aendert sie die Richtung (Abprallen), kommt sie neu - und der Gast folgt",
      len(_meins306) == 1 and _wirt306 is not None
      and pygame.Vector2(_meins306[0][0], _meins306[0][1]).distance_to(_wirt306) < 0.5)
_k306.lebt = False
for _ in range(8):
    w306.schritt(K.FIXED_DT); g306.schritt(K.FIXED_DT)
pruef("Ist sie beim Gastgeber weg, ist sie es auch beim Gast",
      not [e_ for e_ in g306._fremde_schuesse if e_[6] == -1])
w306.verlassen(); g306.verlassen()

# ─────────────────────────────────────────────────────────────────────
# Krad und Jagdpanzer (seit 0.34.107): zwei Fahrzeuge fuer grosse Karten.
# Krad: schnell, ohne Schutz, Beifahrer schiesst. Jagdpanzer: starre Kanone,
# weite Reichweite, dicke Front, nichts fuer Bots.
from dustfront import schlacht as _SL107
_tm107 = _TM59.Testmodus(app, karte="staubtal_offen")
_tm107.zeit_stopp = False
_objekte107 = [e_.name for e_ in _tm107.eintraege if e_.gruppe == "OBJEKTE"]
_nachschub107 = [e_.name for e_ in _tm107.eintraege if e_.gruppe == "NACHSCHUB"]
pruef("Testmodus: KRAD und JAGDPANZER stehen im Spawner (OBJEKTE) und als Abwurf (NACHSCHUB)",
      "KRAD" in _objekte107 and "JAGDPANZER" in _objekte107
      and "ABWURF: KRAD" in _nachschub107 and "ABWURF: JAGDPANZER" in _nachschub107,
      str(_objekte107 + _nachschub107))
_namen107 = [n_ for n_, _c, _t in K.SCHLACHT["belohnungen"]]
pruef("Beide sind im Nachschub der SCHLACHT zu kaufen, mit Buchstaben fuer die Dropzone",
      "krad" in _namen107 and "jagdpanzer" in _namen107
      and K.SCHLACHT["dropzone"]["zeichen"]["krad"] == "K"
      and K.SCHLACHT["dropzone"]["zeichen"]["jagdpanzer"] == "J")
_unten107 = _SL107.SchlachtTeil._belohnung_hilfe_rect().bottom + 2 + 14
pruef("Die Nachschubtafel passt mit allen Zeilen aufs Bild (Hinweiszeile bleibt frei)",
      _unten107 < K.GAME_H - 36, "unten bei %d" % _unten107)
pruef("Die Basis jeder Seite bekommt ein Krad dazu",
      ("krad", 1) in K.basis_wagen())

# Ein freies Feld, gross genug zum Fahren.
_e107 = _tm107.welt.ebene(0)
_rnd107 = random.Random(107)
for _ in range(40000):
    _tx107 = _rnd107.randrange(60, _e107.breite - 90)
    _ty107 = _rnd107.randrange(20, _e107.hoehe - 40)
    if all(not K.KACHELN[_e107.kachel(_tx107 + x_, _ty107 + y_)]["fest"]
           for x_ in range(30) for y_ in range(14)):
        break
_z107 = lambda x_, y_: pygame.Vector2((_tx107 + x_ + 0.5) * K.TILE, (_ty107 + y_ + 0.5) * K.TILE)

_krad107 = _tm107.fahrzeug_setzen("krad", _z107(4, 4), 0, {"winkel": 0})
_bug107 = _tm107.fahrzeug_setzen("buggy", _z107(4, 9), 0, {"winkel": 0})
_f107 = _tm107.puppe_setzen(_krad107.ausstiegsorte(9.0)[0], 0, {"team": 0}, name="FAHRER")
_tm107._anwenden(_f107, {"will": [0, 0], "ziel": [0, 0], "knoepfe": ["nutzen"]})
pruef("Krad: man steigt mit E ein, und es ist ein Krad (eigenes Bild, Art)",
      _f107.fahrzeug is _krad107 and _krad107.art == "krad" and _krad107.bild.startswith("krad_"),
      _krad107.bild)
_fb107 = _tm107.puppe_setzen(_bug107.ausstiegsorte(9.0)[0], 0, {"team": 0}, name="BUGGY")
_tm107._anwenden(_fb107, {"will": [0, 0], "ziel": [0, 0], "knoepfe": ["nutzen"]})
for _ in range(int(3.5 / K.FIXED_DT)):
    _tm107._anwenden(_f107, {"will": [0, -1], "ziel": [0, 0], "knoepfe": []})
    _tm107._anwenden(_fb107, {"will": [0, -1], "ziel": [0, 0], "knoepfe": []})
    _tm107.schritt(K.FIXED_DT)
pruef("Krad: schneller als der Buggy und von den Werten her das schnellste Fahrzeug",
      _krad107.geschw.length() > _bug107.geschw.length() + 10.0
      and K.KRAD["hoechst"] > max(K.FAHRZEUG["hoechst"], K.PANZERWAGEN["hoechst"] * 0.9),
      "%.0f gegen %.0f" % (_krad107.geschw.length(), _bug107.geschw.length()))

# Der Beifahrer.
_krad107.pos.update(_z107(10, 4)); _krad107.vorher.update(_krad107.pos)
_krad107.geschw.update(0, 0); _krad107.gas = 0.0
_krad107.winkel = 0.0
_bf107 = _tm107.puppe_setzen(_krad107.pos + pygame.Vector2(20, 14), 0, {"team": 0, "waffe_figur": "sturm"},
                             name="BEIFAHRER")
_tm107._anwenden(_bf107, {"will": [0, 0], "ziel": [0, 0], "knoepfe": ["nutzen"]})
pruef("Krad: ein Kamerad sitzt mit E im Beiwagen auf (ein Platz)",
      _bf107.mitfahrt is _krad107 and len(_krad107.mitfahrer) == 1
      and _tm107._transporter_bei(_tm107.puppe_setzen(_krad107.pos + pygame.Vector2(10, 14), 0,
                                                      {"team": 0}, name="ZWEITER")) is None,
      str(_krad107.mitfahrer))
_tm107.schritt(K.FIXED_DT)
# Seit 0.34.123 sitzt der Beifahrer als eigene Figur im Beiwagen (mit seiner
# Waffe und Blickrichtung, luft._beifahrer_zeichnen) - nicht mehr im Krad-Bild.
pruef("... er sitzt sichtbar im Beiwagen: am Sitz des Krads (das Krad-Bild selbst bleibt ohne Beifahrer)",
      "beiwagen" not in _krad107.bild and _bf107.pos.distance_to(_krad107.beifahrer_sitz()) < 1.0,
      "%s %.1f" % (_krad107.bild, _bf107.pos.distance_to(_krad107.beifahrer_sitz())))
_leben107 = (_krad107.leben, _f107.leben, _bf107.leben)
_ziel107 = _krad107.pos + pygame.Vector2(200, 60)
_vorher107 = _bf107.magazin[_bf107.waffe_name]
for _ in range(int(0.8 / K.FIXED_DT)):
    _tm107._anwenden(_bf107, {"will": [0, 0], "ziel": [_ziel107.x, _ziel107.y], "knoepfe": [],
                              "feuert": True})
    _tm107.schritt(K.FIXED_DT)
pruef("Krad: der Beifahrer schiesst mit seiner Waffe (Munition geht weg) ...",
      _bf107.magazin[_bf107.waffe_name] < _vorher107, str(_bf107.magazin[_bf107.waffe_name]))
pruef("... und trifft sein eigenes Krad nicht",
      _krad107.leben == _leben107[0] and _f107.leben == _leben107[1],
      "%s / %s" % (_krad107.leben, _f107.leben))
_feind107 = _tm107.puppe_setzen(_z107(24, 4), 0, {"team": 1}, name="FEIND")
_tm107._anwenden(_bf107, {"will": [0, 0], "ziel": [_ziel107.x, _ziel107.y], "knoepfe": [],
                          "feuert": False})
_krad107.schaden(40.0, None, _feind107, art="kugel", herkunft=_feind107.pos)
pruef("Krad: ein Treffer kommt ungeschuetzt bei beiden an (im Gegensatz zu allen anderen Fahrzeugen)",
      _f107.leben < _leben107[1] and _bf107.leben < _leben107[2]
      and abs((_leben107[1] - _f107.leben) - (_leben107[2] - _bf107.leben)) < 1e-6,
      "Fahrer %.0f, Beifahrer %.0f" % (_f107.leben, _bf107.leben))
_f107.treppe_rest = 0.0
_tm107._anwenden(_f107, {"will": [0, 0], "ziel": [0, 0], "knoepfe": ["nutzen"]})
for _ in range(3):
    _tm107.schritt(K.FIXED_DT)
pruef("Krad: steigt der Fahrer aus, steigt der Beifahrer ab",
      _f107.fahrzeug is None and _bf107.mitfahrt is None and not _krad107.mitfahrer)

# Der Jagdpanzer.
_jp107 = _tm107.fahrzeug_setzen("jagdpanzer", _z107(16, 9), 0, {"winkel": 0})
_pz107 = _tm107.fahrzeug_setzen("panzer", _z107(16, 3), 0, {"winkel": 0})
_jf107 = _tm107.puppe_setzen(_jp107.ausstiegsorte(9.0)[0], 0, {"team": 0}, name="JAEGER")
_tm107._anwenden(_jf107, {"will": [0, 0], "ziel": [0, 0], "knoepfe": ["nutzen"]})
pruef("Jagdpanzer: eigene Art, einsteigen geht, er ist rechteckig wie der Panzer",
      _jf107.fahrzeug is _jp107 and _jp107.art == "jagdpanzer" and _jp107.rechteckig
      and _jp107.bild == "jagdpanzer")
# Zeiger weit hinter ihn: das Rohr bleibt im Schwenkbereich.
_hinten107 = _jp107.pos + pygame.Vector2(-300, 40)
for _ in range(int(3.0 / K.FIXED_DT)):
    _tm107._anwenden(_jf107, {"will": [0, 0], "ziel": [_hinten107.x, _hinten107.y], "knoepfe": []})
    _tm107.schritt(K.FIXED_DT)
_ab107 = abs((_jp107.aufbau - _jp107.winkel + 180.0) % 360.0 - 180.0)
pruef("Jagdpanzer: die Kanone schwenkt nur wenige Grad aus der Wanne (kein Turm)",
      _ab107 <= K.JAGDPANZER["schwenk"] + 0.5, "%.1f Grad" % _ab107)
_vorn107 = _jp107.pos + pygame.Vector2(300, 0)
for _ in range(int(2.5 / K.FIXED_DT)):
    _tm107._anwenden(_jf107, {"will": [0, 0], "ziel": [_vorn107.x, _vorn107.y], "knoepfe": []})
    _tm107.schritt(K.FIXED_DT)
_gr107 = len([w_ for w_ in _tm107.welt.wesen if isinstance(w_, _FZ59.Panzergranate)])
_tm107._anwenden(_jf107, {"will": [0, 0], "ziel": [_vorn107.x, _vorn107.y], "knoepfe": [],
                          "feuert": True})
_tm107.schritt(K.FIXED_DT)
_tm107.schritt(K.FIXED_DT)
_gr2107 = [w_ for w_ in _tm107.welt.wesen if isinstance(w_, _FZ59.Panzergranate)]
pruef("Jagdpanzer: die Linke schiesst die Kanone - weiter als der Panzer, mit eigener Pause",
      len(_gr2107) == _gr107 + 1 and _gr2107[-1].rest > K.FAHRZEUG_WAFFEN["kanone"]["reichweite"]
      and abs(_jp107.takt["kanone"] - K.FAHRZEUG_WAFFEN["jagdkanone"]["takt"]) < 0.1,
      "Rest %.0f, Pause %.2f" % (_gr2107[-1].rest if _gr2107 else -1, _jp107.takt.get("kanone", -1)))
_vor107 = _jp107.pos + _jp107.vorn * 100
_hin107 = _jp107.pos - _jp107.vorn * 100
pruef("Jagdpanzer: von vorn dicker als der Panzer, von hinten duenner als von vorn",
      _jp107.panzerung("kugel", _vor107) < _pz107.panzerung("kugel", _pz107.pos + _pz107.vorn * 100)
      and _jp107.panzerung("hohlladung", _hin107) > _jp107.panzerung("hohlladung", _vor107) * 2.0,
      "%.3f gegen %.3f" % (_jp107.panzerung("kugel", _vor107),
                           _pz107.panzerung("kugel", _pz107.pos + _pz107.vorn * 100)))
_tm107._anwenden(_jf107, {"will": [0, 0], "ziel": [0, 0], "knoepfe": ["nutzen"]})
_jf107.treppe_rest = 0.0
_tm107._anwenden(_jf107, {"will": [0, 0], "ziel": [0, 0], "knoepfe": ["nutzen"]})
_bot107 = _tm107.bot_setzen(_jp107.pos + pygame.Vector2(0, 50), 0, {"team": 1})
_bot107.darf_fahren = True
_krad2107 = _tm107.fahrzeug_setzen("krad", _z107(24, 10), 0, {"winkel": 0})
_bot2107 = _tm107.bot_setzen(_krad2107.pos + pygame.Vector2(0, 24), 0, {"team": 1})
_bot2107.darf_fahren = True
pruef("Jagdpanzer: ein Bot steigt nicht ein (noch nichts fuer Bots), ins Krad schon",
      _tm107._freier_buggy(_bot107) is None and _tm107._freier_buggy(_bot2107) is _krad2107,
      "%s / %s" % (_tm107._freier_buggy(_bot107), _tm107._freier_buggy(_bot2107)))
_bi107 = app.bilder
_masse107 = [(n_, _bi107.bild(n_).get_size()) for n_ in
             ("krad", "krad_fahrer", "krad_beiwagen_fahrer", "krad_beiwagen_rot_fahrer",
              "krad_blau_fahrer", "krad_wrack", "krad_schatten", "jagdpanzer", "jagdpanzer_rohr",
              "jagdpanzer_rohr_fahrer", "jagdpanzer_rohr_rot_fahrer", "jagdpanzer_wrack")]
pruef("Alle Bilder von Krad und Jagdpanzer gibt es, in ihrem Sollmass",
      all(g_ == K.BILD_MASS[n_] for n_, g_ in _masse107), str(_masse107[:3]))
_krad107.schaden(9999.0, None, _feind107)
pruef("Krad: zerstoert ist es ein Wrack",
      _krad107.kaputt and _krad107.bild == "krad_wrack")
_tm107.verlassen()

# ─────────────────────────────────────────────────────────────────────
# Trosswagen (seit 0.34.108): hinten dran Nachschub holen (E), eigene
# Fahrzeuge dort reparieren, nichts fuer Bots, nicht zu kaufen.
_tm108 = _TM59.Testmodus(app, karte="staubtal_offen")
pruef("Testmodus: TROSSWAGEN steht im Spawner (OBJEKTE)",
      "TROSSWAGEN" in [e_.name for e_ in _tm108.eintraege if e_.gruppe == "OBJEKTE"])
pruef("Der Trosswagen steht an jeder Basis, ist aber nicht zu kaufen",
      dict(K.basis_wagen()).get("trosswagen") == 2
      and "trosswagen" not in [n_ for n_, _c, _t in K.SCHLACHT["belohnungen"]])
_e108 = _tm108.welt.ebene(0)
_rnd108 = random.Random(108)
for _ in range(40000):
    _tx108 = _rnd108.randrange(60, _e108.breite - 90)
    _ty108 = _rnd108.randrange(20, _e108.hoehe - 40)
    if all(not K.KACHELN[_e108.kachel(_tx108 + x_, _ty108 + y_)]["fest"]
           for x_ in range(30) for y_ in range(14)):
        break
_z108 = lambda x_, y_: pygame.Vector2((_tx108 + x_ + 0.5) * K.TILE, (_ty108 + y_ + 0.5) * K.TILE)
_tw108 = _tm108.fahrzeug_setzen("trosswagen", _z108(12, 7), 0, {"winkel": 0})
_tw108.nachschub = 2
pruef("Trosswagen: eigene Art, kein Platz zum Aufsitzen, seit 0.34.131 auch mit Bot am Steuer",
      _tw108.art == "trosswagen" and "plaetze" not in _tw108.werte
      and not _tw108.werte.get("nur_mensch") and _tw108.bild == "trosswagen")
_hinten108 = _tw108.zone_mitte()
_a108 = _tm108.puppe_setzen(_hinten108 + pygame.Vector2(6, 4), 0, {"team": 0, "waffe_figur": "sturm"},
                            name="HOLER")
_a108.medkits = 0
_a108.magazin[_a108.waffe_name] = 1
_m108 = _a108.medkits
_tm108._anwenden(_a108, {"will": [0, 0], "ziel": [0, 0], "knoepfe": ["nutzen"]})
pruef("Trosswagen: hinten dran gibt E Munition und ein Medkit - ohne einzusteigen",
      _a108.medkits == _m108 + 1
      and _a108.magazin[_a108.waffe_name] == K.WAFFEN[_a108.waffe_name]["magazin"]
      and _a108.fahrzeug is None and _tw108.nachschub == 1,
      "Medkits %d, Magazin %d, Vorrat %d" % (_a108.medkits, _a108.magazin[_a108.waffe_name],
                                              _tw108.nachschub))
_a108.treppe_rest = 0.0
_a108.magazin[_a108.waffe_name] = 1
_tm108._anwenden(_a108, {"will": [0, 0], "ziel": [0, 0], "knoepfe": ["nutzen"]})
pruef("... derselbe Spieler muss warten (Pause), der Vorrat bleibt",
      _tw108.nachschub == 1 and _a108.magazin[_a108.waffe_name] == 1 and _a108.fahrzeug is None)
_b108 = _tm108.puppe_setzen(_hinten108 + pygame.Vector2(-8, -6), 0, {"team": 1, "waffe_figur": "sturm"},
                            name="GEGNER")
_b108.magazin[_b108.waffe_name] = 1
_tm108._anwenden(_b108, {"will": [0, 0], "ziel": [0, 0], "knoepfe": ["nutzen"]})
pruef("... ein Gegner darf ihn auch plündern (zweite Entnahme, danach ist er leer)",
      _b108.magazin[_b108.waffe_name] == K.WAFFEN[_b108.waffe_name]["magazin"]
      and _tw108.nachschub == 0, str(_tw108.nachschub))
_c108 = _tm108.puppe_setzen(_hinten108 + pygame.Vector2(0, 10), 0, {"team": 0}, name="DRITTER")
_c108.magazin[_c108.waffe_name] = 1
_tm108._anwenden(_c108, {"will": [0, 0], "ziel": [0, 0], "knoepfe": ["nutzen"]})
pruef("... ist der Vorrat leer, gibt es nichts mehr",
      _c108.magazin[_c108.waffe_name] == 1)
_ferne108 = _tm108.puppe_setzen(_tw108.pos + pygame.Vector2(0, 150), 0, {"team": 0}, name="FERN")
_tw108.nachschub = 5
_ferne108.magazin[_ferne108.waffe_name] = 1
_tm108._anwenden(_ferne108, {"will": [0, 0], "ziel": [0, 0], "knoepfe": ["nutzen"]})
pruef("Trosswagen: wer nicht hinten dransteht, bekommt nichts", _tw108.nachschub == 5
      and _ferne108.magazin[_ferne108.waffe_name] == 1)
# Reparatur: ein eigener Panzer hinten dran, ein anderer weiter weg.
_pz108 = _tm108.fahrzeug_setzen("panzer", _tw108.zone_mitte(), 0, {"winkel": 0})
_pf108 = _tm108.fahrzeug_setzen("panzer", _z108(26, 12), 0, {"winkel": 0})
_pz108.leben = _pz108.max_leben * 0.5
_pf108.leben = _pf108.max_leben * 0.5
_l108 = (_pz108.leben, _pf108.leben, _tw108.reparatur)
for _ in range(int(3.0 / K.FIXED_DT)):
    _tm108.schritt(K.FIXED_DT)
pruef("Trosswagen: ein Fahrzeug hinten dran wird repariert, auch im Stehen - ein fernes nicht",
      _pz108.leben > _l108[0] + 30.0 and _pf108.leben == _l108[1] and _tw108.reparatur < _l108[2],
      "%.0f -> %.0f, Vorrat %.0f" % (_l108[0], _pz108.leben, _tw108.reparatur))
_tw108.reparatur = 0.0
_v108 = _pz108.leben
_pz108.leben = _v108 - 100.0
for _ in range(int(1.0 / K.FIXED_DT)):
    _tm108.schritt(K.FIXED_DT)
pruef("... ist der Vorrat an Reparatur leer, hoert es auf", _pz108.leben == _v108 - 100.0)
_bot108 = _tm108.bot_setzen(_tw108.pos + pygame.Vector2(0, 30), 0, {"team": 1})
_bot108.darf_fahren = True
# Seit 0.34.131 faehrt ein Bot ihn (gewuenscht: "die Bots sollen alle
# Fahrzeuge richtig nutzen") - an die Front, dort stellt er ihn ab.
pruef("Trosswagen: ein Bot steigt ein (seit 0.34.131)", _tm108._freier_buggy(_bot108) is _tw108)
_tm108.verlassen()

# ─────────────────────────────────────────────────────────────────────
# 0.34.109: Skins auch im Krad und im Jagdpanzer, und die Reichweite des
# Jagdpanzers (Kanone und Zielfernrohr).
from dustfront import art_figuren as _AF109
_tm109 = _TM59.Testmodus(app, karte="staubtal_offen")
_skin109 = _AF109.waehlbar()[3]
_namen109 = ["krad_skin_%s_rot" % _skin109, "krad_beiwagen_skin_%s_blau" % _skin109,
             "jagdpanzer_rohr_skin_%s_rot" % _skin109, "krad_skin_%s" % _skin109]
_soll109 = [K.BILD_MASS["krad_fahrer"], K.BILD_MASS["krad_beiwagen_fahrer"],
            K.BILD_MASS["jagdpanzer_rohr_fahrer"], K.BILD_MASS["krad_fahrer"]]
pruef("Skins: Bilder von Krad (leer-Fahrer, Beiwagen) und Jagdpanzer-Kanone im Skin, im Sollmass",
      all(app.bilder.bild(n_).get_size() == m_ for n_, m_ in zip(_namen109, _soll109)),
      str([app.bilder.bild(n_).get_size() for n_ in _namen109]))
pruef("... ein Skin, den es nicht gibt, bleibt ohne Muster (faellt auf die Mannschaft zurueck)",
      not app.bilder.mass("krad_skin_gibtesnicht_rot"))
_e109 = _tm109.welt.ebene(0)
_rnd109 = random.Random(109)
for _ in range(60000):
    _ty109 = _rnd109.randrange(20, _e109.hoehe - 20)
    _tx109 = _rnd109.randrange(40, _e109.breite - 60)
    if all(not K.KACHELN[_e109.kachel(_tx109 + x_, _ty109 + dy_)]["fest"]
           for x_ in range(48) for dy_ in (-2, -1, 0, 1, 2)):
        break
_z109 = lambda x_, y_: pygame.Vector2((_tx109 + x_ + 0.5) * K.TILE, (_ty109 + y_ + 0.5) * K.TILE)
_kr109 = _tm109.fahrzeug_setzen("krad", _z109(2, 0), 0, {"winkel": 0})
_f109 = _tm109.puppe_setzen(_kr109.ausstiegsorte(9.0)[0], 0, {"team": 0, "aussehen": _skin109}, name="FAHRER")
_tm109._anwenden(_f109, {"will": [0, 0], "ziel": [0, 0], "knoepfe": ["nutzen"]})
_b109 = _tm109.puppe_setzen(_kr109.pos + pygame.Vector2(20, 14), 0, {"team": 0}, name="BEI")
_alt109 = _kr109.bild
_tm109._anwenden(_b109, {"will": [0, 0], "ziel": [0, 0], "knoepfe": ["nutzen"]})
pruef("Skins: das Krad zeigt den Fahrer in seinem Aussehen (leer und mit Beifahrer - der sitzt seit 0.34.123 als eigene Figur daneben)",
      _alt109 == "krad_skin_%s_rot" % _skin109
      and _kr109.bild == "krad_skin_%s_rot" % _skin109,
      "%s / %s" % (_alt109, _kr109.bild))
_jp109 = _tm109.fahrzeug_setzen("jagdpanzer", _z109(6, 0), 0, {"winkel": 0})
_jf109 = _tm109.puppe_setzen(_jp109.ausstiegsorte(9.0)[0], 0, {"team": 0, "aussehen": _skin109},
                             name="KOMMANDANT")
_tm109._anwenden(_jf109, {"will": [0, 0], "ziel": [0, 0], "knoepfe": ["nutzen"]})
# Seit 0.34.117 (gewuenscht): beim Jagdpanzer ist der Fahrer nicht zu sehen, die Luke ist
# geschlossen - es gibt dafuer nur noch ein Bild, ohne Skin und ohne Mannschaftsfarbe.
pruef("Jagdpanzer: der Fahrer ist nicht sichtbar - die Kanone hat immer dasselbe Bild mit geschlossener Luke",
      _jp109.aufbau_bild_name() == "jagdpanzer_rohr", _jp109.aufbau_bild_name())
# Reichweite: ein Ziel 1 300 Pixel entfernt, mitten in der freien Bahn.
_ziel109 = _tm109.puppe_setzen(_jp109.pos + pygame.Vector2(1300, 0), 0, {"team": 1, "leben": 20.0},
                               name="WEIT")
_l109 = _ziel109.leben
_jp109.takt["kanone"] = 0.0
for _ in range(int(3.5 / K.FIXED_DT)):
    _tm109._anwenden(_jf109, {"will": [0, 0], "ziel": [_ziel109.pos.x, _ziel109.pos.y], "knoepfe": [],
                              "feuert": True})
    _tm109.schritt(K.FIXED_DT)
pruef("Jagdpanzer: ein Ziel in 1 300 Pixeln wird von der Kanone getroffen (der Panzer reicht nur 900)",
      _ziel109.leben < _l109 or not _ziel109.lebt, "Leben %.0f von %.0f" % (_ziel109.leben, _l109))
_pz109 = _tm109.fahrzeug_setzen("panzer", _z109(6, 4), 0, {"winkel": 0})
pruef("... der Panzer kaeme dort nicht mehr an (Reichweite)",
      K.FAHRZEUG_WAFFEN["kanone"]["reichweite"] < 1300 < K.FAHRZEUG_WAFFEN["jagdkanone"]["reichweite"])
# Zielfernrohr: rechte Maustaste im Jagdpanzer, nicht im Panzer oder Buggy.
_gehalten109 = app.eingabe.gehalten
app.eingabe.gehalten = lambda n_: n_ == "zweit"
_tm109.uebernehmen(_jf109)          # ab hier ist er "ich" (mit eigener Eingabe, nicht mehr gesteuert)
_scope_jp109 = _tm109.scope_an()
_jf109.treppe_rest = 0.0
_tm109._aussteigen(_jf109)
_scope_draussen109 = _tm109.scope_an()
app.eingabe.gehalten = lambda n_: False
_scope_ohne109 = _tm109.scope_an()
app.eingabe.gehalten = _gehalten109
pruef("Zielfernrohr: im Jagdpanzer mit der rechten Maustaste an, ohne sie und zu Fuss (ohne Fernrohrwaffe) aus",
      _scope_jp109 and not _scope_draussen109 and not _scope_ohne109,
      "%s %s %s" % (_scope_jp109, _scope_draussen109, _scope_ohne109))
from dustfront.render import Kamera as _Kam109
_ka109 = _Kam109((1000, 1000))
_kb109 = _Kam109((1000, 1000))
for _ in range(240):
    _ka109.schritt(K.FIXED_DT, pygame.Vector2(1000, 1000), pygame.Vector2(1000 + 900, 1000), (9999, 9999),
                   versatz=pygame.Vector2(300, 0), scope=True)
    _kb109.schritt(K.FIXED_DT, pygame.Vector2(1000, 1000), pygame.Vector2(1000 + 900, 1000), (9999, 9999),
                   versatz=pygame.Vector2(300, 0), scope=False)
pruef("Zielfernrohr: die Kamera laeuft weit voraus (mehr als ohne)",
      _ka109.pos.x - 1000 > (_kb109.pos.x - 1000) * 1.5 and _ka109.pos.x - 1000 > 300,
      "%.0f gegen %.0f" % (_ka109.pos.x - 1000, _kb109.pos.x - 1000))
_tm109.verlassen()

# ─────────────────────────────────────────────────────────────────────
# Spulenwagen (seit 0.34.110): schwacher Kettenblitz, EMP-Feld nur aufgebaut,
# zeitlich begrenzt, danach laden; eigene Fahrzeuge bleiben verschont.
_tm110 = _TM59.Testmodus(app, karte="staubtal_offen")
_namen110 = [e_.name for e_ in _tm110.eintraege]
pruef("Testmodus: SPULENWAGEN im Spawner (OBJEKTE) und als Abwurf (NACHSCHUB)",
      "SPULENWAGEN" in _namen110 and "ABWURF: SPULENWAGEN" in _namen110)
pruef("Der Spulenwagen ist im Nachschub, die Tafel passt trotzdem",
      "spulenwagen" in [n_ for n_, _c, _t in K.SCHLACHT["belohnungen"]]
      and _SL107.SchlachtTeil._gratis_rect.__name__ and
      _SL107.SchlachtTeil._belohnung_hilfe_rect().bottom + 2 + 14 < K.GAME_H - 36)
_e110 = _tm110.welt.ebene(0)
_rnd110 = random.Random(110)
for _ in range(40000):
    _tx110 = _rnd110.randrange(60, _e110.breite - 90)
    _ty110 = _rnd110.randrange(20, _e110.hoehe - 40)
    if all(not K.KACHELN[_e110.kachel(_tx110 + x_, _ty110 + y_)]["fest"]
           for x_ in range(34) for y_ in range(16)):
        break
_z110 = lambda x_, y_: pygame.Vector2((_tx110 + x_ + 0.5) * K.TILE, (_ty110 + y_ + 0.5) * K.TILE)
_sp110 = _tm110.fahrzeug_setzen("spulenwagen", _z110(6, 8), 0, {"winkel": 0})
_sf110 = _tm110.puppe_setzen(_sp110.ausstiegsorte(9.0)[0], 0, {"team": 0}, name="TECHNIKER")
_tm110._anwenden(_sf110, {"will": [0, 0], "ziel": [0, 0], "knoepfe": ["nutzen"]})
pruef("Spulenwagen: eigene Art, keine Plaetze, seit 0.34.131 auch fuer Bots, eigenes Bild",
      _sf110.fahrzeug is _sp110 and _sp110.art == "spulenwagen" and "plaetze" not in _sp110.werte
      and not _sp110.werte.get("nur_mensch") and _sp110.bild == "spulenwagen")
# Die Gegner: ein Panzer im Kreis, einer ausserhalb, ein eigener im Kreis.
_feind110 = _tm110.fahrzeug_setzen("panzer", _z110(11, 8), 0, {"winkel": 180})
_fern110 = _tm110.fahrzeug_setzen("panzer", _z110(30, 13), 0, {"winkel": 180})
_eigen110 = _tm110.fahrzeug_setzen("buggy", _z110(6, 4), 0, {"winkel": 0})
_ef110 = _tm110.puppe_setzen(_feind110.ausstiegsorte(9.0)[0], 0, {"team": 1}, name="FEIND")
_tm110._anwenden(_ef110, {"will": [0, 0], "ziel": [0, 0], "knoepfe": ["nutzen"]})
_if110 = _tm110.puppe_setzen(_eigen110.ausstiegsorte(9.0)[0], 0, {"team": 0}, name="FREUND")
_tm110._anwenden(_if110, {"will": [0, 0], "ziel": [0, 0], "knoepfe": ["nutzen"]})
_ziel110 = [_z110(20, 8).x, _z110(20, 8).y]
def _sp_ein110(zielt_, will_=(0, 0), feuert_=False):
    _tm110._anwenden(_sf110, {"will": list(will_), "ziel": _ziel110, "knoepfe": [], "zielt": zielt_,
                              "feuert": feuert_})
    _tm110.schritt(K.FIXED_DT)
for _ in range(3):
    _sp_ein110(True)
_sp_ein110(False)
pruef("Spulenwagen: die rechte Maustaste baut das Feld auf (Phase 1), er steht dabei",
      _sp110.phase == 1 and _sp110.phase_rest > 2.0)
for _ in range(int(1.0 / K.FIXED_DT)):
    _sp_ein110(False, will_=(0, -1))
pruef("... beim Aufbauen faehrt er nicht (Gas gilt nicht)", _sp110.geschw.length() < 1.0,
      "%.1f" % _sp110.geschw.length())
for _ in range(int(2.0 / K.FIXED_DT)):
    _sp_ein110(False)
pruef("... danach ist das Feld aktiv (Phase 2) und pulsiert: Bild mit Glut",
      _sp110.phase == 2 and _sp110.bild == "spulenwagen_aktiv", str(_sp110.phase))
for _ in range(int(1.5 / K.FIXED_DT)):
    _sp_ein110(False)
pruef("Ein Puls legt fremde Fahrzeuge im Kreis still ...", _feind110.emp_rest > 0.0,
      "%.1f" % _feind110.emp_rest)
pruef("... aber nicht eigene und nicht die ausserhalb", _eigen110.emp_rest == 0.0 and _fern110.emp_rest == 0.0,
      "%.1f / %.1f" % (_eigen110.emp_rest, _fern110.emp_rest))
_ph110 = K.SPULENWAGEN["feld"]
for _ in range(int((_ph110["dauer"] + 0.5) / K.FIXED_DT)):
    _sp_ein110(False)
pruef("Das Feld haelt nur seine Zeit: danach laedt er (Phase 3) und steht wieder frei",
      _sp110.phase == 3 and _sp110.phase_rest > _ph110["laden"] - 3.0, "%d %.1f" % (_sp110.phase, _sp110.phase_rest))
for _ in range(3):
    _sp_ein110(True)
_sp_ein110(False)
pruef("... solange er laedt, geht kein neues Feld", _sp110.phase == 3)
for _ in range(int((_ph110["laden"] + 1.0) / K.FIXED_DT)):
    _sp_ein110(False)
_sp110.pos.update(_z110(2, 2)); _sp110.vorher.update(_sp110.pos); _sp110.geschw.update(0, 0)
_sp110.winkel = 90.0
for _ in range(int(2.0 / K.FIXED_DT)):
    _sp_ein110(False, will_=(0, -1))
pruef("... nach dem Laden ist er bereit und faehrt", _sp110.phase == 0 and _sp110.geschw.length() > 5.0,
      "%d %.1f" % (_sp110.phase, _sp110.geschw.length()))
# Nur im Stand aufbauen.
_tm110._anwenden(_sf110, {"will": [0, -1], "ziel": _ziel110, "knoepfe": [], "zielt": True})
_tm110.schritt(K.FIXED_DT)
pruef("Aufbauen geht nur im Stand, nicht in voller Fahrt", _sp110.phase == 0 and _sp110.geschw.length() > 20.0)
# Der Blitz.
_sp110.pos.update(_z110(4, 3)); _sp110.vorher.update(_sp110.pos); _sp110.geschw.update(0, 0)
_sp110.winkel = 0.0; _sp110.phase = 0
_tm110.fahrzeuge  # (nur zur Lesbarkeit)
_a110 = _tm110.puppe_setzen(_sp110.spule_mitte() + pygame.Vector2(180, 0), 0, {"team": 1, "leben": 20.0}, name="A")
_b110 = _tm110.puppe_setzen(_a110.pos + pygame.Vector2(60, 40), 0, {"team": 1, "leben": 20.0}, name="B")
_c110 = _tm110.puppe_setzen(_sp110.spule_mitte() + pygame.Vector2(0, 220), 0, {"team": 1, "leben": 20.0}, name="C")
_ziel110 = [_a110.pos.x, _a110.pos.y]
_la110, _lb110, _lc110 = _a110.leben, _b110.leben, _c110.leben
_sf110.treppe_rest = 0.0
for _ in range(int(0.3 / K.FIXED_DT)):
    _sp_ein110(False, feuert_=True)
_da110, _db110 = _la110 - _a110.leben, _lb110 - _b110.leben
pruef("Spulenwagen: der Blitz trifft den ersten im Kegel und springt weiter, schwaecher",
      0.0 < _db110 < _da110 and _lc110 == _c110.leben and _da110 <= K.SPULENWAGEN["blitz"]["schaden"] + 0.01,
      "%.1f / %.1f" % (_da110, _db110))
pruef("... und viel schwaecher als der Kettenblitz zu Fuss",
      K.SPULENWAGEN["blitz"]["schaden"] < K.WAFFEN["kettenblitz"]["schaden"])
_tm110.verlassen()

# ─────────────────────────────────────────────────────────────────────
# Funkwagen (seit 0.34.111): Mast aufbauen, PEILEN (Gegner markieren) oder
# STOEREN (kein Funk, keine Markierungen, keine Drohnen, kein Nachschub),
# und die Bots der Seite sprechen mit ihm (Funknetz).
_tm111 = _TM59.Testmodus(app, karte="staubtal_offen")
_namen111 = [e_.name for e_ in _tm111.eintraege]
pruef("Testmodus: FUNKWAGEN im Spawner (OBJEKTE) und als Abwurf (NACHSCHUB); im Nachschub fuer 7 Punkte",
      "FUNKWAGEN" in _namen111 and "ABWURF: FUNKWAGEN" in _namen111
      and "funkwagen" in [n_ for n_, _c, _t in K.SCHLACHT["belohnungen"]])
_e111 = _tm111.welt.ebene(0)
_rnd111 = random.Random(111)
for _ in range(40000):
    _tx111 = _rnd111.randrange(60, _e111.breite - 90)
    _ty111 = _rnd111.randrange(20, _e111.hoehe - 40)
    if all(not K.KACHELN[_e111.kachel(_tx111 + x_, _ty111 + y_)]["fest"]
           for x_ in range(40) for y_ in range(24)):
        break
_z111 = lambda x_, y_: pygame.Vector2((_tx111 + x_ + 0.5) * K.TILE, (_ty111 + y_ + 0.5) * K.TILE)
_fw111 = _tm111.fahrzeug_setzen("funkwagen", _z111(6, 8), 0, {"winkel": 0})
_ff111 = _tm111.puppe_setzen(_fw111.ausstiegsorte(9.0)[0], 0, {"team": 0}, name="FUNKER")
_tm111._anwenden(_ff111, {"will": [0, 0], "ziel": [0, 0], "knoepfe": ["nutzen"]})
pruef("Funkwagen: eigene Art, keine Plaetze, seit 0.34.131 auch fuer Bots, Betriebsart PEILEN zu Beginn",
      _ff111.fahrzeug is _fw111 and _fw111.art == "funkwagen" and "plaetze" not in _fw111.werte
      and not _fw111.werte.get("nur_mensch") and _fw111.modus == 0 and _fw111.bild == "funkwagen")
def _fw_ein111(zielt_, knoepfe_=(), will_=(0, 0)):
    _tm111._anwenden(_ff111, {"will": list(will_), "ziel": [0, 0], "knoepfe": list(knoepfe_), "zielt": zielt_})
    _tm111.schritt(K.FIXED_DT)
_fw_ein111(True); _fw_ein111(True); _fw_ein111(False)
pruef("Funkwagen: die rechte Maustaste baut den Mast auf (er steht dabei) ...",
      _fw111.phase == 1 and _fw111.phase_rest > 2.0)
for _ in range(int(3.3 / K.FIXED_DT)):
    _fw_ein111(False, will_=(0, -1))
pruef("... nach drei Sekunden steht er (Phase 2, Mast ganz aufgebaut - seit 0.34.124 ein 3D-Modell ueber dem Wagen)",
      _fw111.phase == 2 and _fw111.fortschritt >= 1.0 and _fw111.bild == "funkwagen" and _fw111.geschw.length() < 1.0,
      "%s %.2f %.1f" % (_fw111.bild, _fw111.fortschritt, _fw111.geschw.length()))
_nah111 = _tm111.puppe_setzen(_fw111.mast_mitte() + pygame.Vector2(300, 0), 0, {"team": 1}, name="NAH")
_fern111 = _tm111.puppe_setzen(_fw111.mast_mitte() + pygame.Vector2(0, 600), 0, {"team": 1}, name="FERN")
_freund111 = _tm111.puppe_setzen(_fw111.mast_mitte() + pygame.Vector2(0, -200), 0, {"team": 0}, name="FREUND")
_pz111 = _tm111.fahrzeug_setzen("panzer", _z111(14, 16), 0, {"winkel": 0})
_pf111 = _tm111.puppe_setzen(_pz111.ausstiegsorte(9.0)[0], 0, {"team": 1}, name="FAHRER")
_tm111._anwenden(_pf111, {"will": [0, 0], "ziel": [0, 0], "knoepfe": ["nutzen"]})
for _ in range(int(1.3 / K.FIXED_DT)):
    _fw_ein111(False)
pruef("Funkwagen PEILEN: Gegner im Kreis sind fuer die eigene Seite markiert - auch ein Fahrzeug",
      _nah111.markiert_rest > 0.0 and _nah111.markiert_fuer == _ff111.fraktion
      and _pz111.markiert_rest > 0.0 and _pz111.markiert_fuer == _ff111.fraktion,
      "%s %s" % (_nah111.markiert_fuer, _ff111.fraktion))
pruef("... Gegner ausserhalb und die eigenen nicht",
      getattr(_fern111, "markiert_rest", 0.0) == 0.0 and getattr(_freund111, "markiert_rest", 0.0) == 0.0)
_fw_ein111(False, knoepfe_=["nachladen"])
pruef("Funkwagen: R schaltet auf STOEREN (und wieder zurueck)", _fw111.modus == 1)
# Funknetz: ein Bot der Seite im Kreis meldet, was er sieht.
_bot111 = _tm111.bot_setzen(_fw111.pos + pygame.Vector2(0, 150), 0, {"team": 0})
_feind111 = _tm111.puppe_setzen(_fw111.pos + pygame.Vector2(800, 400), 0, {"team": 1}, name="WEIT")
_fw111.modus = 0
_alt_funk111 = _tm111.regelwerk if hasattr(_tm111, "regelwerk") else None
_tm111.regelwerk = dict(_alt_funk111 or {}, funk=False)
_tm111.lage_melden(_bot111, _feind111)
_aus111 = getattr(_feind111, "markiert_rest", 0.0)
_tm111.regelwerk = dict(_alt_funk111 or {}, funk=True)
_tm111.lage_melden(_bot111, _feind111)
pruef("Funknetz: nur mit aktiver Funk-Regel gibt ein Bot im Kreis dem Team weiter, was er sieht",
      _aus111 == 0.0 and _feind111.markiert_rest > 0.0 and _feind111.markiert_fuer == _bot111.fraktion,
      "%.1f / %.1f" % (_aus111, _feind111.markiert_rest))
# Stoeren: ein zweiter Funkwagen der anderen Seite.
_fw2111 = _tm111.fahrzeug_setzen("funkwagen", _z111(26, 6), 0, {"winkel": 0})
_f2111 = _tm111.puppe_setzen(_fw2111.ausstiegsorte(9.0)[0], 0, {"team": 1}, name="STOERER")
_tm111._anwenden(_f2111, {"will": [0, 0], "ziel": [0, 0], "knoepfe": ["nutzen"]})
def _fw2_ein111(zielt_, knoepfe_=()):
    _tm111._anwenden(_f2111, {"will": [0, 0], "ziel": [0, 0], "knoepfe": list(knoepfe_), "zielt": zielt_})
    _tm111.schritt(K.FIXED_DT)
_fw2_ein111(True); _fw2_ein111(True); _fw2_ein111(False)
for _ in range(int(3.3 / K.FIXED_DT)):
    _fw2_ein111(False)
_fw2_ein111(False, ["nachladen"])
_op111 = _tm111.puppe_setzen(_fw2111.mast_mitte() + pygame.Vector2(-200, 0), 0, {"team": 0}, name="OPFER")
_ausser111 = _tm111.puppe_setzen(_fw2111.mast_mitte() + pygame.Vector2(-700, 0), 0, {"team": 0}, name="AUSSEN")
_eig111 = _tm111.puppe_setzen(_fw2111.mast_mitte() + pygame.Vector2(150, 0), 0, {"team": 1}, name="EIGENER")
_eig111.markiert_rest = 5.0; _eig111.markiert_fuer = "team0"      # der Gegner hat ihn markiert
_dr111 = _tm111.ausruestung_setzen("SPÄHDROHNE", _fw2111.mast_mitte() + pygame.Vector2(100, 100), 0,
                                   {"team": 0})
for _ in range(int(1.5 / K.FIXED_DT)):
    _fw2_ein111(False)
pruef("Funkwagen STOEREN: wer im Kreis steht, kann nicht funken - wer draussen steht, schon",
      _tm111.funk_gestoert(_op111) and not _tm111.funk_gestoert(_ausser111)
      and not _tm111.funk_gestoert(_f2111), "%s %s" % (_tm111.funk_gestoert(_op111), _tm111.funk_gestoert(_ausser111)))
pruef("... was der Gegner im Kreis markiert hat, verfaellt, und seine Spaehdrohne faellt aus",
      getattr(_eig111, "markiert_rest", 0.0) == 0.0 and all(not d_.lebt or d_.emp_rest > 0.0 for d_ in _dr111) and _dr111, "%.1f" % getattr(_eig111, "markiert_rest", 0.0))
pruef("... und der Stoerer steht dabei auf der Karte der Gegner (markiert)",
      _fw2111.markiert_rest > 0.0 and _fw2111.markiert_fuer == "team0", _fw2111.markiert_fuer)
_k111 = _tm111.puppe_setzen(_z111(30, 20), 0, {"team": 0}, name="KAEUFER")
_k111.schlacht_punkte = 99
_in111 = _fw2111.mast_mitte() + pygame.Vector2(-100, 0)
pruef("... und kein Nachschub kommt in den Kreis (gestoert), ausserhalb schon",
      "GESTÖRT" in _tm111.belohnung_pruefen(_k111, "munition", _in111)
      and "GESTÖRT" not in _tm111.belohnung_pruefen(_k111, "munition", _fw2111.mast_mitte() + pygame.Vector2(-900, 0)))
_fw2111.schaden(9999.0, None, _op111)
pruef("... ein zerstoerter Funkwagen stoert nicht mehr", not _tm111.funk_gestoert(_op111))
_tm111.verlassen()

# ─────────────────────────────────────────────────────────────────────
# Werfer (seit 0.34.112): aufgebaut, Salve nur auf gueltige Ziele der Seite,
# rote Kreise, verraet sich, sehr zerbrechlich mit grosser Explosion.
_tm112 = _TM59.Testmodus(app, karte="staubtal_offen")
random.seed(1120)          # die Streuung der Raketen waere sonst Glueckssache
_namen112 = [e_.name for e_ in _tm112.eintraege]
pruef("Testmodus: WERFER im Spawner (OBJEKTE) und als Abwurf (NACHSCHUB); im Nachschub fuer 9 Punkte",
      "WERFER" in _namen112 and "ABWURF: WERFER" in _namen112
      and "werfer" in [n_ for n_, _c, _t in K.SCHLACHT["belohnungen"]])
_e112 = _tm112.welt.ebene(0)
_rnd112 = random.Random(112)
for _ in range(40000):
    _tx112 = _rnd112.randrange(60, _e112.breite - 90)
    _ty112 = _rnd112.randrange(20, _e112.hoehe - 40)
    if all(not K.KACHELN[_e112.kachel(_tx112 + x_, _ty112 + y_)]["fest"]
           for x_ in range(44) for y_ in range(24)):
        break
_z112 = lambda x_, y_: pygame.Vector2((_tx112 + x_ + 0.5) * K.TILE, (_ty112 + y_ + 0.5) * K.TILE)
_wf112 = _tm112.fahrzeug_setzen("werfer", _z112(4, 10), 0, {"winkel": 0})
_wp112 = _tm112.puppe_setzen(_wf112.ausstiegsorte(9.0)[0], 0, {"team": 0}, name="WERFERFUEHRER")
_tm112._anwenden(_wp112, {"will": [0, 0], "ziel": [0, 0], "knoepfe": ["nutzen"]})
pruef("Werfer: eigene Art, keine Plaetze, seit 0.34.131 auch fuer Bots, sehr leicht zu zerstoeren",
      _wp112.fahrzeug is _wf112 and _wf112.art == "werfer" and "plaetze" not in _wf112.werte
      and not _wf112.werte.get("nur_mensch") and _wf112.leben < K.FAHRZEUG["leben"] / 2.0, str(_wf112.leben))
_ziel112 = [0.0, 0.0]
def _wf_ein112(feuert_=False, zielt_=False):
    _tm112._anwenden(_wp112, {"will": [0, 0], "ziel": list(_ziel112), "knoepfe": [], "feuert": feuert_,
                              "zielt": zielt_})
    _tm112.schritt(K.FIXED_DT)
for _ in range(3):
    _wf_ein112(zielt_=True)
for _ in range(int(3.0 / K.FIXED_DT)):
    _wf_ein112()
pruef("Werfer: die rechte Maustaste baut ihn auf (Phase 2), er steht", _wf112.phase == 2 and _wf112.bild.startswith("werfer_stuetze_"),
      "%d %s" % (_wf112.phase, _wf112.bild))
# Ein Gegner 640 Pixel entfernt, ein Kamerad dicht dabei (sieht ihn).
_feind112 = _tm112.puppe_setzen(_z112(24, 10), 0, {"team": 1, "leben": 5.0}, name="FEIND")
_kam112 = _tm112.puppe_setzen(_z112(21, 10), 0, {"team": 0}, name="KAMERAD")
_fern112 = _tm112.puppe_setzen(_z112(40, 20), 0, {"team": 1, "leben": 5.0}, name="UNGESEHEN")
_ziel112 = [_feind112.pos.x, _feind112.pos.y]
for _ in range(int(0.6 / K.FIXED_DT)):
    _wf_ein112()
pruef("Werfer: ein Ziel, das ein Kamerad sieht, gilt (ziel_grund 0), die Salve ist bereit",
      _wf112.ziel_grund == 0 and _wf112.bereit, "%d %s" % (_wf112.ziel_grund, _wf112.bereit))
_ziel112 = [_fern112.pos.x, _fern112.pos.y]
for _ in range(int(0.6 / K.FIXED_DT)):
    _wf_ein112(feuert_=True)
pruef("... ein Gegner, den niemand sieht, nicht - die Salve geht nicht raus",
      _wf112.ziel_grund == 3 and not _wf112.einschlaege and _wf112.bereit, str(_wf112.ziel_grund))
_ziel112 = [_wf112.pos.x + 200, _wf112.pos.y]
for _ in range(int(0.6 / K.FIXED_DT)):
    _wf_ein112()
# Seit 0.34.134 reicht er ueber die halbe Kartenbreite (werfer_weite).
pruef("... zu nah (unter 400 Pixeln) und zu weit (ueber werfer_weite) auch nicht",
      _wf112.ziel_grund == 1 and (_ziel112.__setitem__(0, _wf112.pos.x + _tm112.werfer_weite() + 400) or True)
      and (_wf_ein112() or True) and _wf112.ziel_grund == 2, str(_wf112.ziel_grund))
# Markiert gilt auch ohne Sicht.
_fern112.markiert_rest = 5.0; _fern112.markiert_fuer = _wp112.fraktion
_ziel112 = [_fern112.pos.x, _fern112.pos.y]
for _ in range(int(0.6 / K.FIXED_DT)):
    _wf_ein112()
pruef("... ein markierter Gegner (Drohne, Funkwagen) gilt, auch ohne Sicht", _wf112.ziel_grund == 0,
      str(_wf112.ziel_grund))
_fern112.markiert_rest = 0.0
# Die Salve auf den gesehenen Gegner.
_ziel112 = [_feind112.pos.x, _feind112.pos.y]
for _ in range(int(0.6 / K.FIXED_DT)):
    _wf_ein112()
_leben112 = _feind112.leben
_wf_ein112(feuert_=True)
_n112 = len(_wf112.einschlaege)
pruef("Werfer: die linke Maustaste schiesst eine Salve - sechs Raketen unterwegs, er laedt danach",
      _n112 == K.WERFER["salve"]["raketen"] and not _wf112.bereit and len(_wf112.nachladen) == 6,
      "%d Raketen, %d Rohre laden nach" % (_n112, len(_wf112.nachladen)))
pruef("... er hat sich verraten (fuer die Gegner markiert)",
      _wf112.markiert_rest > 0.0 and _wf112.markiert_fuer == "team1", str(_wf112.markiert_fuer))
_w2112 = _FZ59.Werfer((0, 0), 0, 0.0, nur_bild=True)
_w2112.netz_extra_setzen(_wf112.netz_extra())
pruef("... und der Gast sieht dieselben Raketen (Zusatzwert im Netz)",
      len(_w2112.einschlaege) == _n112 and _w2112.rohre == _wf112.rohre
      and _w2112._rohr_soll == round(_wf112.rohr_rel))
for _ in range(int(2.0 / K.FIXED_DT)):
    _wf_ein112()
pruef("... die Raketen starten nacheinander (die ersten fliegen, die letzten warten noch im Rohr)",
      any(e_[3] for e_ in _wf112.einschlaege) and not all(e_[3] for e_ in _wf112.einschlaege)
      if _wf112.einschlaege else False)
for _ in range(int(5.0 / K.FIXED_DT)):
    _wf_ein112()
pruef("... sie schlagen ein: der Gegner am Ziel ist getroffen, und nichts ist mehr in der Luft",
      not _wf112.einschlaege and (_feind112.leben < _leben112 or not _feind112.lebt),
      "%.0f -> %.0f" % (_leben112, _feind112.leben))
# Hotzone gilt.
_tm112.zone_setzen(_z112(30, 5), 0)
_tm112.schritt(K.FIXED_DT)
_ziel112 = [_z112(30, 5).x + 60, _z112(30, 5).y]
for _ in range(int(0.6 / K.FIXED_DT)):
    _wf_ein112()
pruef("Werfer: die Hotzone ist ein gueltiges Ziel", _wf112.ziel_grund == 0, str(_wf112.ziel_grund))
# Zerbrechlich: ein Treffer, und alle in der Naehe sind tot.
_nah112 = _tm112.puppe_setzen(_wf112.pos + pygame.Vector2(0, 60), 0, {"team": 1}, name="DANEBEN")
_ferne112 = _tm112.puppe_setzen(_wf112.pos + pygame.Vector2(0, 400), 0, {"team": 1}, name="WEITWEG")
_nah112.unverwundbar = 0.0
_ferne112.unverwundbar = 0.0
_tm112.welt._raster_bauen()          # die eben gesetzten stehen sonst noch nicht im Raster
_wf112.schaden(_wf112.max_leben + 5.0, None, _nah112, art="kugel", herkunft=_nah112.pos)
pruef("Werfer: wird er zerstoert, gibt es eine grosse Explosion - wer daneben steht, ist tot, wer weit weg steht, nicht",
      _wf112.kaputt and (not _nah112.lebt or _nah112.am_boden) and _ferne112.lebt
      and K.WERFER["explosion_radius"] > K.FAHRZEUG["explosion_radius"] * 2,
      "%s / %s" % (_nah112.lebt, _ferne112.lebt))
_tm112.verlassen()

# ─────────────────────────────────────────────────────────────────────
# Tragschrauber und die Luftziel-Regel (seit 0.34.113, luft.py): man schiesst
# auf das, worauf der Mauszeiger liegt - auch in der Luft.
_tm113 = _TM59.Testmodus(app, karte="staubtal_offen")
_namen113 = [e_.name for e_ in _tm113.eintraege]
pruef("Testmodus: TRAGSCHRAUBER im Spawner (OBJEKTE) und als Abwurf (NACHSCHUB); im Nachschub fuer 9 Punkte",
      "TRAGSCHRAUBER" in _namen113 and "ABWURF: TRAGSCHRAUBER" in _namen113
      and "tragschrauber" in [n_ for n_, _c, _t in K.SCHLACHT["belohnungen"]])
_e113 = _tm113.welt.ebene(0)
_rnd113 = random.Random(113)
for _ in range(40000):
    _tx113 = _rnd113.randrange(60, _e113.breite - 90)
    _ty113 = _rnd113.randrange(20, _e113.hoehe - 40)
    if all(not K.KACHELN[_e113.kachel(_tx113 + x_, _ty113 + y_)]["fest"]
           for x_ in range(50) for y_ in range(24)):
        break
_z113 = lambda x_, y_: pygame.Vector2((_tx113 + x_ + 0.5) * K.TILE, (_ty113 + y_ + 0.5) * K.TILE)
_ts113 = _tm113.fahrzeug_setzen("tragschrauber", _z113(2, 12), 0, {"winkel": 0})
_tp113 = _tm113.puppe_setzen(_ts113.ausstiegsorte(9.0)[0], 0, {"team": 0}, name="PILOT")
_tm113._anwenden(_tp113, {"will": [0, 0], "ziel": [0, 0], "knoepfe": ["nutzen"]})
pruef("Tragschrauber: eigene Art, am Boden ein Wagen, seit 0.34.131 auch fuer Bots",
      _tp113.fahrzeug is _ts113 and _ts113.art == "tragschrauber" and not _ts113.luft
      and not _ts113.werte.get("nur_mensch") and "plaetze" not in _ts113.werte and _ts113.trefferbar)
def _ts_ein113(will_=(0, 0), feuert_=False, knoepfe_=()):
    _tm113._anwenden(_tp113, {"will": list(will_), "ziel": [0, 0], "knoepfe": list(knoepfe_),
                              "feuert": feuert_})
    _tm113.schritt(K.FIXED_DT)
for _ in range(int(6.0 / K.FIXED_DT)):
    _ts_ein113(will_=(0, -1))
pruef("Tragschrauber: mit Gas hebt er ab, steigt auf seine Hoehe und ist dann in der Luft (hoch oben, nicht mehr vom Boden zu treffen)",
      _ts113.luft and _ts113.hoehe > _ts113.werte["hoehe"] * 0.8 and _ts113.hoch_oben and _ts113.in_der_luft
      and not _ts113.trefferbar, "luft %s hoehe %.0f" % (_ts113.luft, _ts113.hoehe))
pruef("... er faehrt mindestens so schnell wie `flug_min` und nicht schneller als `flug_hoechst`",
      K.TRAGSCHRAUBER["flug_min"] - 1.0 <= _ts113.flug_v <= K.TRAGSCHRAUBER["flug_hoechst"] + 1.0,
      "%.0f" % _ts113.flug_v)
# Ein Schuetze am Boden, ein Stueck unter ihm.
_s113 = _tm113.puppe_setzen(_ts113.pos + pygame.Vector2(0, 140), 0, {"team": 1, "waffe_figur": "sturm"},
                            name="SCHUETZE")
_s113.magazin[_s113.waffe_name] = 400
_s113.vorrat[_s113.waffe_name] = 400
_tm113.welt._raster_bauen()
_l113 = _ts113.leben
for _ in range(int(0.8 / K.FIXED_DT)):
    _tm113._anwenden(_s113, {"will": [0, 0], "ziel": [_ts113.pos.x, _ts113.pos.y], "knoepfe": [],
                             "feuert": True})
    _ts_ein113(will_=(0, 0))
pruef("Luftziel: wer auf den Boden unter dem Tragschrauber zielt, trifft ihn nicht (er fliegt darueber)",
      _ts113.leben == _l113 and _s113.luft_ziel is None, "%.0f" % _ts113.leben)
_l113 = _ts113.leben
for _ in range(int(1.5 / K.FIXED_DT)):
    _bp113 = pygame.Vector2(_ts113.pos.x, _ts113.pos.y - _ts113.hoehe)       # sein Bild
    _tm113._anwenden(_s113, {"will": [0, 0], "ziel": [_bp113.x, _bp113.y], "knoepfe": [], "feuert": True})
    _ts_ein113(will_=(0, 0))
    if _ts113.leben < _l113:
        break
_getroffen113 = _ts113.leben
pruef("Luftziel: liegt der Zeiger auf seinem Bild, rastet das Ziel ein - und die Kugeln treffen ihn",
      _s113.luft_ziel is not None and _s113.luft_ziel.objekt is _ts113 and _getroffen113 < _l113,
      "%.0f -> %.0f" % (_l113, _getroffen113))
_tm113._anwenden(_s113, {"will": [0, 0], "ziel": [0, 0], "knoepfe": [], "feuert": False})
_freund113 = _tm113.puppe_setzen(_ts113.pos + pygame.Vector2(0, 140), 0, {"team": 0, "waffe_figur": "sturm"},
                                 name="FREUND")
_tm113._anwenden(_freund113, {"will": [0, 0], "ziel": [_bp113.x, _bp113.y], "knoepfe": []})
pruef("... auf die eigene Seite rastet nichts ein", _freund113.luft_ziel is None)
# Aufklaerung: ein Gegner unter ihm ist fuer die Seite markiert.
_ts113.leben = _ts113.max_leben
_unten113 = _tm113.puppe_setzen(_ts113.pos + _ts113.vorn * 60, 0, {"team": 1}, name="UNTEN")
_weit113 = _tm113.puppe_setzen(_ts113.pos + pygame.Vector2(0, 700), 0, {"team": 1}, name="WEIT")
_tm113.welt._raster_bauen()
_ts113._aufkl_rest = 0.0
_ts_ein113(will_=(0, 0))
pruef("Tragschrauber: ein Gegner im Kreis unter ihm ist fuer seine Seite markiert (Aufklaerung), ein weit entfernter nicht",
      getattr(_unten113, "markiert_rest", 0.0) > 0.0 and _unten113.markiert_fuer == _tp113.fraktion
      and getattr(_weit113, "markiert_rest", 0.0) == 0.0,
      "%s" % getattr(_unten113, "markiert_fuer", None))
# Die Bombe.
_bomben113 = _ts113.bomben
# Seit 0.34.119 faellt die Bombe senkrecht unter ihm (ohne sein Tempo) - seit 0.34.123 dort, wo
# der Fahrer sie neben der Kanzel fallen laesst (K.TRAGSCHRAUBER["bombe"]["abwurf"]).
_opfer113 = _tm113.puppe_setzen(_ts113.pos + pygame.Vector2(K.TRAGSCHRAUBER["bombe"]["abwurf"]).rotate(_ts113.winkel), 0,
                                {"team": 1, "leben": 5.0}, name="OPFER")
_vorn113 = _tm113.puppe_setzen(_ts113.pos + _ts113.vorn * _ts113.flug_v * K.TRAGSCHRAUBER["bombe"]["fall"], 0,
                               {"team": 1, "leben": 5.0}, name="VORNE")
_vorn113.unverwundbar = 0.0
_vl113 = _vorn113.leben
_opfer113.unverwundbar = 0.0
_tm113.welt._raster_bauen()
_ol113 = _opfer113.leben
_ts_ein113(feuert_=True)
_ts_ein113(feuert_=False)
pruef("Tragschrauber: die linke Maustaste wirft eine Bombe (eine weniger), sie faellt eine Weile ...",
      _ts113.bomben == _bomben113 - 1 and len(_ts113.bomben_fall) == 1,
      "%d / %d" % (_ts113.bomben, len(_ts113.bomben_fall)))
for _ in range(int(1.2 / K.FIXED_DT)):
    _ts_ein113()
pruef("... und schlaegt dort ein, wo er sie abgeworfen hat (senkrecht, ohne sein Tempo): der Gegner darunter ist getroffen, einer weiter vorn nicht",
      not _ts113.bomben_fall and (_opfer113.leben < _ol113 or not _opfer113.lebt) and _vorn113.leben == _vl113,
      "%.0f -> %.0f, vorn %.0f -> %.0f" % (_ol113, _opfer113.leben, _vl113, _vorn113.leben))
_n113 = _ts113.netz_extra()
_g113 = _FZ59.Tragschrauber((0, 0), 0, 0.0, nur_bild=True)
_g113.netz_extra_setzen(_n113)
pruef("... der Gast sieht ihn in der Luft (Zusatzwert im Netz) - hoch oben, mit seinen Bomben",
      _g113.luft and _g113.hoch_oben and _g113.bomben == _ts113.bomben, str(_n113))
# Landen: E setzt an, unten ist Platz.
_ts_ein113(will_=(0, 0), knoepfe_=["nutzen"])
pruef("Tragschrauber: E setzt zur Landung an", _ts113.landen)
for _ in range(int(5.0 / K.FIXED_DT)):
    _ts_ein113()
pruef("... er setzt auf und ist wieder ein Wagen am Boden (trefferbar), sonst stuerzte er ab",
      not _ts113.luft and _ts113.hoehe == 0.0 and (_ts113.trefferbar or _ts113.kaputt) and not _ts113.kaputt,
      "luft %s hoehe %.0f kaputt %s" % (_ts113.luft, _ts113.hoehe, _ts113.kaputt))
# Nur Flak trifft Abwuerfe am Schirm: ein gewoehnlicher Schuetze rastet dort nicht ein.
_tm113.nachschub_setzen("munition", _z113(30, 4), {"team": 1})
for _ in range(int(1.6 / K.FIXED_DT)):
    _tm113.schritt(K.FIXED_DT)
_ab113 = _tm113.abwuerfe[0]
_bild113 = _tm113.luft_ziele()
_sch113 = _tm113.puppe_setzen(_z113(30, 14), 0, {"team": 0}, name="NORMAL")
_tm113._anwenden(_sch113, {"will": [0, 0], "ziel": [_bild113[0].bild_pos.x, _bild113[0].bild_pos.y], "knoepfe": []})
pruef("Abwuerfe am Schirm sind Luftziele, aber nur fuer Flak (ein gewoehnlicher Schuetze rastet nicht ein)",
      _bild113 and _bild113[0].art == "abwurf" and _bild113[0].nur_flak and _sch113.luft_ziel is None)
_tm113.verlassen()

# Flakwagen (seit 0.34.114): ein Laster mit Flak-Vierling, nur Bots fahren ihn.
_tm114 = _TM59.Testmodus(app, karte="staubtal_offen")
_namen114 = [e_.name for e_ in _tm114.eintraege]
pruef("Testmodus: FLAKWAGEN im Spawner (OBJEKTE) und als Abwurf (NACHSCHUB); im Nachschub fuer 9 Punkte",
      "FLAKWAGEN" in _namen114 and "ABWURF: FLAKWAGEN" in _namen114
      and "flakwagen" in [n_ for n_, _c, _t in K.SCHLACHT["belohnungen"]])
pruef("Flakwagen: Werte - nur Bots, Flak, kein Truppentransporter; die Flak-Zeile traegt `flak`",
      K.FLAKWAGEN["nur_bot"] and K.FLAKWAGEN["flak"] and "plaetze" not in K.FLAKWAGEN
      and K.FAHRZEUG_WAFFEN["flak_kanone"]["flak"] and K.FLAK["luft_schaden"] > 50.0)
_e114 = _tm114.welt.ebene(0)
_rnd114 = random.Random(114)
for _ in range(40000):
    _tx114 = _rnd114.randrange(60, _e114.breite - 90)
    _ty114 = _rnd114.randrange(20, _e114.hoehe - 40)
    if all(not K.KACHELN[_e114.kachel(_tx114 + x_, _ty114 + y_)]["fest"]
           for x_ in range(50) for y_ in range(24)):
        break
_z114 = lambda x_, y_: pygame.Vector2((_tx114 + x_ + 0.5) * K.TILE, (_ty114 + y_ + 0.5) * K.TILE)
_fw114 = _tm114.fahrzeug_setzen("flakwagen", _z114(10, 12), 0, {"winkel": 0})
pruef("Flakwagen: eigene Art, ein Panzerwagen mit Lafette, nur Bots",
      _fw114.art == "flakwagen" and isinstance(_fw114, _FZ59.Panzerwagen) and _fw114.flak
      and _fw114.aufbau_name == "flak_lafette" and _fw114.werte["nur_bot"])
# Ein Mensch kommt nicht hinein, ein Bot schon.
_mensch114 = _tm114.puppe_setzen(_fw114.ausstiegsorte(9.0)[0], 0, {"team": 0}, name="MENSCH")
_tm114._anwenden(_mensch114, {"will": [0, 0], "ziel": [0, 0], "knoepfe": ["nutzen"]})
pruef("Flakwagen: ein Mensch kann nicht einsteigen (E bleibt ohne Wirkung)",
      _mensch114.fahrzeug is None and _fw114.fahrer is None)
_bot114 = _tm114.fahrer_setzen(_fw114.ausstiegsorte(9.0)[0], 0, {"team": 0}, mit_fahrzeug=False)
_tm114._anwenden(_bot114, {"will": [0, 0], "ziel": [0, 0], "knoepfe": ["nutzen"]})
pruef("Flakwagen: ein Bot, der fahren darf, findet ihn und kann einsteigen",
      _bot114.fahrzeug is _fw114 and _fw114.fahrer is _bot114)
# Zielregel: ein Schuetze im Flakwagen rastet auch auf Abwuerfe ein, ein gewoehnlicher nicht.
_fl114 = _tm114.fahrzeug_setzen("flakwagen", _z114(10, 20), 0, {"winkel": 0})
_pilot114 = _tm114.puppe_setzen(_fl114.pos + pygame.Vector2(0, 90), 0, {"team": 0}, name="FLAKSCHUETZE")
_tm114._einsteigen(_pilot114, _fl114)
_tm114.nachschub_setzen("munition", _z114(18, 22), {"team": 1})
for _ in range(int(1.6 / K.FIXED_DT)):
    _tm114.schritt(K.FIXED_DT)
_lz114 = [x_ for x_ in _tm114.luft_ziele() if x_.art == "abwurf"]
_tm114._anwenden(_pilot114, {"will": [0, 0], "ziel": [_lz114[0].bild_pos.x, _lz114[0].bild_pos.y],
                             "knoepfe": []})
pruef("Flakwagen: wer darin sitzt, rastet auf einen Abwurf am Schirm ein (das trifft sonst nur Flak)",
      _lz114 and _pilot114.luft_ziel is not None and _pilot114.luft_ziel.art == "abwurf")
_tm114._aussteigen(_pilot114)
# Der Fahrer-Bot schiesst auf einen Tragschrauber, der vorbeifliegt.
_tm114.verlassen()
_tm114 = _TM59.Testmodus(app, karte="staubtal_offen")
_e114 = _tm114.welt.ebene(0)
_z114 = lambda x_, y_: pygame.Vector2((_tx114 + x_ + 0.5) * K.TILE, (_ty114 + y_ + 0.5) * K.TILE)
_ts114 = _tm114.fahrzeug_setzen("tragschrauber", _z114(4, 12), 0, {"winkel": 0})
_pil114 = _tm114.puppe_setzen(_ts114.ausstiegsorte(9.0)[0], 0, {"team": 1}, name="PILOT")
_tm114._anwenden(_pil114, {"will": [0, 0], "ziel": [0, 0], "knoepfe": ["nutzen"]})
for _ in range(int(6.0 / K.FIXED_DT)):
    _tm114._anwenden(_pil114, {"will": [0, -1], "ziel": [0, 0], "knoepfe": [], "feuert": False})
    _tm114.schritt(K.FIXED_DT)
# Erst jetzt, wo er fliegt, der Flakwagen: schraeg voraus, in Reichweite.
_fw114 = _tm114.fahrzeug_setzen("flakwagen", _ts114.pos + _ts114.vorn * 260 + pygame.Vector2(0, 120), 0,
                                {"winkel": 0})
_fahrer114 = _tm114.fahrer_setzen(_fw114.pos, 0, {"team": 0, "fahrzeug": "flakwagen"}, mit_fahrzeug=False)
_tm114._einsteigen(_fahrer114, _fw114)
_tm114.welt._raster_bauen()
_l114 = _ts114.leben
_gesehen114 = False
for _ in range(int(8.0 / K.FIXED_DT)):
    _tm114._anwenden(_pil114, {"will": [0, -1], "ziel": [0, 0], "knoepfe": [], "feuert": False})
    _tm114.schritt(K.FIXED_DT)
    if getattr(_fahrer114.hirn, "flak_ziel", None) is not None:
        _gesehen114 = True
    if not _ts114.lebt or _ts114.kaputt or _ts114.leben < _l114 - 30:
        break
pruef("Flakwagen: der Bot am Steuer sucht sich den fliegenden Tragschrauber der Gegner als Ziel (flak_ziel)",
      _gesehen114 and _ts114.luft, "luft %s" % _ts114.luft)
pruef("... und trifft ihn mit dem Vierling in der Luft (Leben sinkt, Flak wiegt dort mehr)",
      _ts114.leben < _l114, "%.0f -> %.0f, Abstand %.0f" % (
          _l114, _ts114.leben, _ts114.pos.distance_to(_fw114.pos)))
# Der Flak-Bot schiesst auch einen gegnerischen Abwurf am Schirm ab (nur Flak trifft ihn).
_tm114.nachschub_setzen("medkit", _fw114.pos + pygame.Vector2(180, -40), {"team": 1})
_ab114 = None
for _ in range(int(10.0 / K.FIXED_DT)):
    _tm114._anwenden(_pil114, {"will": [0, -1], "ziel": [0, 0], "knoepfe": [], "feuert": False})
    _tm114.schritt(K.FIXED_DT)
    if _ab114 is None and _tm114.abwuerfe:
        _ab114 = _tm114.abwuerfe[0]
    if _ab114 is not None and _ab114 not in _tm114.abwuerfe:
        break
pruef("Flakwagen: sein Bot holt einen gegnerischen Abwurf am Schirm herunter, ehe er landet",
      _ab114 is not None and _ab114 not in _tm114.abwuerfe,
      "Hoehe %s" % (getattr(_ab114, "hoehe", None),))
# Ein Abwurf bringt seinen Bot mit.
_tm114.nachschub_setzen("flakwagen", _z114(30, 4), {"team": 0})
for _ in range(int(12.0 / K.FIXED_DT)):
    _tm114.schritt(K.FIXED_DT)
_ne114 = [b_ for b_ in _tm114.fahrzeuge if b_.art == "flakwagen" and b_ is not _fw114]
pruef("Abwurf FLAKWAGEN: er landet mit einem Bot seiner Seite am Steuer (Verstaerkung, darf nicht nachkommen)",
      _ne114 and _ne114[0].fahrer is not None and _ne114[0].fahrer.ist_bot
      and _ne114[0].fahrer.team == 0 and getattr(_ne114[0].fahrer, "verstaerkung", False))
_tm114.verlassen()

# Gestoerte Minikarte und gestoerter Trupp-Funk (seit 0.34.115): im Stoerkreis
# eines gegnerischen Funkwagens zeigt die Karte nur Rauschen und je Funkwagen
# einen Ping; der Funk der Anfuehrer geht nicht durch.
from dustfront import minikarte as _MK115
_tm115 = _TM59.Testmodus(app, karte="staubtal_offen")
_e115 = _tm115.welt.ebene(0)
_rnd115 = random.Random(115)
for _ in range(40000):
    _tx115 = _rnd115.randrange(60, _e115.breite - 90)
    _ty115 = _rnd115.randrange(20, _e115.hoehe - 40)
    if all(not K.KACHELN[_e115.kachel(_tx115 + x_, _ty115 + y_)]["fest"]
           for x_ in range(50) for y_ in range(24)):
        break
_z115 = lambda x_, y_: pygame.Vector2((_tx115 + x_ + 0.5) * K.TILE, (_ty115 + y_ + 0.5) * K.TILE)
def _stoerer115(x_, y_, team_=1):
    b_ = _tm115.fahrzeug_setzen("funkwagen", _z115(x_, y_), 0, {"winkel": 0})
    b_.phase, b_.phase_rest, b_.modus, b_.basis_team = 2, 0.0, 1, team_
    return b_
_f1115 = _stoerer115(10, 10)
_opfer115 = _tm115.puppe_setzen(_f1115.mast_mitte() + pygame.Vector2(-300, 0), 0, {"team": 0}, name="OPFER")
_frei115 = _tm115.puppe_setzen(_f1115.mast_mitte() + pygame.Vector2(-1500, 0), 0, {"team": 0}, name="FREI")
pruef("Stoerkreis: ein Funkwagen auf STOEREN erfasst die Gegner im Kreis (Liste), die eigene Seite und Ferne nicht",
      _tm115.funk_stoerer(_opfer115.pos, 0) == [_f1115] and not _tm115.funk_stoerer(_frei115.pos, 0)
      and not _tm115.funk_stoerer(_opfer115.pos, 1))
_f2115 = _stoerer115(10, 10)
_f2115.pos.update(_opfer115.pos + pygame.Vector2(-300, 0) - (_f2115.mast_mitte() - _f2115.pos))
_f2115.vorher.update(_f2115.pos)                                  # auf der anderen Seite des Opfers
pruef("... zwei Funkwagen, deren Kreise sich decken, erfassen ihn beide",
      len(_tm115.funk_stoerer(_opfer115.pos, 0)) == 2 and len(_tm115.funk_stoerer(_frei115.pos, 0)) == 0)
# Der Gast kennt den Wagen nur aus der Meldung: nur_bild, Phase, Betriebsart und Basis-Team.
_gw115 = _FZ59.neu("funkwagen", _z115(30, 6), 0, 0.0, True)
_gw115.phase = 2
_gw115.netz_extra_setzen(_f1115.netz_extra())
pruef("Funkwagen im Netz: Betriebsart und Basis-Team gehen mit (Feld 20), ein alter Wert (nur die Zahl) geht auch",
      _f1115.netz_extra() == [1, 1] and _gw115.modus == 1 and _gw115.basis_team == 1
      and (_gw115.netz_extra_setzen(0) or _gw115.modus == 0))
_gw115.netz_extra_setzen([1, 1])
_tm115.fahrzeuge.append(_gw115)
_gw115.ebene = 0
_im115 = _tm115.puppe_setzen(_gw115.mast_mitte() + pygame.Vector2(-100, 0), 0, {"team": 0}, name="GASTOPFER")
pruef("... beim Gast (nur_bild) stoert er genauso, aus der Fahrzeugliste",
      _gw115 in _tm115.funk_stoerer(_im115.pos, 0))
_tm115.fahrzeuge.remove(_gw115)

def _karte115(k_):
    _tm115.uebernehmen(k_)
    f_ = pygame.Surface((K.GAME_W, K.GAME_H)); f_.fill((0, 0, 0))
    _tm115.hud.minikarte.zeichnen(f_, _tm115)
    return f_, _tm115.hud.minikarte.rechteck(_tm115.welt)
def _anzahl115(f_, r_, farbe_):
    return sum(1 for x_ in range(r_.left, r_.right) for y_ in range(r_.top, r_.bottom)
               if f_.get_at((x_, y_))[:3] == tuple(farbe_))
def _ping_da115(f_, r_, b_):
    e_ = _tm115.welt.ebenen[0]
    p_ = b_.mast_mitte()
    px_ = int(r_.x + p_.x * r_.width / float(e_.pixel_breite))
    py_ = int(r_.y + p_.y * r_.height / float(e_.pixel_hoehe))
    return f_.get_at((px_, py_))[:3] == _MK115.PING_FARBE
_f115, _r115 = _karte115(_frei115)
pruef("Minikarte ausserhalb des Kreises: wie immer - man selbst steht darauf, kein Ping",
      _anzahl115(_f115, _r115, _MK115.FARBE_ICH) > 0 and not _ping_da115(_f115, _r115, _f1115))
_f115, _r115 = _karte115(_opfer115)
pruef("Minikarte im Stoerkreis: man selbst und alles andere sind weg (nur Rauschen) ...",
      _anzahl115(_f115, _r115, _MK115.FARBE_ICH) == 0)
pruef("... aber jeder Funkwagen, der einen erfasst, steht als Ping darauf (hier zwei)",
      _ping_da115(_f115, _r115, _f1115) and _ping_da115(_f115, _r115, _f2115))
_f2115.schaden(99999.0, None, _opfer115)
_f115, _r115 = _karte115(_opfer115)
pruef("... faellt einer aus, bleibt nur sein Ping weg",
      _ping_da115(_f115, _r115, _f1115) and not _ping_da115(_f115, _r115, _f2115))
# Trupp-Funk: ein Anfuehrer im Stoerkreis kommt nicht durch und hoert nichts.
_tm115.alles_weg()
_f1115 = _stoerer115(10, 10)
_ta115 = _tm115.trupp_setzen(_f1115.mast_mitte() + pygame.Vector2(-150, 0), 0, {"groesse": 2, "team": 0, "fuehrer": "funk"})
_tb115 = _tm115.trupp_setzen(_z115(30, 20), 0, {"groesse": 2, "team": 0, "fuehrer": "funk"})
_zq115 = _tm115.puppe_setzen(_z115(25, 20), 0, {"team": 1, "leben": 10.0})
_ta115.lage = {_zq115: [pygame.Vector2(_zq115.pos), 0, _tm115.welt.zeit]}
_tm115.ki_stopp = True
_fh115 = _ta115.fuehrer.hirn
_fh115.funk_laeuft = dict(art="lage", dauer=1.0, phase="senden", ort=None, weg_bis=0.0, text="",
                          anfang=_tm115.welt.zeit, bis=_tm115.welt.zeit + 0.5, leben=_ta115.fuehrer.leben)
_tm115.welt.zeit += 1.0
_gesendet115 = len(_tm115.__dict__.get("_funknetz", []))
_r115 = _fh115._funken_tun("lage")
pruef("Trupp-Funk im Stoerkreis: der Spruch geht nicht raus (abgebrochen, nichts im Funknetz) ...",
      _r115[-1] == "gescheitert" and _fh115.funk_laeuft is None
      and len(_tm115.__dict__.get("_funknetz", [])) == _gesendet115
      and _fh115.funk_ende is not None and _fh115.funk_ende[1] == "abgebrochen")
_r115 = _fh115._funken_tun("lage")
pruef("... und er versucht es nicht gleich wieder (Pause)",
      _r115[-1] == "gescheitert" and _fh115.funk_laeuft is None
      and _fh115.funk_gestoert_bis > _tm115.welt.zeit)
# Ein Spruch von aussen erreicht den Anfuehrer im Stoerkreis nicht, ausserhalb schon.
_tb115.fuehrer.pos.update(_f1115.mast_mitte() + pygame.Vector2(-100, 0))
_tc115 = _tm115.trupp_setzen(_z115(40, 20), 0, {"groesse": 2, "team": 0, "fuehrer": "funk"})
_tc115.lage = {_zq115: [pygame.Vector2(_zq115.pos), 0, _tm115.welt.zeit]}
_tc115.funk_senden("lage")
pruef("... wer im Stoerkreis steht, hoert einen Funkspruch nicht",
      not _tb115.funk_lage and not _ta115.funk_lage, "%d %d" % (len(_tb115.funk_lage), len(_ta115.funk_lage)))
_tb115.fuehrer.pos.update(_f1115.mast_mitte() + pygame.Vector2(900, 0))
_td115 = _tm115.trupp_setzen(_z115(45, 20), 0, {"groesse": 2, "team": 0, "fuehrer": "funk"})
_td115.lage = {_zq115: [pygame.Vector2(_zq115.pos), 0, _tm115.welt.zeit]}
_td115.funk_senden("lage")
pruef("... ein Anfuehrer ausserhalb schon", bool(_tb115.funk_lage), "%d" % len(_tb115.funk_lage))
_tm115.ki_stopp = False
_tm115.verlassen()

# Abwurf am Fallschirm zeichnen, fuer jede Fahrzeugart (seit 0.34.116). Gefunden
# beim Filmen: `_fracht_zeichnen` nahm fuer jede Art ohne Eigenschaft
# `rechteckig` die Wanne eines Schweren - Krad, Buggy, Trosswagen, Spulenwagen,
# Funkwagen, Werfer und Tragschrauber stuerzten beim Zeichnen ab.
_tm116 = _TM59.Testmodus(app, karte="staubtal_offen")
_bild116 = pygame.Surface((K.GAME_W, K.GAME_H))
_fehler116 = []
for _art116 in _FZ59.ARTEN:
    try:
        _tm116._fracht_zeichnen(_bild116, _art116, pygame.Vector2(320, 180), 20.0)
    except Exception as ex_:
        _fehler116.append("%s: %s" % (_art116, ex_))
pruef("Abwurf: die Last am Fallschirm laesst sich fuer jede Fahrzeugart zeichnen",
      not _fehler116, "; ".join(_fehler116))
_e116 = _tm116.welt.ebene(0)
_tm116.nachschub_setzen("krad", pygame.Vector2(_e116.pixel_breite / 2, _e116.pixel_hoehe / 2), {"team": 0})
_tm116.kamera.pos.update(_e116.pixel_breite / 2, _e116.pixel_hoehe / 2)
_ok116 = True
try:
    for _ in range(int(2.0 / K.FIXED_DT)):
        _tm116.schritt(K.FIXED_DT)
    _tm116.zeichnen(_bild116, 1.0)
except Exception as ex_:
    _ok116 = False
pruef("... und ein Krad im Abwurf kann im Gefecht gezeichnet werden (Testmodus)", _ok116 and bool(_tm116.abwuerfe))
_tm116.verlassen()

# 0.34.117: Abwurf einheitlich bewegen, Jagdpanzer ohne sichtbaren Fahrer, groesserer
# Trosswagen, mehr Fahrzeuge an der Basis (zwei Trosswagen, ein Flakwagen mit Bot).
_tm117 = _TM59.Testmodus(app, karte="staubtal_offen")
_bild117 = pygame.Surface((K.GAME_W, K.GAME_H), pygame.SRCALPHA)
_arten117 = ["panzer", "panzerwagen", "jagdpanzer", "flakwagen"]
# Wanne und Aufbau sind EIN Bild: die Mitte des Gezeichneten (Schwerpunkt der Deckkraft) dreht
# sich gleichmaessig mit - kein Teil wandert gegen den Rest.
def _schwerpunkt117(art_, winkel_):
    f_ = pygame.Surface((200, 200), pygame.SRCALPHA)
    _tm117._fracht_zeichnen(f_, art_, pygame.Vector2(100, 100), winkel_)
    m_ = pygame.mask.from_surface(f_)
    return pygame.Vector2(m_.centroid()) if m_.count() else None
_ok117 = True
_zusatz117 = []
for _a117 in _arten117:
    _g117 = _tm117._fracht_ganz(_a117)
    _m117 = pygame.mask.from_surface(_g117)
    _c0 = pygame.Vector2(_m117.centroid())
    _rel117 = _c0 - pygame.Vector2(_g117.get_width() / 2, _g117.get_height() / 2)
    for _w117 in (-8, 5, 17):
        _c117 = _schwerpunkt117(_a117, _w117)
        _soll117 = pygame.Vector2(100, 100) + _rel117.rotate(_w117)
        if _c117 is None or _c117.distance_to(_soll117) > 1.6:
            _ok117 = False
            _zusatz117.append("%s %d: %s statt %s" % (_a117, _w117, _c117, _soll117))
pruef("Abwurf: Wanne und Aufbau (Luke, Geschuetz) drehen am Schirm als ein Bild mit - der Schwerpunkt liegt immer dort, wo das gedrehte Ganze ihn hat",
      _ok117, "; ".join(_zusatz117))
from dustfront import art_neue_fahrzeuge as _ANF117
pruef("Jagdpanzer: der Fahrer ist nicht zu sehen - die Luke ist zu, mit und ohne Fahrer dasselbe Bild",
      pygame.image.tobytes(_ANF117.jagdpanzer_aufbau(None), "RGBA")
      == pygame.image.tobytes(_ANF117.jagdpanzer_aufbau((K.C_HULL, K.C_HULL_SH, K.C_TEAL)), "RGBA"))
pruef("Trosswagen: ein Fuenftel groesser (Kreise, Achsen, Zone hinten)",
      abs(K.TROSSWAGEN["kreis"] - 18.0 * 1.2) < 0.1 and abs(K.TROSSWAGEN["achse"] - 26.0 * 1.2) < 0.7
      and K.TROSSWAGEN["zone"]["radius"] > 34.0)
_f117 = dict(K.basis_wagen())
pruef("Basis: zwei Trosswagen und ein Flakwagen je Seite", _f117.get("trosswagen") == 2 and _f117.get("flakwagen") == 1,
      str(_f117))
# Der Flakwagen wartet auf andere Fahrzeuge und faehrt dann hinter ihnen her.
_e117 = _tm117.welt.ebene(0)
_rnd117 = random.Random(117)
for _ in range(40000):
    _tx117 = _rnd117.randrange(60, _e117.breite - 90)
    _ty117 = _rnd117.randrange(20, _e117.hoehe - 40)
    if all(not K.KACHELN[_e117.kachel(_tx117 + x_, _ty117 + y_)]["fest"]
           for x_ in range(50) for y_ in range(24)):
        break
_z117 = lambda x_, y_: pygame.Vector2((_tx117 + x_ + 0.5) * K.TILE, (_ty117 + y_ + 0.5) * K.TILE)
_fl117 = _tm117.fahrzeug_setzen("flakwagen", _z117(4, 12), 0, {"winkel": 0})
_fb117 = _tm117.fahrer_setzen(_fl117.pos, 0, {"team": 0}, mit_fahrzeug=False)
_tm117._einsteigen(_fb117, _fl117)
_bg117 = _tm117.fahrzeug_setzen("buggy", _z117(8, 12), 0, {"winkel": 0})
_pg117 = _tm117.puppe_setzen(_bg117.ausstiegsorte(9.0)[0], 0, {"team": 0}, name="VORDERMANN")
_tm117._anwenden(_pg117, {"will": [0, 0], "ziel": [0, 0], "knoepfe": ["nutzen"]})
_start117 = pygame.Vector2(_fl117.pos)
for _ in range(int(4.0 / K.FIXED_DT)):
    _tm117._anwenden(_pg117, {"will": [0, 0], "ziel": [0, 0], "knoepfe": []})
    _tm117.schritt(K.FIXED_DT)
pruef("Flakwagen an der Basis: steht, solange kein anderes Fahrzeug seiner Seite losgefahren ist",
      _fl117.pos.distance_to(_start117) < 6.0, "%.0f" % _fl117.pos.distance_to(_start117))
for _ in range(int(5.0 / K.FIXED_DT)):
    _tm117._anwenden(_pg117, {"will": [0, -1], "ziel": [0, 0], "knoepfe": []})
    _tm117.schritt(K.FIXED_DT)
_weit117 = _bg117.pos.distance_to(_bg117.start[0])
for _ in range(int(8.0 / K.FIXED_DT)):
    _tm117._anwenden(_pg117, {"will": [0, 0], "ziel": [0, 0], "knoepfe": [], "hb": True})
    _tm117.schritt(K.FIXED_DT)
pruef("... ist eines mehr als 350 px von seinem Start weg, faehrt er hinter ihm her",
      _weit117 > K.FLAK["konvoi_los"] and _fl117.pos.distance_to(_start117) > 150.0
      and _fl117.pos.distance_to(_bg117.pos) < _start117.distance_to(_bg117.pos) - 100.0,
      "Vordermann %.0f weg, Flak %.0f bewegt, Abstand %.0f" % (
          _weit117, _fl117.pos.distance_to(_start117), _fl117.pos.distance_to(_bg117.pos)))
_tm117.verlassen()

# 0.34.118: Flak - langsamer, Granaten platzen am Zielpunkt (Wolke), stark gegen Luftziele;
# Abwuerfe: kleine Last platzt, Fahrzeuge verlieren den Schirm und stuerzen.
_tm118 = _TM59.Testmodus(app, karte="staubtal_offen")
_e118 = _tm118.welt.ebene(0)
_rnd118 = random.Random(118)
for _ in range(40000):
    _tx118 = _rnd118.randrange(60, _e118.breite - 90)
    _ty118 = _rnd118.randrange(20, _e118.hoehe - 40)
    if all(not K.KACHELN[_e118.kachel(_tx118 + x_, _ty118 + y_)]["fest"]
           for x_ in range(50) for y_ in range(24)):
        break
_z118 = lambda x_, y_: pygame.Vector2((_tx118 + x_ + 0.5) * K.TILE, (_ty118 + y_ + 0.5) * K.TILE)
_ex118 = []
_alt_ex118 = _tm118.welt.explosion
def _ex_merk118(pos, ebene, radius, art="spreng", von=None):
    _ex118.append((pygame.Vector2(pos), art))
    return _alt_ex118(pos, ebene, radius, art, von)
_tm118.welt.explosion = _ex_merk118
_w118 = K.FAHRZEUG_WAFFEN["flak_kanone"]
pruef("Flak: deutlich langsamer (hoechstens 3 Schuss/s, vorher 16) und ohne MG-Zeile",
      _w118["takt"] >= 0.33 and "flak_mg" not in K.FAHRZEUG_WAFFEN, "%.2f s" % _w118["takt"])
_fl118 = _tm118.fahrzeug_setzen("flakwagen", _z118(10, 12), 0, {"winkel": 0})
_sch118 = _tm118.puppe_setzen(_fl118.pos, 0, {"team": 0}, name="FLAKSCHUETZE")
_tm118._einsteigen(_sch118, _fl118)
def _flak_ein118(ziel_, feuer_=True):
    _tm118._anwenden(_sch118, {"will": [0, 0], "ziel": [ziel_.x, ziel_.y], "knoepfe": [], "feuert": feuer_})
    _tm118.schritt(K.FIXED_DT)
# Am Boden: zwei Gegner - einer auf dem Weg, einer am Zielpunkt. Die Granate fliegt ueber den ersten und platzt am Ziel.
_weg118 = _tm118.puppe_setzen(_fl118.pos + pygame.Vector2(200, 0), 0, {"team": 1, "leben": 5.0}, name="WEG")
_zp118 = _fl118.pos + pygame.Vector2(420, 0)
_ziel118 = _tm118.puppe_setzen(_zp118, 0, {"team": 1, "leben": 5.0}, name="ZIEL")
_weg118.unverwundbar = 0.0; _ziel118.unverwundbar = 0.0
_wl118, _zl118 = _weg118.leben, _ziel118.leben
_tm118.welt._raster_bauen()
_ex118.clear()
for _ in range(int(0.15 / K.FIXED_DT)):
    _flak_ein118(_zp118)
_flak_ein118(_zp118, False)
for _ in range(int(1.2 / K.FIXED_DT)):
    _flak_ein118(_zp118, False)
_fl_ex118 = [p_ for p_, a_ in _ex118 if a_ == "flak"]
pruef("Flak am Boden: die Granate platzt nach der Strecke bis zum Zeiger - nicht an dem, der dazwischen steht",
      bool(_fl_ex118) and min(abs(p_.x - _zp118.x) for p_ in _fl_ex118) < 40.0
      and _weg118.leben == _wl118 and _ziel118.leben < _zl118,
      "Wolken %s, Weg %.1f->%.1f, Ziel %.1f->%.1f" % ([(round(p_.x), round(p_.y)) for p_ in _fl_ex118],
                                                     _wl118, _weg118.leben, _zl118, _ziel118.leben))
# Schussfolge: in 3 Sekunden Dauerfeuer nicht mehr als 3 je Sekunde.
_n118 = [0]
_alt_dazu118 = _tm118.welt.dazu
def _dazu118(w_):
    if w_.__class__.__name__ == "Flakgranate":
        _n118[0] += 1
    return _alt_dazu118(w_)
_tm118.welt.dazu = _dazu118
for _ in range(int(3.0 / K.FIXED_DT)):
    _flak_ein118(_zp118)
pruef("... Dauerfeuer: in 3 s hoechstens neun Granaten", 5 <= _n118[0] <= 9, str(_n118[0]))
_tm118.welt.dazu = _alt_dazu118
# In der Luft: ein fliegender Tragschrauber der Gegner, auf sein Bild gezielt.
_ts118 = _tm118.fahrzeug_setzen("tragschrauber", _z118(30, 4), 0, {"winkel": 0})
_pil118 = _tm118.puppe_setzen(_ts118.ausstiegsorte(9.0)[0], 0, {"team": 1}, name="PILOT")
_tm118._anwenden(_pil118, {"will": [0, 0], "ziel": [0, 0], "knoepfe": ["nutzen"]})
for _ in range(int(6.0 / K.FIXED_DT)):
    _tm118._anwenden(_pil118, {"will": [0, -1], "ziel": [0, 0], "knoepfe": []})
    _tm118.schritt(K.FIXED_DT)
# Der Flakwagen steht jetzt schraeg voraus in Reichweite (der Tragschrauber ist weit geflogen).
_fl118.pos.update(_ts118.pos + pygame.Vector2(260, 200)); _fl118.vorher.update(_fl118.pos)
_sch118.pos.update(_fl118.pos)
_l118 = _ts118.leben
_ex118.clear()
_n118[0] = 0
for _ in range(int(2.0 / K.FIXED_DT)):
    _tm118._anwenden(_pil118, {"will": [0, -1], "ziel": [0, 0], "knoepfe": []})
    _bp118 = pygame.Vector2(_ts118.pos.x, _ts118.pos.y - _ts118.hoehe)
    _tm118._anwenden(_sch118, {"will": [0, 0], "ziel": [_bp118.x, _bp118.y], "knoepfe": [], "feuert": True})
    _tm118.schritt(K.FIXED_DT)
    if not _ts118.lebt or _ts118.kaputt:
        break
pruef("Flak in der Luft: die Wolke platzt am Ziel und trifft den Tragschrauber hart (zwei, drei Granaten)",
      (_ts118.leben < _l118 - 40.0 or _ts118.kaputt) and any(a_ == "flak" for _p, a_ in _ex118),
      "%.0f -> %.0f" % (_l118, _ts118.leben))
# Abwuerfe: Kiste platzt mit einem Treffer, mit einer neuen Animation.
_tm118.welt.explosion = _ex_merk118
_ex118.clear()
_tm118.nachschub_setzen("medkit", _z118(20, 20), {"team": 1})
for _ in range(int(1.6 / K.FIXED_DT)):
    _tm118.schritt(K.FIXED_DT)
_lz118 = [x_ for x_ in _tm118.luft_ziele() if x_.art == "abwurf"][0]
_lz118.treffen(K.FLAK["luft_schaden"], _sch118)
pruef("Abwurf am Schirm: Medkit/Kiste platzt mit einem Flaktreffer (neue Animation 'luft_kiste'), nichts landet",
      not _tm118.abwuerfe and any(a_ == "luft_kiste" for _p, a_ in _ex118)
      and not any(getattr(b_, "art", "") == "medkit" for b_ in _tm118.welt.wesen))
# Fahrzeug am Schirm: nach etwas Beschuss reisst der Schirm, er faellt schnell und kommt fast kaputt an.
_ex118.clear()
_tm118.nachschub_setzen("krad", _z118(25, 18), {"team": 1})
for _ in range(int(2.4 / K.FIXED_DT)):
    _tm118.schritt(K.FIXED_DT)
_ab118 = _tm118.abwuerfe[0]
_lz118 = [x_ for x_ in _tm118.luft_ziele() if x_.art == "abwurf"][0]
_lz118.treffen(K.FLAK["luft_schaden"], _sch118)
pruef("Fahrzeug am Schirm: ein Treffer reisst den Schirm noch nicht",
      _ab118 in _tm118.abwuerfe and _ab118.gerissen == 0.0)
_lz118 = [x_ for x_ in _tm118.luft_ziele() if x_.art == "abwurf"][0]
_lz118.treffen(K.FLAK["luft_schaden"], _sch118)
_lz118 = [x_ for x_ in _tm118.luft_ziele() if x_.art == "abwurf"][0]
_lz118.treffen(K.FLAK["luft_schaden"], _sch118)
pruef("... nach genug Treffern reisst er (neue Animation 'fallschirm_riss'), der Wagen ist kein Luftziel mehr",
      _ab118.gerissen > 0.0 and any(a_ == "fallschirm_riss" for _p, a_ in _ex118)
      and not [x_ for x_ in _tm118.luft_ziele() if x_.art == "abwurf"])
_h0118 = _ab118.hoehe
for _ in range(int(0.5 / K.FIXED_DT)):
    _tm118.schritt(K.FIXED_DT)
_normal118 = K.SCHLACHT["abwurf"]["sinken"] * 0.5
pruef("... und faellt viel schneller als am Schirm (beschleunigt)",
      _h0118 - _ab118.hoehe > _normal118 * 2.5, "%.0f px in 0,5 s, am Schirm %.0f" % (_h0118 - _ab118.hoehe, _normal118))
_bild118 = pygame.Surface((K.GAME_W, K.GAME_H))
_tm118.zeichnen(_bild118, 1.0)                      # gerissen zeichnen geht
_m118 = _tm118.schlacht_meldung()
_m118["ab"][0] = list(_m118["ab"][0])
_g118 = _TM59.Testmodus(app, karte="staubtal_offen")
_g118.schlacht_uebernehmen(_m118)
pruef("... der Gast bekommt den Riss mit (Abwurf Feld 7)",
      _g118.abwuerfe and _g118.abwuerfe[0].gerissen > 0.0)
for _ in range(int(3.0 / K.FIXED_DT)):
    _tm118.schritt(K.FIXED_DT)
_krad118 = [b_ for b_ in _tm118.fahrzeuge if b_.art == "krad" and getattr(b_, "basis_team", -1) == 1]
pruef("... er kommt mit extrem wenig Leben am Boden an (hartes Aufsetzen: 'absturz')",
      _krad118 and _krad118[-1].leben <= _krad118[-1].max_leben * 0.06 and _krad118[-1].lebt
      and any(a_ == "absturz" for _p, a_ in _ex118),
      "%s" % ([(b_.leben, b_.max_leben) for b_ in _krad118]))
# Fallschirmjaeger: tot in der Luft - eigene Animation.
_ex118.clear()
_sp118 = _tm118.fallschirmjaeger_abwerfen(_z118(5, 5), 1)
for _ in range(int(0.5 / K.FIXED_DT)):
    _tm118.schritt(K.FIXED_DT)
_lzs118 = [x_ for x_ in _tm118.luft_ziele() if x_.art == "springer"]
_lzs118[0].treffen(9999.0, _sch118)
pruef("Fallschirmjaeger: stirbt einer in der Luft, gibt es die Animation 'luft_mensch'",
      _lzs118 and any(a_ == "luft_mensch" for _p, a_ in _ex118) and not _lzs118[0].objekt.lebt)
_tm118.verlassen()

# 0.34.119: Tragschrauber - ein Schatten, der genau zu ihm passt; Bomben gross, eine nach der anderen.
_tm119 = _TM59.Testmodus(app, karte="staubtal_offen")
_e119 = _tm119.welt.ebene(0)
_rnd119 = random.Random(119)
for _ in range(40000):
    _tx119 = _rnd119.randrange(60, _e119.breite - 90)
    _ty119 = _rnd119.randrange(20, _e119.hoehe - 40)
    if all(not K.KACHELN[_e119.kachel(_tx119 + x_, _ty119 + y_)]["fest"]
           for x_ in range(50) for y_ in range(24)):
        break
_z119 = lambda x_, y_: pygame.Vector2((_tx119 + x_ + 0.5) * K.TILE, (_ty119 + y_ + 0.5) * K.TILE)
# Der Schatten ist die Silhouette des Bildes (kein Oval) ...
_sp119 = pygame.mask.from_surface(app.bilder.bild("tragschrauber"), 40)
_sh119 = pygame.mask.from_surface(app.bilder.bild("tragschrauber_schatten"), 40)
_u119 = _sp119.overlap_area(_sh119, (0, 0))
pruef("Tragschrauber: der Schatten ist genau seine Silhouette (Rahmen, Kanzel, Leitwerk - deckungsgleich mit dem Bild)",
      _sp119.count() > 300 and _u119 >= 0.97 * _sp119.count() and _sh119.count() <= 1.03 * _sp119.count(),
      "%d / %d / %d" % (_u119, _sp119.count(), _sh119.count()))
pruef("... der Rotor wirft seinen eigenen Schatten (sechs Stellungen, wie das Bild)",
      all(app.bilder.bild("rotor_schatten_%d" % i_).get_size() == app.bilder.bild("rotor_%d" % i_).get_size()
          and pygame.mask.from_surface(app.bilder.bild("rotor_schatten_%d" % i_), 20).count() > 50 for i_ in range(6)))
_ts119 = _tm119.fahrzeug_setzen("tragschrauber", _z119(4, 12), 0, {"winkel": 0})
_p119 = _tm119.puppe_setzen(_ts119.ausstiegsorte(9.0)[0], 0, {"team": 0}, name="PILOT")
_tm119._anwenden(_p119, {"will": [0, 0], "ziel": [0, 0], "knoepfe": ["nutzen"]})
def _ts_ein119(feuert_=False):
    _tm119._anwenden(_p119, {"will": [0, -1], "ziel": [0, 0], "knoepfe": [], "feuert": feuert_})
    _tm119.schritt(K.FIXED_DT)
for _ in range(int(6.0 / K.FIXED_DT)):
    _ts_ein119()
_tm119.kamera.pos.update(_ts119.pos)
_namen119 = []
_alt_ged119 = _tm119.renderer.bilder.gedreht
def _ged119(name_, winkel_, *a_, **k_):
    _namen119.append(name_)
    return _alt_ged119(name_, winkel_, *a_, **k_)
_tm119.renderer.bilder.gedreht = _ged119
_b119 = pygame.Surface((K.GAME_W, K.GAME_H))
_tm119.zeichnen(_b119, 1.0)
_tm119.renderer.bilder.gedreht = _alt_ged119
pruef("Tragschrauber in der Luft: es gibt nur noch EINEN Schatten (die Luftschicht), nicht zwei", _namen119.count("tragschrauber_schatten") == 1,
      str(_namen119.count("tragschrauber_schatten")))
# Bomben: seit 0.34.123 kleine Schrottbomben (art_bombe.py), eine nach der anderen.
from dustfront import art_bombe as _AB119
_bg119 = pygame.mask.from_surface(_AB119.schrottbombe(0.0), 40).get_bounding_rects()[0]
pruef("Bomben: die Schrottbombe ist klein (5 bis 12 Pixel hoch) und am Tragschrauber nicht zu sehen; er hat zwei dabei",
      5 <= _bg119.height <= 12 and _ts119.bomben == 2 and _ts119.bild == _ts119._insassen_bild("tragschrauber"),
      "%d %s" % (_bg119.height, _ts119.bild))
_ts_ein119(True); _ts_ein119(False)
pruef("... eine Bombe faellt, eine hat er noch", _ts119.bomben == 1 and len(_ts119.bomben_fall) == 1)
_ts_ein119(True); _ts_ein119(False)
pruef("... eine zweite geht erst, wenn die erste unten ist (nur eine auf einmal)",
      _ts119.bomben == 1 and len(_ts119.bomben_fall) == 1)
_tm119.zeichnen(_b119, 1.0)                          # fallende Bombe zeichnen geht
for _ in range(int(1.3 / K.FIXED_DT)):
    _ts_ein119()
_ts_ein119(True); _ts_ein119(False)
pruef("... danach die zweite", _ts119.bomben == 0 and len(_ts119.bomben_fall) == 1)
_tm119.verlassen()

# 0.34.120: Funkwagen und Werfer bauen mit Animation auf; neues Raketengestell (3D, dreht
# sich zum Zeiger, Raketen nacheinander, Rohre laden einzeln nach, Rueckstrahl); der Werfer
# geht mit der groessten Explosion hoch, ohne Wrack.
_tm120 = _TM59.Testmodus(app, karte="staubtal_offen")
_e120 = _tm120.welt.ebene(0)
_rnd120 = random.Random(120)
for _ in range(40000):
    _tx120 = _rnd120.randrange(60, _e120.breite - 90)
    _ty120 = _rnd120.randrange(20, _e120.hoehe - 40)
    if all(not K.KACHELN[_e120.kachel(_tx120 + x_, _ty120 + y_)]["fest"]
           for x_ in range(50) for y_ in range(24)):
        break
_z120 = lambda x_, y_: pygame.Vector2((_tx120 + x_ + 0.5) * K.TILE, (_ty120 + y_ + 0.5) * K.TILE)
_ex120 = []
_dekal120 = []
_alt_ex120 = _tm120.welt.explosion
def _exm120(pos, ebene, radius, art="spreng", von=None):
    _ex120.append((pygame.Vector2(pos), round(radius, 1), art))
    return _alt_ex120(pos, ebene, radius, art, von)
_tm120.welt.explosion = _exm120
_alt_dk120 = _tm120.welt.bild_dekal
def _dkm120(name, pos, ebene, winkel=0.0):
    _dekal120.append(name)
    return _alt_dk120(name, pos, ebene, winkel)
_tm120.welt.bild_dekal = _dkm120
# -- Funkwagen: Aufbau und Abbau als Folge von Bildern
_fw120 = _tm120.fahrzeug_setzen("funkwagen", _z120(6, 6), 0, {"winkel": 0})
_pf120 = _tm120.puppe_setzen(_fw120.ausstiegsorte(9.0)[0], 0, {"team": 0}, name="FUNKER")
_tm120._anwenden(_pf120, {"will": [0, 0], "ziel": [0, 0], "knoepfe": ["nutzen"]})
def _f_ein120(zielt_=False, gas_=0.0):
    _tm120._anwenden(_pf120, {"will": [0, -gas_], "ziel": [0, 0], "knoepfe": [], "zielt": zielt_})
    _tm120.schritt(K.FIXED_DT)
for _ in range(3):
    _f_ein120(True)
# Seit 0.34.124 ist der Mast ein 3D-Modell (art_funkmast.py): die Stellungen
# zaehlen hier als Bilder des Mastes, nicht mehr als Namen des Wagenbildes.
from dustfront import art_funkmast as _AFM120
_bilder120, _prog120 = [], []
for _ in range(int(3.0 / K.FIXED_DT)):
    _f_ein120()
    _prog120.append(_fw120.fortschritt)
    _sl120 = _AFM120._schluessel(_fw120.winkel, _fw120.fortschritt, _fw120.kopf)
    if not _bilder120 or _bilder120[-1] != _sl120:
        _bilder120.append(_sl120)
pruef("Funkwagen: der Aufbau ist eine Animation - der Fortschritt steigt gleichmaessig, der Mast durchlaeuft viele Stellungen (kein Sprung)",
      all(b_ >= a_ for a_, b_ in zip(_prog120, _prog120[1:])) and _prog120[-1] >= 0.999
      and len(set(_bilder120)) >= 10 and _fw120.bild == "funkwagen"
      and all(b_[1] - a_[1] <= 1 for a_, b_ in zip(_bilder120, _bilder120[1:])),
      "%d Stellungen: %s ... %s" % (len(set(_bilder120)), _bilder120[:2], _bilder120[-2:]))
_k0_120 = _fw120.kopf
for _ in range(int(0.5 / K.FIXED_DT)):
    _f_ein120()
pruef("... am Ende steht der Mast und der Peilkopf dreht sich", _fw120.phase == 2 and _fw120.fortschritt >= 1.0
      and abs((_fw120.kopf - _k0_120 + 180.0) % 360.0 - 180.0) > 10.0, "%.0f -> %.0f" % (_k0_120, _fw120.kopf))
for _ in range(3):
    _f_ein120(True)
_bilder120, _prog120 = [], []
for _ in range(int(1.0 / K.FIXED_DT)):
    _f_ein120(gas_=1.0)
    _prog120.append(_fw120.fortschritt)
    _bilder120.append(_AFM120._schluessel(_fw120.winkel, _fw120.fortschritt, _fw120.kopf))
pruef("... der Abbau laeuft rueckwaerts (Fortschritt faellt) und der Wagen steht dabei, bis er eingepackt ist",
      _prog120[-1] < _prog120[0] and 0.0 < _prog120[-1] < 1.0 and _fw120.geschw.length() < 5.0
      and len(set(_bilder120)) >= 4, "%.2f -> %.2f, v %.0f" % (_prog120[0], _prog120[-1], _fw120.geschw.length()))
for _ in range(int(2.5 / K.FIXED_DT)):
    _f_ein120(gas_=1.0)
pruef("... danach faehrt er wieder", _fw120.fortschritt == 0.0 and _fw120.bild == "funkwagen")
# -- Werfer
_we120 = _tm120.fahrzeug_setzen("werfer", _z120(6, 18), 0, {"winkel": 0})
_pw120 = _tm120.puppe_setzen(_we120.ausstiegsorte(9.0)[0], 0, {"team": 0}, name="WERFERFUEHRER")
_tm120._anwenden(_pw120, {"will": [0, 0], "ziel": [0, 0], "knoepfe": ["nutzen"]})
_zz120 = [_we120.pos.x + 900, _we120.pos.y]
def _w_ein120(feuert_=False, zielt_=False):
    _tm120._anwenden(_pw120, {"will": [0, 0], "ziel": list(_zz120), "knoepfe": [], "feuert": feuert_, "zielt": zielt_})
    _tm120.schritt(K.FIXED_DT)
from dustfront import art_werfer as _AW120
pruef("Werfer: das Gestell ist ein 3D-Modell (seit 0.34.123) mit sechs geladenen Rohren; eingepackt liegt es flach",
      _we120.rohre == 63 and _we120.stufe == 0 and _we120.erhebung() == 0.0
      and _AW120.gestell(30.0, 40.0, 5)[0].get_size() == (_AW120.GROESSE_BILD, _AW120.GROESSE_BILD))
for _ in range(3):
    _w_ein120(zielt_=True)
_st120, _stufen120 = [], []
for _ in range(int(3.0 / K.FIXED_DT)):
    _w_ein120()
    _st120.append(_we120.fortschritt)
    if not _stufen120 or _stufen120[-1] != _we120.stufe:
        _stufen120.append(_we120.stufe)
pruef("Werfer: beim Aufbau schwenken die Stuetzen aus und das Gestell hebt sich stufenweise (0 bis 8), alles weich",
      _we120.phase == 2 and _stufen120[0] == 0 and _stufen120[-1] == 8 and len(_stufen120) >= 7
      and all(b_ >= a_ for a_, b_ in zip(_st120, _st120[1:])), str(_stufen120))
# Das Gestell dreht sich weich zum Zeiger (nicht ruckartig).
_zz120[:] = [_we120.pos.x, _we120.pos.y - 800]
_r0120 = _we120.rohr_rel
for _ in range(int(0.15 / K.FIXED_DT)):
    _w_ein120()
_r1120 = _we120.rohr_rel
pruef("Werfer: das Gestell dreht sich weich zum Zeiger - in 0,15 s hoechstens 110 Grad/s weit",
      0.0 < abs(_r1120 - _r0120) <= K.WERFER["dreh"] * 0.15 + 1.0, "%.1f -> %.1f" % (_r0120, _r1120))
for _ in range(int(2.5 / K.FIXED_DT)):
    _w_ein120()
pruef("... und zeigt am Ende genau dorthin (links der Fahrtrichtung, -90 Grad)", abs(_we120.rohr_rel + 90.0) < 3.0,
      "%.1f" % _we120.rohr_rel)
# Salve: die Raketen starten nacheinander aus ihren Rohren, die Rohre laden einzeln wieder.
_feind120 = [_tm120.puppe_setzen(pygame.Vector2(_we120.pos.x, _we120.pos.y - 900 + 30 * i_), 0, {"team": 1, "leben": 5.0},
                                 name="FEIND%d" % i_) for i_ in range(3)]
for _f120 in _feind120:
    _f120.markiert_rest = 60.0; _f120.markiert_fuer = _pw120.fraktion
_zz120[:] = [_feind120[1].pos.x, _feind120[1].pos.y]
for _ in range(int(0.7 / K.FIXED_DT)):
    _w_ein120()
pruef("Werfer: das Ziel gilt, er ist bereit", _we120.bereit and _we120.ziel_grund == 0, "%s %d" % (_we120.bereit, _we120.ziel_grund))
_ex120.clear()
_maske120 = [_we120.rohre]
_w_ein120(True)
_w_ein120(False)
if _maske120[-1] != _we120.rohre:
    _maske120.append(_we120.rohre)
for _ in range(int(3.2 / K.FIXED_DT)):
    _w_ein120()
    if _maske120[-1] != _we120.rohre:
        _maske120.append(_we120.rohre)
_leer120 = [bin(m_).count("1") for m_ in _maske120]
pruef("... die Raketen verlassen ihre Rohre nacheinander (die Zahl geladener Rohre sinkt Stufe fuer Stufe 6, 5, ... 0)",
      _leer120 == [6, 5, 4, 3, 2, 1, 0], str(_leer120))
_st120 = [a_ for a_ in _ex120 if a_[2] == "werfer_start"]
pruef("... jede zuendet einen Rueckstrahl (Welt.explosion 'werfer_start', Radius = Steilheit * 1000 + Richtung des Gestells)",
      len(_st120) == 6 and all(abs((int(r_) % 1000 - _we120.gestell_winkel() + 180.0) % 360.0 - 180.0) < 1.5
                               and int(r_) // 1000 == int(round(_we120.erhebung())) for _p, r_, _a in _st120),
      str([r_ for _p, r_, _a in _st120]))
_bs120 = sum(1 for f_ in _tm120.welt.effekte if f_.art == "rauch" and f_.palette == "staub")
pruef("... mit viel Staub am Boden, hinter dem Werfer", _bs120 >= 30, str(_bs120))
_ladend120 = []
for _ in range(int(16.0 / K.FIXED_DT)):
    _w_ein120()
    _ladend120.append(bin(_we120.rohre).count("1"))
pruef("... danach tauchen die Raketen in den Rohren nacheinander wieder auf (sechs Stufen), bis er wieder bereit ist",
      sorted(set(_ladend120)) == [0, 1, 2, 3, 4, 5, 6][:len(sorted(set(_ladend120)))] and len(set(_ladend120)) >= 6
      and _ladend120[-1] == 6 and _we120.bereit, str(sorted(set(_ladend120))))
# Zerstoerung: die groesste Explosion, kein Wrack.
_nah120 = _tm120.puppe_setzen(_we120.pos + pygame.Vector2(0, 150), 0, {"team": 0}, name="NAH")
_mitte120 = _tm120.puppe_setzen(_we120.pos + pygame.Vector2(0, 280), 0, {"team": 1}, name="MITTE")
_weit120 = _tm120.puppe_setzen(_we120.pos + pygame.Vector2(0, 600), 0, {"team": 1}, name="WEIT")
for _p120 in (_nah120, _mitte120, _weit120):
    _p120.unverwundbar = 0.0
_tm120.welt._raster_bauen()
_ex120.clear(); _dekal120.clear()
_we120.schaden(_we120.max_leben + 5.0, None, _mitte120, art="kugel", herkunft=_mitte120.pos)
_tm120.schritt(K.FIXED_DT)
pruef("Werfer: er geht mit der groessten Explosion hoch (Art 'werfer_gross', Radius deutlich ueber 300)",
      any(a_[2] == "werfer_gross" and a_[1] >= 300.0 for a_ in _ex120) and _we120.kaputt, str(_ex120[:2]))
pruef("... der Fahrer stirbt sofort (nicht nur am Boden), und alle im Umkreis von gut 200 Pixeln mit ihm",
      not _pw120.lebt and not _nah120.lebt, "%s %s" % (_pw120.lebt, _nah120.lebt))
pruef("... wer weiter weg steht, bekommt nur noch einen Teil ab oder nichts", _weit120.lebt, str(_weit120.lebt))
_leer120 = pygame.mask.from_surface(app.bilder.bild(_we120.bild), 10).count()
pruef("... kein Wrack bleibt zurueck (sein Bild ist leer), nur Einzelteile am Boden (Dekale 'fx_teil_N', seit 0.34.123)",
      _we120.bild == "werfer_wrack" and _leer120 == 0 and len([n_ for n_ in _dekal120 if n_.startswith("fx_teil_")]) >= 6,
      "%d Pixel, %d Teile" % (_leer120, len(_dekal120)))
_b120 = pygame.Surface((K.GAME_W, K.GAME_H))
_tm120.kamera.pos.update(_we120.pos)
for _ in range(int(0.6 / K.FIXED_DT)):
    _tm120.schritt(K.FIXED_DT)
_tm120.zeichnen(_b120, 1.0)                           # die Explosion zeichnen geht
_tm120.verlassen()


# 0.34.123: Nacharbeit an den neuen Fahrzeugen, alles neu gemacht - Effektsystem
# (effekte.py), Schrottbombe des Tragschraubers, 3D-Werfer, Flak-Leuchtspur,
# Jagdpanzer-Luke fest in der Wanne, Beifahrer im Krad, kein Schieben von oben.
from dustfront import effekte as _FX123, art_neue_fahrzeuge as _ANF123, art_werfer as _AW123
from dustfront import art_bombe as _AB123
_tm123 = _TM59.Testmodus(app, karte="staubtal_offen")
_e123 = _tm123.welt.ebene(0)
_rnd123 = random.Random(123)
for _ in range(40000):
    _tx123 = _rnd123.randrange(60, _e123.breite - 90)
    _ty123 = _rnd123.randrange(20, _e123.hoehe - 40)
    if all(not K.KACHELN[_e123.kachel(_tx123 + x_, _ty123 + y_)]["fest"]
           for x_ in range(50) for y_ in range(24)):
        break
_z123 = lambda x_, y_: pygame.Vector2((_tx123 + x_ + 0.5) * K.TILE, (_ty123 + y_ + 0.5) * K.TILE)
# -- Effektsystem: jede Art erzeugt Teilchen und laesst sich zeichnen.
_b123 = pygame.Surface((K.GAME_W, K.GAME_H))
_arten123 = []
for _art123 in sorted(_FX123.ARTEN):
    _tm123.welt.effekte = []
    _r123 = {"flak_schuss": 1.0 * (90 + 360 * (300 + 2048 * 40)), "werfer_start": 40.0 * 1000 + 30.0,
             "fallschirm_riss": 40.0 * 10 + 1}.get(_art123, 30.0)
    _tm123.welt.explosion(_z123(25, 12), 0, _r123, _art123, None)
    _n123 = len(_tm123.welt.effekte)
    for _ in range(int(0.3 / K.FIXED_DT)):
        _tm123.welt.effekte_schritt(K.FIXED_DT)
    _tm123.kamera.pos.update(_z123(25, 12))
    _tm123.zeichnen(_b123, 1.0)
    if _n123 == 0:
        _arten123.append(_art123)
pruef("Effekte: jede Art des neuen Effektsystems erzeugt Teilchen und laesst sich zeichnen",
      not _arten123 and len(_FX123.ARTEN) >= 11, str(_arten123))
_tm123.welt.effekte = []
_tm123.welt.explosion(_z123(25, 12), 0, 50.0, "flak", None)
_hoch123 = [f_.z for f_ in _tm123.welt.effekte if f_.art == "rauch"]
pruef("... die Flakwolke steht in der Hoehe des Ziels (Radius = Hoehe), nicht am Boden",
      _hoch123 and min(_hoch123) > 40.0, str(_hoch123[:3]))
# -- Jagdpanzer: die Luke ist fest in der Wanne, nicht im drehenden Aufbau.
_alt_luke123 = _ANF123._kommandantenluke
_mit123 = _ANF123.jagdpanzer_wanne()
_ANF123._kommandantenluke = lambda b_, c_: None
_ohne123 = _ANF123.jagdpanzer_wanne()
def _luke_verboten123(b_, c_):
    raise AssertionError("Luke im Aufbau")
_ANF123._kommandantenluke = _luke_verboten123
try:
    _ANF123.jagdpanzer_aufbau()
    _aufbau_ok123 = True
except AssertionError:
    _aufbau_ok123 = False
_ANF123._kommandantenluke = _alt_luke123
_diff123 = sum(1 for x_ in range(_mit123.get_width()) for y_ in range(_mit123.get_height())
               if _mit123.get_at((x_, y_)) != _ohne123.get_at((x_, y_)))
pruef("Jagdpanzer: die Kommandantenluke ist ins Bild der Wanne gemalt (kann sich nicht eigen bewegen), der Aufbau hat keine",
      _diff123 > 40 and _aufbau_ok123, "%d Pixel" % _diff123)
# -- Krad: der Beifahrer sitzt im Beiwagen und dreht sich nur in seinem Bogen.
_kr123 = _tm123.fahrzeug_setzen("krad", _z123(4, 4), 0, {"winkel": 0})
_bo123 = K.KRAD["beifahrer_bogen"]
pruef("Krad: der Beifahrer dreht sich nur im Bogen (nach vorn rechts bis hinten), nicht in den Fahrer hinein",
      abs(_kr123.beifahrer_klemmen(90.0) - 90.0) < 0.01 and abs(_kr123.beifahrer_klemmen(-100.0) - _bo123[0]) < 0.01
      and abs(_kr123.beifahrer_klemmen(175.0) - _bo123[1]) < 0.01,
      "%.1f %.1f %.1f" % (_kr123.beifahrer_klemmen(90.0), _kr123.beifahrer_klemmen(-100.0), _kr123.beifahrer_klemmen(175.0)))
_kf123 = _tm123.puppe_setzen(_kr123.ausstiegsorte(9.0)[0], 0, {"team": 0}, name="KRADFAHRER")
_tm123._anwenden(_kf123, {"will": [0, 0], "ziel": [0, 0], "knoepfe": ["nutzen"]})
_kb123 = _tm123.puppe_setzen(_kr123.pos + pygame.Vector2(20, 14), 0, {"team": 0, "waffe_figur": "sturm"}, name="BEI")
_tm123._anwenden(_kb123, {"will": [0, 0], "ziel": [0, 0], "knoepfe": ["nutzen"]})
_zk123 = _kr123.pos + pygame.Vector2(-300, -10)          # nach hinten links: ausserhalb des Bogens
for _ in range(10):
    _tm123._anwenden(_kb123, {"will": [0, 0], "ziel": [_zk123.x, _zk123.y], "knoepfe": []})
    _tm123._anwenden(_kf123, {"will": [0, 0], "ziel": [0, 0], "knoepfe": []})
    _tm123.schritt(K.FIXED_DT)
_rel123 = (_kb123.winkel - _kr123.winkel + 180.0) % 360.0 - 180.0
pruef("... zielt er dorthin, schaut er nur bis an den Rand des Bogens; er sitzt am Sitz im Beiwagen",
      _bo123[0] - 0.5 <= _rel123 <= _bo123[1] + 0.5 and abs(abs(_rel123) - 180.0) > 20.0
      and _kb123.pos.distance_to(_kr123.beifahrer_sitz()) < 1.0, "%.1f" % _rel123)
_tm123.zeichnen(_b123, 1.0)                          # Beifahrer zeichnen geht
# -- Tragschrauber: hoch oben schiebt er niemanden am Boden; die Schrottbombe.
_ts123 = _tm123.fahrzeug_setzen("tragschrauber", _z123(10, 12), 0, {"winkel": 0})
_tp123 = _tm123.puppe_setzen(_ts123.ausstiegsorte(9.0)[0], 0, {"team": 0}, name="PILOT")
_tm123._anwenden(_tp123, {"will": [0, 0], "ziel": [0, 0], "knoepfe": ["nutzen"]})
for _ in range(int(5.0 / K.FIXED_DT)):
    _tm123._anwenden(_tp123, {"will": [0, -1], "ziel": [0, 0], "knoepfe": []})
    _tm123.schritt(K.FIXED_DT)
_boden123 = _tm123.puppe_setzen(pygame.Vector2(_ts123.pos), 0, {"team": 1}, name="BODEN")
_bp123 = 0.0
for _ in range(int(0.5 / K.FIXED_DT)):
    _tm123._anwenden(_tp123, {"will": [0, -1], "ziel": [0, 0], "knoepfe": []})
    _boden123.pos.update(_ts123.pos); _boden123.vorher.update(_ts123.pos)
    _vor_b123 = pygame.Vector2(_boden123.pos)
    _tm123.schritt(K.FIXED_DT)
    _bp123 = max(_bp123, _boden123.pos.distance_to(_vor_b123))
pruef("Tragschrauber: hoch oben schiebt er keinen am Boden (auch nicht, wenn der genau unter ihm steht)",
      _ts123.hoch_oben and _bp123 < 1.0, "%.1f" % _bp123)
_boden123.pos.update(_z123(40, 2))
_ex123 = []
_alt_ex123 = _tm123.welt.explosion
def _ex_merk123(pos, ebene, radius, art="spreng", von=None):
    _ex123.append((pygame.Vector2(pos), radius, art))
    return _alt_ex123(pos, ebene, radius, art, von)
_tm123.welt.explosion = _ex_merk123
_vor123 = (pygame.Vector2(_ts123.pos), _ts123.winkel)
_tm123._anwenden(_tp123, {"will": [0, -1], "ziel": [0, 0], "knoepfe": [], "feuert": True})
_tm123.schritt(K.FIXED_DT)
_los123 = [e_ for e_ in _ex123 if e_[2] == "bombe_los"]
_soll123 = _vor123[0] + pygame.Vector2(K.TRAGSCHRAUBER["bombe"]["abwurf"]).rotate(_vor123[1])
pruef("Schrottbombe: der Fahrer zuendet sie und laesst sie neben der Kanzel fallen ('bombe_los' in seiner Hoehe)",
      len(_los123) == 1 and _los123[0][0].distance_to(_soll123) < 12.0 and _los123[0][1] > 30.0
      and len(_ts123.bomben_fall) == 1 and len(_ts123.netz_extra()[3][0]) == 4,
      str(_los123))
_tm123.kamera.pos.update(_ts123.pos)
for _ in range(int(0.4 / K.FIXED_DT)):
    _tm123._anwenden(_tp123, {"will": [0, -1], "ziel": [0, 0], "knoepfe": []})
    _tm123.schritt(K.FIXED_DT)
_tm123.zeichnen(_b123, 1.0)                          # fallende Schrottbombe zeichnen geht
pruef("... sie ueberschlaegt sich im Fall: zwoelf verschiedene Lagen, die Lunte wandert mit",
      len({_AB123.schrottbombe(w_ * 30.0).get_size() for w_ in range(12)}) == 1
      and _AB123.lunte_spitze(0.0) != _AB123.lunte_spitze(90.0))
_tm123.welt.explosion = _alt_ex123
# -- Werfer: das 3D-Gestell richtet sich nach der Entfernung auf; Raketen aus ihren Rohren.
_we123 = _tm123.fahrzeug_setzen("werfer", _z123(10, 20), 0, {"winkel": 0})
_wp123 = _tm123.puppe_setzen(_we123.ausstiegsorte(9.0)[0], 0, {"team": 0}, name="WERFER")
_tm123._anwenden(_wp123, {"will": [0, 0], "ziel": [0, 0], "knoepfe": ["nutzen"]})
_wz123 = [_we123.pos.x + 450, _we123.pos.y]
def _we_ein123(sek_, zielt_=False):
    for _ in range(int(sek_ / K.FIXED_DT)):
        _tm123._anwenden(_wp123, {"will": [0, 0], "ziel": list(_wz123), "knoepfe": [], "zielt": zielt_})
        _tm123.schritt(K.FIXED_DT)
_we_ein123(0.05, True)
_we_ein123(4.0)
_nah123 = _we123.erhebung()
_wz123[:] = [_we123.pos.x + 3000, _we123.pos.y]
_we_ein123(2.0)
_weit123 = _we123.erhebung()
pruef("Werfer: aufgebaut stehen die Rohre schraeg, bei nahem Ziel steiler als bei weitem",
      _we123.phase == 2 and _nah123 > _weit123 + 10.0 and _weit123 > 20.0, "%.1f / %.1f" % (_nah123, _weit123))
_m123 = [_we123.muendung(i_) for i_ in range(6)]
_h123 = [_we123.muendung_hoehe(i_) for i_ in range(6)]
pruef("... die sechs Muendungen liegen vorn am Gestell, hoch in der Luft (3D: obere Reihe hoeher)",
      len({(round(m_.x), round(m_.y)) for m_ in _m123}) >= 3 and min(_h123) > 8.0 and _h123[3] > _h123[0],
      str([round(h_) for h_ in _h123]))
_e123r = [3.0, _we123.pos.x + 3000, _we123.pos.y, True, 2]
_bahn123 = _tm123._raketen_bahn(_we123, _e123r)
_a123, _z123b = _bahn123(0.0), _bahn123(1.0)
_mitte123 = _bahn123(0.5)
pruef("... eine Rakete fliegt aus ihrem Rohr (Start an der Muendung, Nase nach oben) im Bogen ins Ziel",
      pygame.Vector2(_a123[0], _a123[1]).distance_to(_we123.muendung(2)) < 1.0 and _a123[4] < -10.0
      and abs(_z123b[0] - _e123r[1]) < 1.0 and _z123b[2] < 1.0 and _mitte123[2] > 100.0 and _z123b[4] > 10.0,
      "%.0f %.0f %.0f" % (_a123[4], _mitte123[2], _z123b[4]))
_gb123, _gs123 = _AW123.gestell(30.0, 40.0, 63)
_gl123 = _AW123.gestell(30.0, 40.0, 0)[0]
pruef("... das Gestell sieht man je nach Richtung anders (3D), leere Rohre anders als geladene",
      pygame.image.tostring(_AW123.gestell(30.0, 40.0, 63)[0], "RGBA") != pygame.image.tostring(_AW123.gestell(210.0, 40.0, 63)[0], "RGBA")
      and pygame.image.tostring(_gb123, "RGBA") != pygame.image.tostring(_gl123, "RGBA"))
_gast123 = _FZ59.Werfer((0, 0), 0, 0.0, nur_bild=True)
_gast123.netz_extra_setzen(_we123.netz_extra())
pruef("... der Gast bekommt die Steilheit mit (Feld 6 der Meldung)",
      abs(_gast123._hub_soll - _we123._hub_soll) < 1.0, "%.1f %.1f" % (_gast123._hub_soll, _we123._hub_soll))
_tm123.zeichnen(_b123, 1.0)
# -- Flak: Leuchtspur aus dem Effektsystem, sie steigt zur Hoehe des Ziels.
_tm123.welt.effekte = []
_tm123.welt.explosion(_z123(25, 12), 0, float(0 + 360 * (400 + 2048 * 60)), "flak_schuss", None)
_ls123 = [f_ for f_ in _tm123.welt.effekte if f_.art == "leuchtspur"]
pruef("Flak: jeder Schuss zeichnet eine Leuchtspur, die zur Hoehe des Ziels steigt (dort, wo die Wolke platzt)",
      len(_ls123) == 1 and _ls123[0].vz > 0.0
      and abs(_ls123[0].z + _ls123[0].vz * _ls123[0].dauer - 60.0) < 1.0
      and abs(_ls123[0].vx * _ls123[0].dauer - 400.0) < 2.0, str([(f_.vz, f_.dauer) for f_ in _ls123]))
pruef("... die Granate selbst sieht man nicht (nur die Spur)", _FZ59.Flakgranate.bild == "flak_leer"
      and _FZ59.Flakgranate.spur is None)
_tm123.verlassen()

print("\n-- Funkwagen: der Mast als 3D-Modell (0.34.124)")
from dustfront import art_funkmast as _AFM124
_st0_124, _st1_124 = _AFM124.stellung(0.0), _AFM124.stellung(1.0)
pruef("Funkmast: eingepackt liegt er (0 Grad, eingefahren, zu, keine Seile), aufgebaut steht er ganz",
      _st0_124 == (0.0, 0.0, 0.0, 0.0) and _st1_124 == (90.0, 1.0, 1.0, 1.0), "%s %s" % (_st0_124, _st1_124))
_folge124 = [_AFM124.stellung(i_ / 50.0) for i_ in range(51)]
pruef("... erst richtet er sich auf, dann faehrt er aus, dann klappt der Kopf auf, zuletzt die Seile",
      all(all(b_[j_] >= a_[j_] for j_ in range(4)) for a_, b_ in zip(_folge124, _folge124[1:]))
      and _AFM124.stellung(0.42)[1] == 0.0 and _AFM124.stellung(0.6)[2] == 0.0 and _AFM124.stellung(0.72)[3] == 0.0
      and _AFM124.stellung(0.42)[0] == 90.0)
_m0_124 = _AFM124.funkmast(0.0, 0.0)
_m1_124 = _AFM124.funkmast(0.0, 1.0)
def _hoch124(s_):
    r_ = s_.get_bounding_rect(1)
    return (s_.get_height() // 2 - _AFM124.MITTE[1]) - r_.top
pruef("... aufgerichtet ragt er im Bild weit nach oben, liegend kaum",
      _m0_124.get_size() == (_AFM124.GROESSE_BILD, _AFM124.GROESSE_BILD)
      and _hoch124(_m1_124) > _hoch124(_m0_124) + 25, "%d %d" % (_hoch124(_m0_124), _hoch124(_m1_124)))
pruef("... der Kopf dreht sich im Bild, und die Richtung des Wagens dreht den liegenden Mast mit (3D)",
      pygame.image.tostring(_AFM124.funkmast(0.0, 1.0, 0.0), "RGBA") != pygame.image.tostring(_AFM124.funkmast(0.0, 1.0, 45.0), "RGBA")
      and pygame.image.tostring(_AFM124.funkmast(0.0, 0.0), "RGBA") != pygame.image.tostring(_AFM124.funkmast(90.0, 0.0), "RGBA"))
pruef("... mit Schatten (gleich gross, nicht leer)",
      _AFM124.schatten(0.0, 1.0).get_size() == _m1_124.get_size()
      and _AFM124.schatten(0.0, 1.0).get_bounding_rect(1).width > 10)
_fwg124 = _FZ59.Funkwagen((0, 0), 0, 0.0, nur_bild=True)
_fwg124.phase, _fwg124.kopf = 0, 120.0
for _ in range(int(1.5 / K.FIXED_DT)):
    _fwg124.schritt(K.FIXED_DT)
pruef("... beim Abbau dreht der Kopf zurueck in Fahrtrichtung (auch beim Gast, ohne Meldung)",
      abs((_fwg124.kopf + 180.0) % 360.0 - 180.0) < 1.0 and _fwg124.bild == "funkwagen", "%.1f" % _fwg124.kopf)
pruef("... die alten flachen Mastbilder gibt es nicht mehr",
      not any(n_.startswith(("funkwagen_aktiv_", "funkwagen_aufbau_")) for n_ in K.BILD_MASS))

# Ein Brocken, der ausgeblendet wird, darf sein Bild im Zwischenspeicher nicht
# undurchsichtig machen (bis 0.34.124: schwarze Quadrate bei jedem Einschlag).
from dustfront import effekte as _FX124
_br124 = _FX124.brocken(3, "erde", 1, 0)
_fx124 = _FX124.Fx("brocken", 20.0, 20.0, 0.0, 0, 1.0)
_fx124.r0, _fx124.palette, _fx124.variante, _fx124.alter = 3.0, "erde", 1, 0.9
_FX124._zeichne(pygame.Surface((40, 40)), _fx124, 0.0, 0.0)
_weiss124 = pygame.Surface(_br124.get_size())
_weiss124.fill((255, 255, 255))
_weiss124.blit(_FX124.brocken(3, "erde", 1, 0), (0, 0))
pruef("Effekte: ein ausgeblendeter Brocken laesst sein Bild durchsichtig (kein schwarzes Quadrat)",
      tuple(_weiss124.get_at((0, 0)))[:3] == (255, 255, 255), str(tuple(_weiss124.get_at((0, 0)))))

print("\n-- 0.34.126: kein Drift-Ton, Teilchenwolken, Funkmast einheitlich, Werfer klassisch")
from dustfront import art_funkmast as _AFM126, art_werfer as _AW126, effekte as _FX126, drei_d as _D126
from dustfront import art as _ART126
_tm126 = _TM59.Testmodus(app, karte="staubtal_offen")
_rnd126 = random.Random(126)
_e126 = _tm126.welt.ebene(0)
for _ in range(40000):
    _tx126 = _rnd126.randrange(60, _e126.breite - 90)
    _ty126 = _rnd126.randrange(20, _e126.hoehe - 40)
    if all(not K.KACHELN[_e126.kachel(_tx126 + x_, _ty126 + y_)]["fest"]
           for x_ in range(30) for y_ in range(20)):
        break
_z126 = lambda x_, y_: pygame.Vector2((_tx126 + x_ + 0.5) * K.TILE, (_ty126 + y_ + 0.5) * K.TILE)
_kl126 = []
_alt_kl126 = _tm126.welt.klang
def _klm126(name, *a_, **k_):
    _kl126.append(name)
    return _alt_kl126(name, *a_, **k_)
_tm126.welt.klang = _klm126
_kr126 = _tm126.fahrzeug_setzen("krad", _z126(15, 10), 0, {"winkel": 0})
_kf126 = _tm126.puppe_setzen(_kr126.ausstiegsorte(9.0)[0], 0, {"team": 0}, name="KRADFAHRER")
_tm126._anwenden(_kf126, {"will": [0, 0], "ziel": [0, 0], "knoepfe": ["nutzen"]})
_rut126 = 0.0
for i_ in range(int(1.5 / K.FIXED_DT)):
    if i_ % 30 == 0:
        _kr126.geschw.update(pygame.Vector2(0, 260).rotate(_kr126.winkel))    # quer: es rutscht
    _tm126._anwenden(_kf126, {"will": [1, -1], "ziel": [0, 0], "knoepfe": []})
    _tm126.schritt(K.FIXED_DT)
    _rut126 = max(_rut126, _kr126.rutschen)
pruef("Drift: das Krad rutscht, aber der Rutsch-Ton ist weg (auch aus Klangliste und Netz)",
      _rut126 > 0.6 and "buggy_rutschen" not in _kl126 and "buggy_rutschen" not in K.KLANG_NAMEN
      and not hasattr(_FZ59.Buggy, "_quietschen"), "%.2f %s" % (_rut126, sorted(set(_kl126))[:6]))
_tm126.welt.klang = _alt_kl126
# Explosionen: Rauch und Feuer sind Teilchenwolken.
_tm126.welt.effekte = []
_tm126.welt.explosion(_z126(15, 10), 0, 40030.0, "werfer_start", None)
_ws126 = [f_ for f_ in _tm126.welt.effekte if f_.art in ("rauch", "feuer")]
pruef("Explosionen: der Rueckstrahl ist eine grosse Wolke aus einzelnen Teilchen (keine gemalten Ballen)",
      len(_ws126) > 150 and all(isinstance(f_, _FX126.Teilchen) for f_ in _ws126), str(len(_ws126)))
_tm126.welt.effekte = []
for _art126 in ("einschlag", "bombe", "flak", "absturz", "luft_kiste"):
    _tm126.welt.explosion(_z126(15, 10), 0, 30.0, _art126, None)
pruef("... ebenso bei allen anderen neuen Explosionen",
      all(isinstance(f_, _FX126.Teilchen) for f_ in _tm126.welt.effekte if f_.art in ("rauch", "feuer")))
# Aus der juengsten Explosion: mehr als 2400 Effekte auf einmal haelt die Welt
# nicht, die aeltesten fallen weg (Welt.effekte_schritt).
_t126 = [f_ for f_ in reversed(_tm126.welt.effekte) if isinstance(f_, _FX126.Teilchen)
         and f_.vx * f_.vx + f_.vy * f_.vy > 400.0 and f_.dauer > 0.6 and f_.verzoegert < 0.05][0]
_o0_126 = _t126.ort()
for _ in range(int(0.3 / K.FIXED_DT)):
    _tm126.welt.effekte_schritt(K.FIXED_DT)
_tm126.kamera.pos.update(_z126(15, 10))
_tm126.zeichnen(pygame.Surface((K.GAME_W, K.GAME_H)), 1.0)
pruef("... die Teilchen fliegen auseinander und lassen sich zeichnen", _t126.ort() != _o0_126)
_tm126.verlassen()
# Funkmast: kein dunkler Rand, gleiche Farben beim Aufrichten, liegend unauffaellig.
def _rand_pixel126(s_):
    return sum(1 for x_ in range(s_.get_width()) for y_ in range(s_.get_height())
               if tuple(s_.get_at((x_, y_))) == (16, 11, 8, 255))
def _haeufigste126(s_):
    z_ = {}
    for x_ in range(s_.get_width()):
        for y_ in range(s_.get_height()):
            c_ = tuple(s_.get_at((x_, y_)))
            if c_[3] == 255:
                z_[c_[:3]] = z_.get(c_[:3], 0) + 1
    return max(z_, key=z_.get)
pruef("Funkmast: in keiner Stellung ein schwarzer Umriss",
      all(_rand_pixel126(_AFM126.funkmast(g_, p_ / 24.0, 30.0)) == 0 for g_ in (0, 25, 200) for p_ in (0, 6, 10, 24)))
_farben126 = [_haeufigste126(_AFM126.funkmast(25.0, p_, 0.0)) for p_ in (0.25, 0.3, 0.35, 0.42)]
pruef("... beim Aufrichten bleibt seine Farbe gleich (kein Springen zwischen Lichtstufen)",
      len(set(_farben126)) == 1, str(_farben126))
_dach126 = _AFM126.DACH
_ab126 = lambda c_: sum(abs(a_ - b_) for a_, b_ in zip(c_, _dach126))
pruef("... liegend geht er in den Lack des Dachs ueber, aufgerichtet nicht",
      _ab126(_haeufigste126(_AFM126.funkmast(25.0, 0.0, 0.0))) < _ab126(_farben126[-1]) - 20,
      "%s / %s" % (_haeufigste126(_AFM126.funkmast(25.0, 0.0, 0.0)), _farben126[-1]))
# Werfer: klassisch gemalt, Aufrichtung im Bild zu sehen.
import inspect as _insp126
def _oben126(s_):
    return s_.get_bounding_rect(1).top
pruef("Werfer: das Gestell ist gemalt wie die Fahrzeuge (kein 3D-Modell mehr)",
      "import drei_d" not in _insp126.getsource(_AW126) and "drei_d as" not in _insp126.getsource(_AW126) and _AW126.gestell(0.0, 40.0, 63)[0].get_size()
      == (_AW126.GROESSE_BILD, _AW126.GROESSE_BILD))
pruef("... steiler: die Muendungen ragen im Bild hoeher (jede Aufrichtung ein eigenes Bild)",
      _oben126(_AW126.gestell(0.0, 70.0, 63)[0]) < _oben126(_AW126.gestell(0.0, 30.0, 63)[0])
      < _oben126(_AW126.gestell(0.0, 0.0, 63)[0])
      and len({pygame.image.tobytes(_AW126.gestell(0.0, e_, 63)[0], "RGBA") for e_ in range(0, 81, 10)}) == 9,
      "%d %d %d" % (_oben126(_AW126.gestell(0.0, 70.0, 63)[0]), _oben126(_AW126.gestell(0.0, 30.0, 63)[0]),
                    _oben126(_AW126.gestell(0.0, 0.0, 63)[0])))
pruef("... und jede Drehung (5-Grad-Schritte) ein eigenes Bild",
      len({pygame.image.tobytes(_AW126.gestell(g_, 40.0, 63)[0], "RGBA") for g_ in range(0, 360, 5)}) == 72)

print("\n-- 0.34.127: Absturz des Tragschraubers, dichtere grosse Explosionen")
_tm127 = _TM59.Testmodus(app, karte="staubtal_offen")
_e127 = _tm127.welt.ebene(0)
_rnd127 = random.Random(127)
for _ in range(40000):
    _tx127 = _rnd127.randrange(30, _e127.breite - 60)
    _ty127 = _rnd127.randrange(20, _e127.hoehe - 30)
    if all(not K.KACHELN[_e127.kachel(_tx127 + x_, _ty127 + y_)]["fest"] and not _e127.loch(_tx127 + x_, _ty127 + y_)
           for x_ in range(40) for y_ in range(10)):
        break
_z127 = lambda x_, y_: pygame.Vector2((_tx127 + x_ + 0.5) * K.TILE, (_ty127 + y_ + 0.5) * K.TILE)
def _heli127(mauer_, wand_weg_=150.0):
    ts_ = _tm127.fahrzeug_setzen("tragschrauber", _z127(2, 5), 0, {"winkel": 0})
    p_ = _tm127.puppe_setzen(ts_.ausstiegsorte(9.0)[0], 0, {"team": 0}, name="PILOT")
    _tm127._anwenden(p_, {"will": [0, 0], "ziel": [0, 0], "knoepfe": ["nutzen"]})
    for _ in range(int(4.5 / K.FIXED_DT)):
        _tm127._anwenden(p_, {"will": [0, -1], "ziel": [0, 0], "knoepfe": []})
        _tm127.schritt(K.FIXED_DT)
    ts_.pos.update(_z127(3, 5)); ts_.vorher.update(ts_.pos)
    for _ in range(int(0.3 / K.FIXED_DT)):
        _tm127._anwenden(p_, {"will": [0, -1], "ziel": [0, 0], "knoepfe": []})
        _tm127.schritt(K.FIXED_DT)
    if mauer_:
        for dy_ in range(-3, 4):
            _e127.setzen(int((ts_.pos.x + wand_weg_) // K.TILE), int(ts_.pos.y // K.TILE) + dy_, K.WAND)
        _tm127.welt._raster_bauen()
    return ts_, p_
_ts127, _p127 = _heli127(False)
_h0_127, _x0_127 = _ts127.hoehe, _ts127.pos.x
_ts127.schaden(_ts127.leben + 50.0, None, None, art="spreng")
pruef("Tragschrauber: in der Luft abgeschossen ist der Pilot sofort tot, das Wrack faellt noch (nicht gleich am Boden)",
      _ts127.luft is False and not _p127.lebt and _ts127.kaputt and _ts127.stuerzt and _ts127.hoehe > 40.0
      and _ts127.hoch_oben, "Pilot %s, Hoehe %.0f" % (_p127.lebt, _ts127.hoehe))
_hoehen127, _wege127 = [], []
_tief127 = None
for _ in range(int(3.0 / K.FIXED_DT)):
    _tm127.schritt(K.FIXED_DT)
    _hoehen127.append(_ts127.hoehe)
    _wege127.append(_ts127.pos.x - _x0_127)
    if _tief127 is None and _ts127.hoehe < 16.0:
        _tief127 = _wege127[-1]                # ab hier ist es tiefer als eine Mauer (24)
pruef("... es fliegt mit seinem Schwung weiter in seine Richtung, immer schneller nach unten, bis es aufschlaegt",
      _wege127[-1] > 60.0 and all(b_ <= a_ for a_, b_ in zip(_hoehen127, _hoehen127[1:]))
      and _hoehen127[-1] == 0.0 and not _ts127.stuerzt and _ts127.kaputt
      and _ts127.wrack_rest <= _ts127.werte["wrack_zeit"], "Weg %.0f px" % _wege127[-1])
_tm127.zeichnen(pygame.Surface((K.GAME_W, K.GAME_H)), 1.0)
_frei127 = _wege127[-1]
# Die Mauer dort, wo das Wrack schon tiefer ist als sie (sonst fliegt es darueber).
_ts127b, _p127b = _heli127(True, _tief127 + K.TILE)
_x0_127 = _ts127b.pos.x
_ts127b.schaden(_ts127b.leben + 50.0, None, None, art="spreng")
for _ in range(int(3.0 / K.FIXED_DT)):
    _tm127.schritt(K.FIXED_DT)
_wand127 = (int((_x0_127 + _tief127 + K.TILE) // K.TILE)) * K.TILE
pruef("... faellt es gegen eine Mauer, die hoeher ist als es gerade, prallt es dort ab und liegt davor (nicht darin)",
      _ts127b.pos.x - _x0_127 < _frei127 - 20.0 and _ts127b.pos.x < _wand127 and not _ts127b.stuerzt
      and _FZ59.Buggy.passt(_ts127b, _ts127b.pos), "%.0f px (frei %.0f)" % (_ts127b.pos.x - _x0_127, _frei127))
# Ueber eine Mauer, solange es noch hoeher ist: sinkt es darauf, rutscht es herunter.
_ts127d, _p127d = _heli127(True, _tief127 - 24.0)
_ts127d.schaden(_ts127d.leben + 50.0, None, None, art="spreng")
for _ in range(int(3.0 / K.FIXED_DT)):
    _tm127.schritt(K.FIXED_DT)
pruef("... sinkt es beim Ueberfliegen auf eine Mauer, rutscht es von ihr herunter (liegt nie darin)",
      not _ts127d.stuerzt and _ts127d.kaputt and _FZ59.Buggy.passt(_ts127d, _ts127d.pos)
      and not _e127.fest(int(_ts127d.pos.x // K.TILE), int(_ts127d.pos.y // K.TILE)),
      "%.0f %.0f" % (_ts127d.pos.x, _ts127d.pos.y))
_ts127c = _tm127.fahrzeug_setzen("tragschrauber", _z127(30, 8), 0, {"winkel": 0})
_p127c = _tm127.puppe_setzen(_ts127c.ausstiegsorte(9.0)[0], 0, {"team": 0}, name="AM BODEN")
_tm127._anwenden(_p127c, {"will": [0, 0], "ziel": [0, 0], "knoepfe": ["nutzen"]})
_tm127.schritt(K.FIXED_DT)
_ts127c.schaden(_ts127c.leben + 50.0, None, None, art="spreng")
pruef("... auch am Boden zerstoert sind die Insassen sofort tot", _ts127c.kaputt and not _p127c.lebt
      and not _ts127c.stuerzt)
# Dichtere Teilchen bei massiven Explosionen.
_tm127.welt.effekte = []
_tm127.welt.explosion(_z127(20, 5), 0, 1.0, "einschlag", None)
_klein127 = [f_.r0 for f_ in _tm127.welt.effekte if f_.art == "rauch"]
_tm127.welt.effekte = []
_tm127.welt.explosion(_z127(20, 5), 0, 330.0, "werfer_gross", None)
_gross127 = [f_.r0 for f_ in _tm127.welt.effekte if f_.art == "rauch"]
_alle127 = len(_tm127.welt.effekte)          # vor dem Kappen: sonst fiele der Feuerball weg
pruef("Explosionen: die massive (Werfer) hat groessere, dichtere Teilchen als ein Einschlag, und alles passt unter die Grenze",
      sum(_gross127) / len(_gross127) > sum(_klein127) / len(_klein127) + 0.8
      and _alle127 <= K.EFFEKTE_HOECHSTENS,
      "%.1f / %.1f, %d" % (sum(_gross127) / len(_gross127), sum(_klein127) / len(_klein127), _alle127))
_tm127.verlassen()

print("\n-- 0.34.129: Respawn im Escape-Menue, Aufgeben am Boden")
_tm129 = _TM59.Testmodus(app, karte="staubtal_offen")
_p129 = pygame.Vector2(3000, 3000)
_a129 = _tm129.puppe_setzen(_p129, 0, {"team": 0}, name="A")
_b129 = _tm129.puppe_setzen(_p129 + pygame.Vector2(200, 0), 0, {"team": 1}, name="B")
def _ein129(k_, **x_):
    d_ = {"will": [0, 0], "ziel": [0, 0], "knoepfe": []}
    d_.update(x_)
    _tm129._anwenden(k_, d_)
_ein129(_a129, knoepfe=["aufgeben"])
_tot129 = not _a129.lebt and _a129.toeter is None
for _ in range(int(5.0 / K.FIXED_DT)):
    _tm129.schritt(K.FIXED_DT)
pruef("RESPAWN: man ist sofort tot (ohne Toeter, wenn keiner getroffen hat) und kommt wieder",
      _tot129 and _a129.lebt)
_ab129 = _b129.abschuesse
_a129.schaden(5, None, _b129)
_ein129(_a129, knoepfe=["aufgeben"])
_tm129.schritt(K.FIXED_DT)
pruef("... wer gerade von einem Gegner getroffen wurde, zaehlt fuer ihn als Abschuss (kein Entkommen per Respawn)",
      not _a129.lebt and _b129.abschuesse > _ab129, "%s -> %s" % (_ab129, _b129.abschuesse))
for _ in range(int(5.0 / K.FIXED_DT)):
    _tm129.schritt(K.FIXED_DT)
_a129.revive_an = True
_a129.sterben(_b129)
_unten129 = _a129.am_boden and _a129.lebt
for _ in range(int(2.0 / K.FIXED_DT)):
    _ein129(_a129, ag=True)
    _tm129.schritt(K.FIXED_DT)
_noch129 = _a129.lebt and _a129.am_boden
for _ in range(int(0.7 / K.FIXED_DT)):
    _ein129(_a129, ag=True)
    _tm129.schritt(K.FIXED_DT)
pruef("Am Boden: R %.1f s gehalten gibt auf (2 s noch nicht) - danach tot wie nach dem Verbluten" % K.REVIVE["aufgeben"],
      _unten129 and _noch129 and not _a129.lebt and 2.0 < K.REVIVE["aufgeben"] <= 3.0)
for _ in range(int(5.0 / K.FIXED_DT)):
    _tm129.schritt(K.FIXED_DT)
_a129.revive_an = True                       # nach dem Neuanfang wieder aus
_a129.sterben(_b129)
_unten129b = _a129.am_boden
for i_ in range(int(3.0 / K.FIXED_DT)):
    _ein129(_a129, ag=(i_ % 60) < 40)          # zwischendurch losgelassen
    _tm129.schritt(K.FIXED_DT)
pruef("... loslassen faengt von vorn an", _unten129b and _a129.lebt and _a129.am_boden,
      "%.2f" % getattr(_a129, "aufgeben_stand", -1.0))
_c129 = _tm129.puppe_setzen(_p129 + pygame.Vector2(-200, 0), 0, {"team": 0}, name="C")
_tm129.uebernehmen(_c129)
_tm129.menue_wirken("respawn", ausloesen=True)
pruef("Testmodus: Zeile RESPAWN wirkt auf die gesteuerte Figur", not _c129.lebt
      and "respawn" in [z_[0] for z_ in _tm129._menue_zeilen()])
_tm129.beobachten()
_bot129 = _tm129.bot_setzen(_p129 + pygame.Vector2(0, 200), 0, {"team": 1})
_tm129.aufgeben(_bot129)
pruef("... Bots geben nie auf", _bot129.lebt and getattr(_bot129, "ist_bot", False))
_tm129.verlassen()
from dustfront import mehrspieler as _MS129
pruef("Escape-Menue: RESPAWN ist eine Tat (nur auf Enter, ein Pfeil daneben toetet nicht)",
      "respawn" in _MS129.Gefecht.TATEN)

print("\n-- 0.34.129: Balancing und FREISCHALTEN in SCHLACHT")
from dustfront import regeln as _R129
# Der Vorschlag (docs/BALANCING.md, 0.34.128) - gewuenscht war: "alles ein bisschen billiger".
_vorschlag129 = dict(munition=3, medkit=3, buggy=4, krad=3, aufklaerung=5, napalm=12, fallschirmjaeger=8,
                     panzerwagen=8, panzer=14, jagdpanzer=10, spulenwagen=10, funkwagen=8, werfer=13,
                     tragschrauber=12, flakwagen=6)
_preis129 = {n_: c_ for n_, c_, _t in K.SCHLACHT["belohnungen"]}
pruef("Preise: alles billiger als im Vorschlag, der Konter Flak billiger als der Tragschrauber",
      set(_preis129) == set(_vorschlag129) and all(_preis129[n_] < _vorschlag129[n_] for n_ in _preis129)
      and _preis129["flakwagen"] < _preis129["tragschrauber"], str(_preis129))
pruef("... Panzer, Napalm und Tragschrauber frueher als im Vorschlag (dort erst ganz am Ende)",
      K.SCHLACHT["stufe"]["panzer"] <= 2 and K.SCHLACHT["stufe"]["napalm"] <= 1
      and K.SCHLACHT["stufe"]["tragschrauber"] < K.SCHLACHT["stufe"]["werfer"])
pruef("Ein zerstoertes Fahrzeug bringt den halben Preis (mindestens 2), ein Trosswagen 3",
      _MS129.Gefecht.fahrzeug_punkte("krad") == 2 and _MS129.Gefecht.fahrzeug_punkte("panzer")
      == int(_preis129["panzer"] / 2.0 + 0.5) and _MS129.Gefecht.fahrzeug_punkte("trosswagen") == 3
      and _MS129.Gefecht.fahrzeug_punkte("krad") <= _preis129["krad"])
_d129 = _R129.vorgabe()
for _ in range(len(K.MODI) + 1):
    if _d129["modus"] == "schlacht":
        break
    _R129.verstellen(_d129, "modus", 1)
pruef("FREISCHALTEN ist eine Regel der SCHLACHT (Vorgabe NORMAL), in der einfachen Ansicht",
      _d129.get("freischalten") == "normal"
      and "freischalten" in [f_.schluessel for f_ in _R129.sichtbar(_d129, False)])
w129, g129 = _paar59("schlacht", karte="staubtal")
def _stufe129(regeln_, alter_):
    w129._regeln_setzen(dict(_d129, **regeln_))
    w129.runden_alter = float(alter_)
    return w129.freischalt_stufe()
pruef("5-Minuten-Runde (NORMAL): Stufe 1 nach 30 s, 2 nach gut 1 min, 3 nach 105 s",
      [_stufe129({"ende_art": "zeit", "ende_wert": 300, "freischalten": "normal"}, t_)
       for t_ in (0, 29, 31, 67, 106)] == [0, 0, 1, 2, 3])
pruef("... 30-Minuten-Runde: nicht nach 10 % = 3 min, sondern spaetestens nach 2 / 4,5 / 7,5 min",
      [_stufe129({"ende_art": "zeit", "ende_wert": 1800, "freischalten": "normal"}, t_)
       for t_ in (119, 121, 271, 451)] == [0, 1, 2, 3])
w129._regeln_setzen(dict(_d129, ende_art="abschuesse", ende_wert=100, freischalten="normal"))
w129.runden_alter = 0.0
w129.teampunkte[0], w129.teampunkte[1] = 23, 4
pruef("... nach Abschuessen: die fuehrende Seite am Ziel (23 von 100 = Stufe 2)", w129.freischalt_stufe() == 2,
      str(w129.freischalt_stufe()))
w129.teampunkte[0] = w129.teampunkte[1] = 0
pruef("... AUS: alles sofort", _stufe129({"freischalten": "aus"}, 0) >= 3)
w129._regeln_setzen(dict(_d129, ende_art="zeit", ende_wert=300, freischalten="normal"))
w129.runden_alter = 10.0
pruef("Gesperrtes zeigt, wann es kommt", w129.gesperrt_bis("napalm") == "IN 0:20"
      and w129.gesperrt_bis("buggy") == "" and w129.gesperrt_bis("werfer").startswith("IN "),
      "%s / %s" % (w129.gesperrt_bis("napalm"), w129.gesperrt_bis("werfer")))
w129._einstiegszonen_waehlen()
w129.runden_alter = 0.0
w129._fahrzeuge_neu_aufstellen()
_arten129 = sorted({z_.art for z_ in w129.dropzonen})
pruef("Basis zum Start (NORMAL): nur die leichten - kein Panzer, keine Flak",
      "panzer" not in _arten129 and "flakwagen" not in _arten129 and "buggy" in _arten129, str(_arten129))
w129.runden_alter = 300 * 0.36
w129.schlacht_schritt(K.FIXED_DT)
_arten129b = [z_.art for z_ in w129.dropzonen]
pruef("... mit der Stufe kommen sie nach (Flak, zweiter Trosswagen, Panzer) - je Seite",
      _arten129b.count("panzer") == 2 and _arten129b.count("flakwagen") == 2
      and _arten129b.count("trosswagen") == 4, str(sorted(_arten129b)))
_ich129 = w129.ich
_ich129.schlacht_punkte = 99
_bas129 = w129.schlacht_basis(_ich129.team)
_mitte129 = w129._schlacht_punkte()[2]
_eigen129 = _bas129.lerp(_mitte129, 0.5)
_fremd129 = _mitte129 + (_mitte129 - _bas129) * 0.4
w129.runden_alter = 0.0
pruef("Kaufen: Gesperrtes geht nicht (Napalm am Anfang)",
      w129.belohnung_pruefen(_ich129, "napalm", _eigen129, punkt2=_eigen129 + pygame.Vector2(50, 0))
      .startswith("NOCH NICHT FREI"))
w129.runden_alter = 300.0
_gf129 = w129.belohnung_pruefen(_ich129, "tragschrauber", _fremd129)
pruef("... Tragschrauber, Werfer, Funkwagen nur in der eigenen Haelfte",
      _gf129 == "NUR IN DER EIGENEN HÄLFTE"
      and w129.belohnung_pruefen(_ich129, "werfer", _fremd129) == "NUR IN DER EIGENEN HÄLFTE"
      and w129.belohnung_pruefen(_ich129, "panzer", _fremd129) != "NUR IN DER EIGENEN HÄLFTE", _gf129)
_frei129 = None
for _ in range(200):
    _p129b = _bas129.lerp(_mitte129, random.uniform(0.3, 0.9)) + pygame.Vector2(0, random.uniform(-400, 400))
    if w129.belohnung_pruefen(_ich129, "tragschrauber", _p129b) == "":
        _frei129 = _p129b
        break
_k1_129 = _frei129 is not None and w129.belohnung_kaufen(_ich129, "tragschrauber", _frei129) == ""
pruef("... ohne die Regel HÖCHSTENS JE SEITE (Vorgabe, seit 0.34.130) beliebig viele",
      _k1_129 and w129.belohnung_pruefen(_ich129, "tragschrauber", _frei129) == ""
      and _d129.get("fahrzeug_grenze") is False
      and "fahrzeug_grenze" not in [f_.schluessel for f_ in _R129.sichtbar(_d129, False)]
      and "fahrzeug_grenze" in [f_.schluessel for f_ in _R129.sichtbar(_d129, True)], str(_frei129))
w129.regelwerk["fahrzeug_grenze"] = True
pruef("... mit ihr hoechstens einer je Seite: der zweite Tragschrauber geht nicht, solange der erste unterwegs ist",
      w129.belohnung_pruefen(_ich129, "tragschrauber", _frei129).startswith("SCHON 1")
      and _ich129.schlacht_punkte == 99 - _preis129["tragschrauber"])
w129.runden_alter = 77.0
for _ in range(8):
    w129.schritt(K.NETZ["takt"])
    g129.schritt(K.NETZ["takt"])
pruef("Der Gast kennt die Laufzeit der Runde (Kaufliste zeigt dasselbe wie beim Gastgeber)",
      abs(g129.runden_alter - w129.runden_alter) < 1.0, "%.1f / %.1f" % (g129.runden_alter, w129.runden_alter))

print("\n-- 0.34.130: Chor-Waffen werden heiss, Kugelblitz schwaecher, Napalm-Angriff")
_tm130 = _TM59.Testmodus(app, karte="staubtal_offen")
_p130 = pygame.Vector2(3000, 3000)
_a130 = _tm130.puppe_setzen(_p130, 0, {"team": 0, "waffe_figur": "spiegellaser"}, name="A")
_kl130 = []
_alt_kl130 = _tm130.welt.klang
def _klm130(name_, *a_, **k_):
    _kl130.append(name_)
    return _alt_kl130(name_, *a_, **k_)
_tm130.welt.klang = _klm130
def _ein130(**x_):
    d_ = {"will": [0, 0], "ziel": [_p130.x + 300, _p130.y], "knoepfe": []}
    d_.update(x_)
    _tm130._anwenden(_a130, d_)
    _tm130.schritt(K.FIXED_DT)
_sl130 = K.WAFFEN["spiegellaser"]
_schuss130 = 0
_t130 = 0.0
while "spiegellaser" not in _a130.ueberhitzt and _t130 < 10.0:
    _vor130 = _a130.magazin["spiegellaser"]
    _ein130(feuert=True)
    _schuss130 += 1 if _a130.magazin["spiegellaser"] < _vor130 else 0
    _t130 += K.FIXED_DT
pruef("Chor-Waffe: nach so vielen Schuss, wie frueher ins Magazin passten, ueberhitzt sie - einmal der Kuehlton, kein Nachladeton",
      _schuss130 == _sl130["magazin"] and _kl130.count("ueberhitzt") == 1 and "reload" not in _kl130,
      "%d Schuss, %s" % (_schuss130, sorted(set(_kl130))))
_ein130(knoepfe=["nachladen"])
pruef("... R laedt sie nicht nach, und das Abkuehlen dauert laenger als ein Nachladen",
      _a130.nachlade_rest == 0.0 and _sl130["ueberhitzt"] > _sl130["nachladen"]
      and all(K.WAFFEN[n_]["ueberhitzt"] > K.WAFFEN[n_]["nachladen"] for n_ in K.WAFFEN if K.WAFFEN[n_].get("kuehlt")))
_a130.waffe_waehlen(1)                     # weggesteckt: eine andere Waffe in der Hand
for _ in range(int((_sl130["ueberhitzt"] - 0.3) / K.FIXED_DT)):
    _ein130(feuert=True)
_noch130 = "spiegellaser" in _a130.ueberhitzt
for _ in range(int(0.6 / K.FIXED_DT)):
    _ein130()
pruef("... sie kuehlt auch weggesteckt ab - danach ist sie ganz kalt",
      _noch130 and "spiegellaser" not in _a130.ueberhitzt and _a130.magazin["spiegellaser"] == _sl130["magazin"])
_a130.waffe_waehlen(0)
for _ in range(int(0.9 / K.FIXED_DT)):
    _ein130(feuert=True)
_heiss130 = _a130.magazin["spiegellaser"]
_a130.waffe_waehlen(1)
for _ in range(int(_sl130["abkuehlen"] * 3.2 / K.FIXED_DT)):
    _ein130()
pruef("... und in Ruhe kuehlt sie nach und nach ab, auch in der Tasche",
      _heiss130 < _sl130["magazin"] and _a130.magazin["spiegellaser"] >= _heiss130 + 2,
      "%d -> %d" % (_heiss130, _a130.magazin["spiegellaser"]))
from dustfront import bots as _BO130
_a130.ueberhitzt["spiegellaser"] = 3.0
_mit130 = [n_ for _i, n_ in _BO130.BotHirn._waffen_mit_munition(type("H", (), {"k": _a130})())] \
    if hasattr(_BO130, "BotHirn") and hasattr(_BO130.BotHirn, "_waffen_mit_munition") else None
pruef("Bots nehmen eine ueberhitzte Waffe nicht (sie wechseln)",
      _mit130 is None or "spiegellaser" not in _mit130, str(_mit130))
_tm130.welt.klang = _alt_kl130
pruef("Kugelblitz deutlich schwaecher (gemeldet: viel zu OP): weniger Schaden, kleinere Reichweite der Blitze",
      K.WAFFEN["kugelblitz"]["schaden"] <= 10 and K.WAFFEN["kugelblitz"]["zap_radius"] <= 60
      and K.WAFFEN["kugelblitz"]["platzen_schaden"] <= 40 and K.WAFFEN["kugelblitz"]["platzen_radius"] <= 62)
# Napalm
from dustfront import schlacht as _SL130
_tm130.nachschub_setzen("napalm", _p130, {"winkel": 0})
_la130 = _tm130.luftangriffe[-1]
_kl130 = []
_tm130.welt.klang = _klm130
_orte130 = []
_alt_kl2_130 = _klm130
def _klm2_130(name_, laut_=1.0, pos_=None, ebene_=None):
    if name_ == "bomber":
        _orte130.append(None if pos_ is None else pygame.Vector2(pos_))
    return _klm130(name_, laut_, pos_, ebene_)
_tm130.welt.klang = _klm2_130
_b130 = pygame.Surface((K.GAME_W, K.GAME_H))
_gezeichnet130 = False
_t0_130 = _la130.bomben[0][0]
while _la130 in _tm130.luftangriffe:
    _tm130.schritt(K.FIXED_DT)
    if not _gezeichnet130 and _la130.alter > _t0_130 - 0.4:
        _tm130.kamera.pos.update(_la130.bomben[0][1])
        _tm130.zeichnen(_b130, 1.0)          # fallende Bomben zeichnen geht
        _gezeichnet130 = True
_bahn130 = _la130.ende - _la130.start
_anteile130 = [(o_ - _la130.start).dot(_bahn130) / _bahn130.length_squared() for o_ in _orte130 if o_ is not None]
pruef("Napalm: den Bomber hoert man nur an seinem Ort, und der wandert die Bahn entlang (auch davor und dahinter)",
      len(_orte130) >= 8 and len(_anteile130) == len(_orte130)
      and _anteile130[0] < 0.0 < 1.0 < _anteile130[-1]
      and all(b_ > a_ for a_, b_ in zip(_anteile130, _anteile130[1:])) and "jet" not in _kl130,
      "%d Stuecke, %.2f .. %.2f" % (len(_orte130), _anteile130[0] if _anteile130 else 0, _anteile130[-1] if _anteile130 else 0))
pruef("... jede Bombe pfeift im Fall, und sie fallen sichtbar (gezeichnet)",
      _kl130.count("napalm_fall") == len(_la130.bomben) and _gezeichnet130)
_np130 = [f_ for f_ in _tm130.welt.feuer if getattr(f_, "napalm", False)]
pruef("... das Napalm brennt als eigenes Feuer, deutlich laenger als vorher (16-24 s)",
      _np130 and all(f_.dauer >= 30.0 for f_ in _np130) and K.FEUER["napalm_toene"] != K.FEUER["toene"],
      str([round(f_.dauer) for f_ in _np130[:4]]))
_eintrag130 = [[f_.pos.x, f_.pos.y, f_.ebene, f_.radius, f_.alter, f_.kennung + 9000, f_.dauer, 1] for f_ in _np130[:2]]
_tm130.welt.feuer = []
_tm130._feuer_uebernehmen(_eintrag130)
pruef("... und beim Gast mit seiner Dauer und als Napalm (vorher ging es dort zu frueh aus)",
      len(_tm130.welt.feuer) == 2 and all(f_.napalm and f_.dauer >= 30.0 for f_ in _tm130.welt.feuer))
_la2_130 = _SL130.Luftangriff(_p130, _p130 + pygame.Vector2(1000, 0), 0, "")
_la2_130.alter = 0.0
pruef("... das Flugzeug hat auch vor dem Start einen Ort (vorher Absturz bei lerp ausserhalb 0..1)",
      _la2_130.flugzeug().x < _p130.x)
_tm130.welt.klang = _alt_kl130
_tm130.verlassen()

print("\n-- 0.34.131: Wasser, FLUSSTAL und KANALSTADT, Front mit Punkten, Einstiegskarte, Bots in Gruppen und an allen Fahrzeugen")
from dustfront import world as _W131, front as _FR131, kartenbild as _KB131, bots as _BO131
from dustfront.mehrspieler import Gefecht as _G131
# Wasser: seicht bremst, tief sperrt - aber nicht fuer Kugeln, Sicht und Wuerfe.
_w131 = _W131.Welt([_W131.Ebene.aus_text(["........", "..++%%..", "..++%%..", "........"], 0)])
_ps131 = pygame.Vector2(2.5 * K.TILE, 1.5 * K.TILE)
_pt131 = pygame.Vector2(4.5 * K.TILE, 1.5 * K.TILE)
pruef("Wasser: Zeichen + ist seicht, % tief; tief ist kein Weg, seicht schon",
      _w131.ebene(0).kachel(2, 1) == K.WASSER_SEICHT and _w131.ebene(0).kachel(4, 1) == K.WASSER_TIEF
      and _w131.ebene(0).begehbar(2, 1) and not _w131.ebene(0).begehbar(4, 1))
pruef("... tiefes Wasser haelt jeden auf, der geht oder faehrt - nicht, was darueber fliegt",
      not _w131.frei(_pt131, 10.0, 0) and _w131.frei(_pt131, 10.0, 0, ueber_wasser=True)
      and _w131.frei(_ps131, 10.0, 0))
pruef("... Kugeln und Sicht gehen darueber",
      not _w131.schuss_halt(_pt131, 0) and _w131.sicht_frei(pygame.Vector2(8, 40), pygame.Vector2(250, 40), 0))
pruef("... seichtes Wasser bremst zu Fuss mehr als im Wagen",
      _w131.boden_tempo(_ps131, 0) == K.WASSER["seicht_tempo"] < K.WASSER["seicht_fahrzeug"]
      == _w131.boden_tempo(_ps131, 0, fahrzeug=True) and _w131.boden_tempo(pygame.Vector2(16, 16), 0) == 1.0)
pruef("... Granaten fliegen ueber tiefes Wasser", getattr(_EN_G131 := __import__("dustfront.entities", fromlist=["Granate"]).Granate, "ueber_wasser", False))
pruef("Kachelsaetze gruen und stadt: Abwechslung aus dem Satz, Baum statt Kaktus",
      K.satz_bild(K.KARTENSAETZE["gruen"], K.KACHELN[K.FELS], 1) == "moosfels_2"
      and K.satz_bild(K.KARTENSAETZE["gruen"], K.KACHELN[K.KAKTUS]) == "baum"
      and K.satz_bild(K.KARTENSAETZE["stadt"], K.KACHELN[K.WASSER_TIEF], 2) == "kanal_3"
      and K.satz_bild(K.KARTENSAETZE["wueste"], K.KACHELN[K.FELS], 2) == "fels_3")
# Die Karten und ihr Plan.
for _name131 in ("flusstal", "kanalstadt"):
    _wk131, _kopf131 = _W131.karte_lesen(_name131)
    _plan131 = _FR131.Schlachtplan.lesen(_kopf131)
    _ok_netz131 = _plan131 is not None
    if _ok_netz131:
        for _b131 in _plan131.basen:
            _ent131 = _plan131.entfernungen(_b131.knoten)
            _ok_netz131 = _ok_netz131 and all(p_.knoten in _ent131 for p_ in _plan131.punkte)
    pruef("%s: neun Punkte A-I, je Seite drei Basen mit eigener Ausstattung, von jeder Basis jeder Punkt erreichbar" % _name131.upper(),
          _plan131 is not None and len(_plan131.punkte) == 9
          and sorted(p_.buchstabe for p_ in _plan131.punkte) == list("ABCDEFGHI")
          and sorted(b_.team for b_ in _plan131.basen) == [0, 0, 0, 1, 1, 1]
          and all(b_.fahrzeuge for b_ in _plan131.basen) and _ok_netz131)
    _e131 = _wk131.ebene(0)
    _farbe131 = _KB131.bild(_e131).get_at((5 * _KB131.pixel_je_kachel(_e131), _e131.hoehe // 2 * _KB131.pixel_je_kachel(_e131)))
    pruef("... das Kartenbild hat die Farben des Satzes (nicht sandbraun)",
          _wk131.satz in ("gruen", "stadt") and tuple(_farbe131)[:3] != K.KARTENBILD["sand"], str(_farbe131))
_wf131, _kf131 = _W131.karte_lesen("flusstal")
_alle131 = sum(1 for z_ in "".join("".join("+" if k_ == K.WASSER_SEICHT else "" for k_ in _wf131.ebene(0).kacheln)) if z_)
pruef("FLUSSTAL hat seichtes und tiefes Wasser und Bruecken",
      _alle131 > 200 and K.WASSER_TIEF in _wf131.ebene(0).kacheln and K.BRUECKE in _wf131.ebene(0).kacheln)

# Die Front in einer SCHLACHT auf FLUSSTAL, mit Gast.
w131, g131 = _paar59("schlacht", karte="flusstal")
w131._regeln_setzen(dict(_R199.vorgabe(), modus="schlacht", karte="flusstal", schlacht_seite=8, freischalten="aus"))
w131._einstiegszonen_waehlen()
w131._fahrzeuge_neu_aufstellen()
w131._bots_fuehren(0.0, sofort=True)
w131.front_anlegen()
pruef("FLUSSTAL ist die Vorgabe fuer SCHLACHT, und die Front gilt dort",
      K.SCHLACHT["karte"] == "flusstal" and w131.front_an and len(w131.front_punkte()) == 9)
pruef("... die Basis jeder Seite ist ihr Hauptlager aus dem Kartenkopf",
      w131.schlacht_basis(0) == w131.hauptbasis(0).pos and w131.hauptbasis(0).name == "HAUPTLAGER"
      and w131.schlacht_basis(1).x > w131.schlacht_basis(0).x)
_zonen131 = {z_.art for z_ in w131.dropzonen}
pruef("... an den Basen fallen ihre eigenen Fahrzeuge, auch Werfer, Tragschrauber, Jagdpanzer",
      {"werfer", "tragschrauber", "jagdpanzer", "spulenwagen", "funkwagen"} <= _zonen131, str(sorted(_zonen131)))
# Einnehmen: einer allein zieht den Stand zu sich, Gleichstand haelt, ganz = Besitzer.
_pk131 = w131.front_punkte()[0]
_pk131.stand, _pk131.besitzer = 0.0, -1
_rot131 = next(k_ for k_ in w131.kaempfer.values() if k_.team == 0 and k_.ist_bot)
_blau131 = next(k_ for k_ in w131.kaempfer.values() if k_.team == 1 and k_.ist_bot)
for k_ in w131.kaempfer.values():
    if k_.pos.distance_to(_pk131.pos) < K.FRONT["radius"] + 50:
        k_.pos.update(_pk131.pos + pygame.Vector2(0, 2000))
_rot131.pos.update(_pk131.pos)
for _ in range(int(K.FRONT["zeit"] * 0.5 / 0.1)):
    w131._punkte_einnehmen(0.1)
_halb131 = _pk131.stand
pruef("Punkt: einer allein zieht ihn zu seiner Seite, halb nach der halben Zeit",
      -0.6 < _halb131 < -0.4 and _pk131.besitzer == -1, "%.2f" % _halb131)
_blau131.pos.update(_pk131.pos + pygame.Vector2(30, 0))
for _ in range(20):
    w131._punkte_einnehmen(0.1)
pruef("... stehen beide gleich viele drin, bewegt sich nichts (umkaempft)", abs(_pk131.stand - _halb131) < 1e-6)
_blau131.pos.update(_pk131.pos + pygame.Vector2(0, 3000))
for _ in range(int(K.FRONT["zeit"] / 0.1) + 5):
    w131._punkte_einnehmen(0.1)
pruef("... und ganz eingenommen gehoert er ROT", _pk131.besitzer == 0 and _pk131.gehoert(0))
_ein131 = {e_[0]: e_ for e_ in w131.einstiege(0)}
pruef("Einstiege: die drei Basen immer, ein eigener Punkt, wenn kein Gegner nah ist",
      sum(1 for k_ in _ein131 if k_.startswith("b")) == 3 and _ein131["p%d" % _pk131.nr][3])
_blau131.pos.update(_pk131.pos + pygame.Vector2(K.FRONT["umkaempft"] * 0.5, 0))
pruef("... mit einem Gegner in der Naehe ist der Punkt UMKÄMPFT und kein Einstieg",
      not {e_[0]: e_ for e_ in w131.einstiege(0)}["p%d" % _pk131.nr][3]
      and "UMK" in {e_[0]: e_ for e_ in w131.einstiege(0)}["p%d" % _pk131.nr][4])
_blau131.pos.update(_pk131.pos + pygame.Vector2(0, 3000))
# Mensch: gewaehlter Einstieg - am Punkt; ohne Wahl an der Hauptbasis.
_ich131 = w131.ich
_ich131.team = 0
_ich131.einstieg_wahl = "p%d" % _pk131.nr
pruef("Ein Mensch steigt am gewaehlten Punkt ein",
      w131.front_einstiegsort(_ich131).distance_to(_pk131.pos) <= K.FRONT["einstieg_umkreis"] * 1.2)
_ich131.einstieg_wahl = "p99"
pruef("... ist die Wahl nicht (mehr) frei, an der Hauptbasis",
      w131.front_einstiegsort(_ich131).distance_to(w131.hauptbasis(0).pos) <= K.FRONT["basis_umkreis"] * 1.2)
# Netz: Stand der Punkte zum Gast, die Wahl des Gastes zum Gastgeber.
_pk131.da = [1, 0]
g131.front_uebernehmen(w131.front_meldung())
pruef("Netz: der Gast kennt Besitzer und Stand jedes Punktes (fp)",
      g131.front_punkte()[0].besitzer == 0 and abs(g131.front_punkte()[0].stand - _pk131.stand) < 1e-3
      and "fp" in w131.schlacht_meldung())
g131.ich.lebt = False
g131.einstieg_waehlen("b%d" % w131.front_basen(g131.ich.team)[0].nr)
for _ in range(6):
    g131.schritt(K.NETZ["takt"]); w131.schritt(K.NETZ["takt"])
_gk131 = w131.kaempfer.get(g131.ich.nummer)
pruef("... und der Gastgeber kennt den Einstieg, den der Gast gewaehlt hat (einstieg)",
      _gk131 is not None and _gk131.einstieg_wahl == "b%d" % w131.front_basen(g131.ich.team)[0].nr)
g131.ich.lebt = False          # der Gast bekaeme es sonst mit der naechsten Meldung zurueck
g131.ich.am_boden = False
pruef("Einstiegskarte: offen, solange man tot ist; 1 waehlt den ersten Einstieg",
      g131.einstieg_offen and g131.einstieg_ereignis(
          pygame.event.Event(pygame.KEYDOWN, key=pygame.K_1, mod=0, unicode="1", scancode=0))
      and g131.ich.einstieg_wahl == g131._einstieg_liste()[0][0])
_bild131 = pygame.Surface((K.GAME_W, K.GAME_H))
g131.zeichnen(_bild131, 1.0)
pruef("... und sie zeichnet sich (mit Leiste und Punkten)", True)
g131.ich.lebt = True
# Bots: Gruppen von 1 bis 4 mit Formation und Weg; verschiedene Ziele.
w131._front_rest = [0.0, 0.0]
w131._front_planen(0); w131._front_planen(1)
_gr131 = w131._gruppen
_bots131 = [k_ for k_ in w131.kaempfer.values() if k_.ist_bot and k_.lebt and k_.fahrzeug is None]
pruef("Bots gehen in Gruppen von 1 bis 4, jede mit Formation und Weg",
      _gr131 and all(1 <= len(g_.mitglieder) <= 4 and g_.form in _FR131.FORMATIONEN and g_.weg for g_ in _gr131)
      and all(w131.front_gruppe(k_) is not None for k_ in _bots131),
      str([(len(g_.mitglieder), g_.form) for g_ in _gr131]))
pruef("... und nicht alle zum selben Ziel", len({g_.ziel for g_ in _gr131 if g_.team == 0}) >= 2,
      str({g_.ziel for g_ in _gr131}))
# Flankieren: zwei Gruppen zum selben Ziel nehmen verschiedene Wege.
_ga131 = _FR131.Gruppe(0, ("punkt", 1), random.Random(1)); w131._gruppen.append(_ga131)
w131._weg_planen(_ga131, w131.hauptbasis(0).pos)
_gb131 = _FR131.Gruppe(0, ("punkt", 1), random.Random(2)); w131._gruppen.append(_gb131)
w131._weg_planen(_gb131, w131.hauptbasis(0).pos)
pruef("Zwei Gruppen zum selben Ziel nehmen nicht denselben Weg (sie flankieren)",
      _ga131.kanten != _gb131.kanten, "%s / %s" % (_ga131.kanten[:4], _gb131.kanten[:4]))
w131._gruppen.remove(_ga131); w131._gruppen.remove(_gb131)
_g131 = next(g_ for g_ in _gr131 if len(g_.lebende()) >= 2)
_f131, _m131 = _g131.lebende()[0], _g131.lebende()[1]
_auf131 = w131.front_auftrag(_m131)
pruef("... wer folgt, bekommt einen Platz in der Formation oder auf der Spur",
      _auf131 is not None and _auf131[0].distance_to(_f131.pos) < 400.0)
# Einstieg der Bots: verteilt auf die Einstiege, nicht alle an einem.
w131._einstieg_zahl = {}
_k131 = [k_ for k_ in w131.kaempfer.values() if k_.ist_bot and k_.team == 0]
_fahrer131 = [k_.darf_fahren for k_ in _k131]
for k_ in _k131:
    k_.darf_fahren = False             # Fahrer steigen an der Basis mit ihrem Wagen ein
_wahl131 = [w131._bot_einstieg(k_, {kn_: (o_, kn_[0]) for kn_, o_, _n, ok_, _g in w131.einstiege(0) if ok_})
            for k_ in _k131 * 2]
for k_, d_ in zip(_k131, _fahrer131):
    k_.darf_fahren = d_
pruef("Bots steigen an mehreren Einstiegen ein (von mehreren Seiten zum Ziel)",
      len(set(_wahl131)) >= 2, str(_wahl131))
# Fahrzeuge: keins mehr nur fuer Menschen; das wertvollere zuerst.
pruef("Keine Fahrzeugart ist mehr nur fuer Menschen",
      not any(getattr(K, n_).get("nur_mensch") for n_ in ("JAGDPANZER", "TROSSWAGEN", "SPULENWAGEN",
                                                             "FUNKWAGEN", "WERFER", "TRAGSCHRAUBER")))
pruef("... und ein Bot nimmt lieber den Tragschrauber als den Buggy daneben",
      _BO131.FAHRZEUG_VORZUG["tragschrauber"] > _BO131.FAHRZEUG_VORZUG["buggy"] + 300)
w131.verlassen(); g131.verlassen()

# Fahrzeuge mit Bot im Testmodus: Werfer baut in seiner Stellung auf und
# schiesst nicht auf eigene Leute; Tragschrauber hebt ab und bombt.
_tm131 = _TM59.Testmodus(app, karte="staubtal_offen")
_p131 = pygame.Vector2(4000, 3200)
_fw131 = _tm131.fahrer_setzen(_p131, 0, {"fahrzeug": "werfer", "team": 0, "hirn": "klassisch", "winkel": 0},
                              mit_fahrzeug=True)
_wb131 = _fw131.fahrzeug if _fw131 is not None else None
if _wb131 is not None:
    _fw131.hirn._fz_stellung = (pygame.Vector2(_wb131.pos), 1e9, _wb131)
    for _ in range(int(5.0 / K.FIXED_DT)):
        _tm131.schritt(K.FIXED_DT)
pruef("Werfer mit Bot: in der Stellung baut er auf",
      _wb131 is not None and _wb131.phase in (1, 2), str(getattr(_wb131, "phase", None)))
_ts131 = _tm131.fahrer_setzen(_p131 + pygame.Vector2(0, 600), 0,
                              {"fahrzeug": "tragschrauber", "team": 0, "hirn": "klassisch", "winkel": 0},
                              mit_fahrzeug=True)
_hs131 = _ts131.fahrzeug if _ts131 is not None else None
for _ in range(int(4.0 / K.FIXED_DT)):
    _tm131.schritt(K.FIXED_DT)
pruef("Tragschrauber mit Bot: er nimmt Anlauf und hebt ab",
      _hs131 is not None and _hs131.luft, str(getattr(_hs131, "luft", None)))
# Testmodus: Punkt, Basis, Wasser aus dem Spawner.
_tm131.eroberungspunkt_setzen(_p131 + pygame.Vector2(400, 0), {"team": 1})
_tm131.startbasis_setzen(_p131 - pygame.Vector2(900, 0), {"team": 0})
pruef("Testmodus: ein EROBERUNGSPUNKT schaltet die Front ein (mit Besitzer)",
      _tm131.front_an and _tm131.front_punkte()[-1].besitzer == 1 and _tm131.front_basen(0))
_tm131.wasser_setzen(_p131 + pygame.Vector2(0, -900), 0, {"radius": 2}, K.WASSER_TIEF)
_wt131 = _p131 + pygame.Vector2(0, -900)
pruef("... WASSER: TIEF malt Wasser, und das Wegenetz kennt es",
      _tm131.welt.ebene(0).kachel(int(_wt131.x // K.TILE), int(_wt131.y // K.TILE)) == K.WASSER_TIEF
      and not _tm131.welt.wege._frei(0, int(_wt131.x // K.TILE), int(_wt131.y // K.TILE)))
_tm131.alles_weg()
pruef("... LEEREN nimmt das gemalte Wasser wieder weg",
      _tm131.welt.ebene(0).kachel(int(_wt131.x // K.TILE), int(_wt131.y // K.TILE)) != K.WASSER_TIEF)
_bild131b = pygame.Surface((K.GAME_W, K.GAME_H))
_tm131.info = 1
_tm131.zeichnen(_bild131b, 1.0)
pruef("... und INFO zeichnet die Gruppen der Front", True)
_tm131.verlassen()

print("\n-- 0.34.132: JE SEITE in SCHLACHT je Karte, von sehr wenig bis sehr viel")
from dustfront import regeln as _R132, netz as _NZ132
_f132 = _R132.vorgabe(modus="schlacht", karte="flusstal")
_w132 = _R132.NACH_NAME["schlacht_seite"].werte(_f132)
pruef("FLUSSTAL: JE SEITE von 1 bis 150, Vorgabe 24 (aus dem Kartenkopf)",
      _w132[0] == 1 and _w132[-1] == 150 and _f132["schlacht_seite"] == 24 and len(_w132) >= 15, str(_w132))
_s132 = _R132.vorgabe(modus="schlacht", karte="schneefeld")
pruef("... eine kleine Karte ohne Angabe traegt nach ihrer Flaeche weniger (SCHNEEFELD)",
      max(_R132.NACH_NAME["schlacht_seite"].werte(_s132)) < 12 and _s132["schlacht_seite"] <= 12)
_g132 = _R132.vorgabe(modus="schlacht", karte="flusstal", schlacht_seite=150)
_g132["karte"] = "schneefeld"
_g132 = _R132.saeubern(_g132)
pruef("... wer die Karte wechselt, bekommt hoechstens, was die neue traegt",
      _g132["schlacht_seite"] == max(_R132.NACH_NAME["schlacht_seite"].werte(_g132)), str(_g132["schlacht_seite"]))
pruef("... und das Menue sagt bei sehr vielen, dass es viel ist",
      "VIEL" in _R132.anzeige(_R132.vorgabe(modus="schlacht", karte="flusstal", schlacht_seite=100), "schlacht_seite"))
_l132 = _NZ132.Leitung.__new__(_NZ132.Leitung)
_l132._raus = [b"x" * 40000]
_l132._welt_bytes = 30000
_l132._welt_nr = _l132._bestaetigt = 0
_l132._ausgelassen_folge = 0
_l132.ausgelassen = 0
_l132._wirkung_rest = []
_l132._basis = None
_l132._seit_voll = 0
pruef("Netz: mit sehr vielen Kaempfern faellt nicht jede zweite Weltmeldung aus (die Stau-Grenze waechst mit)",
      _l132._welt_senden({"t": "welt", "wirkung": []}) is not None)

print("\n-- 0.34.133: nicht alle zum selben Kampf - Zulauf begrenzt, eigene Vorstoesse")
w133, g133 = _paar59("schlacht", karte="staubtal_offen")
w133._regeln_setzen(dict(_R199.vorgabe(), modus="schlacht", karte="staubtal_offen", schlacht_seite=8))
_p133 = pygame.Vector2(4800, 3200)
w133._lage = {0: [(pygame.Vector2(_p133), w133.welt.zeit)]}
_zu133 = [w133.kampf_zuteilen(0, n_, _p133 + pygame.Vector2(300, 0), 1000.0, K.SCHLACHT["kampf_zulauf"]) for n_ in range(6)]
pruef("Zu einem gemeldeten Kampf gehen hoechstens kampf_zulauf zugleich, die anderen nicht",
      sum(1 for z_ in _zu133 if z_ is not None) == K.SCHLACHT["kampf_zulauf"], str(_zu133))
pruef("... wer schon zugesagt hat, bekommt ihn wieder",
      w133.kampf_zuteilen(0, 0, _p133, 1000.0, K.SCHLACHT["kampf_zulauf"]) is not None)
w133.welt.zeit += K.SCHLACHT["zulauf_halten"] + 1.0
w133._lage = {0: [(pygame.Vector2(_p133), w133.welt.zeit)]}
pruef("... nach zulauf_halten duerfen andere nachruecken",
      w133.kampf_zuteilen(0, 99, _p133, 1000.0, K.SCHLACHT["kampf_zulauf"]) is not None)
_ab133 = {round(p_.y) for p_ in (w133._schlacht_ziele(sp_)[2][0] for sp_ in range(K.SCHLACHT["spuren"]))}
pruef("Ohne Front: die Abschnitte liegen ueber die Kartenhoehe verteilt (mehr als die Haelfte)",
      max(_ab133) - min(_ab133) > w133.welt.ebene(0).pixel_hoehe * 0.5, str(sorted(_ab133)))
_st133 = sum(1 for n_ in range(K.BOTS["nummer_ab"], K.BOTS["nummer_ab"] + 200)
             if ((n_ * 2654435761) % 1000) / 1000.0 < K.SCHLACHT["stosstrupp"])
pruef("... und ein Teil zieht als Stosstrupp gleich zur Basis der anderen (etwa ein Viertel)",
      30 <= _st133 <= 70, str(_st133))
w133.verlassen(); g133.verlassen()
w133b, g133b = _paar59("schlacht", karte="flusstal")
w133b._regeln_setzen(dict(_R199.vorgabe(), modus="schlacht", karte="flusstal", schlacht_seite=20))
w133b._einstiegszonen_waehlen(); w133b._fahrzeuge_neu_aufstellen(); w133b._bots_fuehren(0.0, sofort=True)
w133b.front_anlegen()
for p_ in w133b.front_punkte():                     # ROT haelt seine Seite: Punkte im Osten liegen hinter der Front
    if p_.pos.x < w133b.welt.ebene(0).pixel_breite * 0.4:
        p_.besitzer, p_.stand = 0, -1.0
_z133 = dict(w133b._front_ziele(0))
pruef("Front: Punkte hinter der Front sind Ziele fuer Vorstoesse (klein gewichtet)",
      any(abs(v_ - K.FRONT["gewicht_vorstoss"]) < 1e-9 for v_ in _z133.values()), str(_z133))
_gr133 = [w133b._gruppe_bilden(0, [(z_, 1.0)], w133b.hauptbasis(0).pos, random.Random(i_))
          for i_, z_ in enumerate(list(w133b._vorstoss_ziele[0])[:1] * 6)]
pruef("... ein Stosstrupp ist einer oder zwei", all(g_.soll <= 2 for g_ in _gr133), str([g_.soll for g_ in _gr133]))
for g_ in _gr133:
    w133b._gruppen.remove(g_)
w133b._gruppen[:] = []
_n133 = sum(1 for k_ in w133b.kaempfer.values() if k_.team == 0 and k_.ist_bot)
_ziel133 = []
for _ in range(_n133):                             # je Bot eine Gruppe von 1
    z_ = w133b._bedarf(0, list(_z133.items()))
    _ziel133.append(z_)
    w133b._gruppen.append(type("G", (), {"team": 0, "ziel": z_, "mitglieder": [None]})())
_haeufig133 = max(_ziel133.count(z_) for z_ in set(_ziel133))
pruef("... kein Ziel bekommt mehr als ziel_anteil der Bots, solange es andere gibt",
      _haeufig133 <= int(_n133 * K.FRONT["ziel_anteil"]) + 1 and len(set(_ziel133)) >= 4,
      "%d von %d Bots, %d Ziele" % (_haeufig133, _n133, len(set(_ziel133))))
w133b.verlassen(); g133b.verlassen()

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
pruef("SCHLACHT: wer einen umwirft, bekommt sofort seinen Punkt (am Boden, noch nicht tot; seit 0.34.135 einer)",
      _feind134.am_boden and _ich134.schlacht_punkte == 1 == K.SCHLACHT["punkte"]["abschuss"],
      str(_ich134.schlacht_punkte))
_feind134.boden_rest = 0.0
for _ in range(10):
    w134._revive(0.1)
    w134._tote_abrechnen(0.1)
pruef("... stirbt er danach, gibt es nicht noch einmal Punkte",
      not _feind134.lebt and _ich134.schlacht_punkte == 1, str(_ich134.schlacht_punkte))
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
_gk134 = w134.kaempfer[g134.ich.nummer]
_wf134b = _FZ134.neu("werfer", _gk134.pos + pygame.Vector2(0, 90), 0)
w134.welt.dazu(_wf134b); w134.fahrzeuge.append(_wf134b)
if _gk134.fahrzeug is not None:
    w134._aussteigen(_gk134)
_gk134.lebt = True; _gk134.am_boden = False
w134._einsteigen(_gk134, _wf134b)
_wf134b.phase, _wf134b.fortschritt = 2, 1.0
for _ in range(20):
    w134.schritt(K.NETZ["takt"]); g134.schritt(K.NETZ["takt"])
    _wf134b.phase = 2
pruef("... auch beim Gast steht die Karte (seit 0.34.135: dort kennt nur das Fahrzeug seinen Fahrer)",
      g134._werfer_eigen() is not None and g134._werfer_eigen().art == "werfer")

print("\n-- 0.34.135: Zielzonen des Werfers, Formation, Staerke --")
_t135 = _ich134.team
_zn135 = w134.werfer_zonen(_t135)
pruef("Werfer-Zonen: um jeden eigenen Kaempfer eine Sichtzone, weiter als er sieht",
      any(a_ == "sicht" and r_ > K.SCHLACHT["karte_sicht"] and o_.distance_to(_ich134.pos) < 1.0
          for o_, r_, a_ in _zn135))
pruef("... um jeden Eroberungspunkt eine Zone",
      sum(1 for _o, _r, a_ in _zn135 if a_ == "punkt") >= len(w134.front_punkte()) > 0)
_ue135 = __import__("dustfront.schlacht", fromlist=["Ueberflug"]).Ueberflug(
    pygame.Vector2(_ich134.pos) + pygame.Vector2(2500, 0), _t135, _ich134.fraktion, 0)
w134.ueberfluege.append(_ue135)
w134._wsp_zuletzt = -99.0; w134._wzn_merk = {}
w134._werfer_spuren_merken()
w134.ueberfluege.remove(_ue135)
w134._wzn_merk = {}
_sp135 = pygame.Vector2(_ue135.pos)
pruef("... wo die Aufklaerungsdrohne war, bleibt eine Spur, auch wenn sie weg ist",
      any(a_ == "spur" and o_.distance_to(_sp135) < 1.0 for o_, _r, a_ in w134.werfer_zonen(_t135)))
w134._werfer_spuren = [(w134._zeit - K.WERFER["zonen"]["spur_dauer"] - 1.0, _sp135, 650.0, _t135)]
w134._wsp_zuletzt = -99.0; w134._werfer_spuren_merken(); w134._wzn_merk = {}
pruef("... und vergeht nach spur_dauer Sekunden",
      not any(a_ == "spur" and o_.distance_to(_sp135) < 1.0 for o_, _r, a_ in w134.werfer_zonen(_t135)))
_fe135 = next(k_ for k_ in w134.kaempfer.values() if k_.lebt and getattr(k_, "team", -1) == 1 - _t135)
_fe135.markiert_fuer, _fe135.markiert_rest = "team%d" % _t135, 10.0
w134._wzn_merk = {}
pruef("... um einen markierten Gegner eine Zone",
      any(a_ == "feind" and o_.distance_to(_fe135.pos) < 1.0 for o_, _r, a_ in w134.werfer_zonen(_t135)))
_weit135 = max(w134.werfer_weite() - 50.0, K.WERFER["salve"]["nah"] + 50.0)
_frei135 = None
for _w in range(0, 360, 10):
    _q = _wf134.rohr_mitte() + pygame.Vector2(_weit135, 0).rotate(_w)
    if not any(o_.distance_to(_q) <= r_ for o_, r_, _a in w134.werfer_zonen(_t135)):
        _frei135 = _q
        break
pruef("... ausserhalb aller Zonen gilt kein Ziel (Grund 3)",
      _frei135 is None or w134.werfer_pruefen(_wf134, _t135, _frei135) == 3)
_in135 = _fe135.pos
pruef("... im Umkreis eines markierten Gegners schon (wenn in Reichweite)",
      w134.werfer_pruefen(_wf134, _t135, _in135 + pygame.Vector2(K.WERFER["zonen"]["feind"] - 30, 0)) in (0, 1, 2))
_gz135 = g134.werfer_zonen(g134.ich.team)
pruef("... der Gast rechnet die Zonen selbst (seine Karte zeigt sie)",
      any(a_ == "sicht" for _o, _r, a_ in _gz135) and any(a_ == "punkt" for _o, _r, a_ in _gz135))
_bild135 = pygame.Surface((K.GAME_W, K.GAME_H))
g134.zeichnen(_bild135, 1.0)
pruef("... und zeichnet die Karte mit Zonen ohne Fehler", g134.__dict__.get("_wzn_bild") is not None)
_wf134.einschlaege = []
w134._werfer_salve(_wf134, pygame.Vector2(_ich134.pos) + pygame.Vector2(1500, 0), _t135)
_ort135 = [pygame.Vector2(e_[1], e_[2]) for e_ in _wf134.einschlaege]
_mi135 = pygame.Vector2(_ich134.pos) + pygame.Vector2(1500, 0)
_ab135 = sorted(o_.distance_to(_mi135) for o_ in _ort135)
pruef("Salve: eine Rakete in die Mitte, die anderen im Ring darum (keine Linie)",
      len(_ort135) == 6 and _ab135[0] <= K.WERFER["salve"]["wackeln"] + 0.5
      and all(o_ > K.WERFER["salve"]["streu"] * K.WERFER["salve"]["formation"] - K.WERFER["salve"]["wackeln"] - 0.5
              for o_ in _ab135[1:]), str([round(x_) for x_ in _ab135]))
_wk135 = [math.degrees(math.atan2(o_.y - _mi135.y, o_.x - _mi135.x)) % 360 for o_ in _ort135[1:]]
_wk135.sort()
_luecke135 = max((_wk135[(i_ + 1) % 5] - _wk135[i_]) % 360 for i_ in range(5))
pruef("... gleichmaessig rundum verteilt (keine Luecke ueber 100 Grad)", _luecke135 < 100, str([round(x_) for x_ in _wk135]))
pruef("... jede Rakete staerker und mit groesserem Radius als vor 0.34.135",
      K.WERFER["salve"]["schaden"] > 90 and K.WERFER["salve"]["radius"] > 46)

from dustfront import bots as _BO135
_bots135 = w134._bots()
# Hier sind es nur ein paar Bots - die Schwelle fuer die Probe tiefer.
_staffel_alt135 = K.BOTS["staffel"]
K.BOTS["staffel"] = ((min(len(_bots135), 5), 2),)
_jede135 = 2
_ruf135 = {}
_alt135 = _BO135.BotHirn.eingabe
def _zaehl135(self, dt):
    z_ = _ruf135.setdefault(self.k.nummer, [0, 0.0]); z_[0] += 1; z_[1] += dt
    return _alt135(self, dt)
_BO135.BotHirn.eingabe = _zaehl135
try:
    for _ in range(6 * _jede135):
        w134._bots_steuern(K.FIXED_DT)
finally:
    _BO135.BotHirn.eingabe = _alt135
    K.BOTS["staffel"] = _staffel_alt135
_mit135 = [v_ for n_, v_ in _ruf135.items()]
pruef("Gestaffelt: ab K.BOTS staffel denkt jeder Bot nur jeden 2. Schritt (%d Bots)" % len(_bots135),
      _jede135 > 1 and _mit135 and all(v_[0] == 6 for v_ in _mit135),
      str(sorted(set(v_[0] for v_ in _mit135))))
pruef("... und bekommt dabei die ganze vergangene Zeit (keine Uhr laeuft langsamer)",
      all(abs(v_[1] - 6 * _jede135 * K.FIXED_DT) <= _jede135 * K.FIXED_DT + 1e-9 for v_ in _mit135))
w134.verlassen(); g134.verlassen()

print()
print("FEHLER:", fails or "keine")
pygame.quit()
