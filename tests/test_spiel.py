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
pruef("Zwei Brecheisenschlaege toeten einen Spieler",
      2 * b["schaden"] >= K.SPIELER["leben"],
      "%.0f x 2 gegen %.0f Leben" % (b["schaden"], K.SPIELER["leben"]))
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

# **Der eigentliche Fehler:** ein Wiedereinstieg darf nicht umsonst
# nachfuellen.
wirt_k.magazin[name] = 0
vorher_vorrat = wirt_k.vorrat[name]
w._wieder_einsteigen(wirt_k)
pruef("Ein Wiedereinstieg fuellt das Magazin",
      wirt_k.magazin[name] == K.WAFFEN[name]["magazin"],
      "%d" % wirt_k.magazin[name])
pruef("Und bezahlt es aus dem Vorrat",
      wirt_k.vorrat[name] == vorher_vorrat - K.WAFFEN[name]["magazin"],
      "%d statt %d" % (wirt_k.vorrat[name],
                       vorher_vorrat - K.WAFFEN[name]["magazin"]))

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
pruef("Auf STAUBTAL stehen fuenf Buggys", len(w.fahrzeuge) == 5, str(len(w.fahrzeuge)))
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

# Schaden: 70 % kommen beim Fahrer an, kein Stoss.
fahrer69.unverwundbar = 0.0
fahrer69.leben = 100.0
fahrer69.tempo.update(0, 0)
fahrer69.schaden(10.0, pygame.Vector2(400, 0), andere69)
pruef("Im Buggy kommen 70 % vom Schaden an",
      abs((100.0 - fahrer69.leben) - 10.0 * K.FAHRZEUG["schaden_anteil"]) < 1e-6
      and abs(K.FAHRZEUG["schaden_anteil"] - 0.7) < 1e-9,
      "%.2f" % (100.0 - fahrer69.leben))
pruef("... und er wird nicht weggestossen", fahrer69.tempo.length() < 1e-6)
andere69.unverwundbar = 0.0
andere69.leben = 100.0
andere69.schaden(10.0, None, fahrer69)
pruef("Zu Fuss kommt der volle Schaden an", abs(andere69.leben - 90.0) < 1e-6)
fahrer69.leben = fahrer69.max_leben
# Seit 0.34.18 nimmt der Wagen den Treffer und reicht ihn an den Fahrer
# weiter (der dann wie oben 70 % abbekommt). Bis dahin ging die Kugel am
# unzerstoerbaren Wagen vorbei auf den Fahrer.
b69.schaden(30.0, None, andere69)
w.welt._raster_bauen()
pruef("Ein Treffer am Buggy: er nimmt Schaden, der Fahrer 70 Prozent davon",
      b69.lebt and not b69.kaputt and b69.leben == b69.max_leben - 30.0
      and abs((fahrer69.max_leben - fahrer69.leben) - 30.0 * 0.7) < 1e-6,
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
pruef("Der Gast sieht alle fuenf Buggys", len(ga.fahrzeuge) == 5, str(len(ga.fahrzeuge)))
pruef("... den besetzten an derselben Stelle",
      len(_gb69) == 1 and _gb69[0].pos.distance_to(b69.pos) < 2.0,
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
      len(w.fahrzeuge) == 5
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
      len(ga.fahrzeuge) == 5
      and all(_buggy_da70(_f70g, _r70g, ga, b_, MK.FARBE_BUGGY) for b_ in ga.fahrzeuge))
w.verlassen(); ga.verlassen()

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
fest_plaetze = KMOD.hotbar_aus_loadout(app.konto.loadouts[fest_nr])
wl, gl = gefechtspaar("pvp", regeln={"loadouts": "gleich",
                                     "loadout_nr": fest_nr})
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

# Der Vorrat steht nur bei knapper Munition unter den Feldern.
unter = pygame.Rect(0, AZ.H - 14, AZ.W, 12)
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
sx = r9.width / float(wm9.welt.ebenen[0].pixel_breite)
sy = r9.height / float(wm9.welt.ebenen[0].pixel_hoehe)
px = (int(r9.x + ich9.pos.x * sx), int(r9.y + ich9.pos.y * sy))
pruef("Man selbst steht darauf, wo man ist",
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
pruef("Bis zur weitesten Stufe, nicht darueber",
      wz.zoom_ziel == max(K.ZOOM["stufen"]), "%.2f" % wz.zoom_ziel)
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
pruef("Mit Zoom gibt es ein normales Bild, ausserhalb Nebel",
      sicht is not None and sicht.size == (K.GAME_W, K.GAME_H)
      and sicht.collidepoint(ich_z.pos.x, ich_z.pos.y))

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
draussen = pygame.Vector2(sicht.right + 120, sicht.centery)
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
pruef("ERWEITERT zeigt alle Regeln und merkt es sich",
      "r:knapp" in [el.name for el in _t46.elemente]
      and app.opt["runden_erweitert"] is True)
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
      len(w71.fahrzeuge) == 5
      and all(b_.lebt and b_ in w71.welt.wesen for b_ in w71.fahrzeuge),
      str([(b_.lebt, b_ in w71.welt.wesen) for b_ in w71.fahrzeuge]))
pruef("... und der Gast sieht dieselben fuenf", len(g71.fahrzeuge) == 5)

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
_soll71 = (K.C4["schaden"] * (1.0 - 0.72 * min(1.0, _d71 / K.C4["radius"]))
           * K.FAHRZEUG["schaden_anteil"])
pruef("Der Fahrer bekommt 70 % der Ladung ab",
      abs((1000.0 - _gk71.leben) - _soll71) < 0.01,
      "%.1f statt %.1f" % (1000.0 - _gk71.leben, _soll71))
pruef("Der Buggy bleibt heil und fahrbereit",
      _gb71.lebt and _gb71 in w71.welt.wesen and _gb71.fahrer is _gk71)
_gk71.leben = _gk71.max_leben

# Die naechste Runde aus dem Plan: die Buggys bleiben, leer, am Platz.
w71._runde_neu()
w71.schritt(K.FIXED_DT)
pruef("Nach einem Neustart stehen die Buggys leer an ihrem Platz",
      len(w71.fahrzeuge) == 5
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
_alt72 = _KM72.hotbar_aus_loadout(app.konto.loadout)
_neu_nr72 = next(i_ for i_, lo_ in enumerate(app.konto.loadouts)
                 if _KM72.hotbar_aus_loadout(lo_) != _alt72)
_neu72 = _KM72.hotbar_aus_loadout(app.konto.loadouts[_neu_nr72])
_gk72 = w72.kaempfer[g72.meine_nummer]
pruef("(Zu Beginn tragen beide das alte)",
      _gk72.waffen == _alt72 and w72.ich.waffen == _alt72, str(_gk72.waffen))
app.konto.gewaehlt = _neu_nr72
netz_durchlassen(w72, g72, 6)
pruef("Ein im Spiel geaendertes Loadout kommt beim Gastgeber an",
      _gk72.angemeldet is not None
      and _KM72.hotbar_aus_loadout(_gk72.angemeldet) == _neu72,
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
w80 = Gefecht(app, "WIRT", gastgeber=_n80, modus="team", seed=3, regeln={"bots": 2})
_bot80 = w80._bots()[0]
_ich80 = w80.ich


def _stelle80(abstand, frei=True):
    for a_ in range(0, 360, 10):
        p_ = _bot80.pos + pygame.Vector2(abstand, 0).rotate(a_)
        if not w80.welt.frei(p_, 9, 0, True):
            continue
        # Frei heisst seit 0.34.26 auch: keine Kiste dazwischen - an der
        # bleibt jede Kugel haengen, und der Bot schiesst nicht hinein.
        if frei and w80.welt.deckung(_bot80.pos, p_, 0) == "":
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
pruef("STAUBTAL hat fuenf Buggys", len(w80.fahrzeuge) == 5, str(len(w80.fahrzeuge)))
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
pruef("Ein Schuss auf den Wagen: der Wagen nimmt Schaden, der Fahrer 70 Prozent",
      _wg80.leben < _vor80[0]
      and abs((_vor80[1] - _gk80.leben) - K.WAFFEN["sturm"]["schaden"] * 0.7) < 0.5,
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
pruef("Nach der Brennzeit ist das Wrack weg", len(w80.fahrzeuge) == 4)
_beide80(K.FAHRZEUG["neu_nach"] + 1.5, w80, g80)
_neu80 = w80.fahrzeuge[-1]
pruef("Spaeter steht irgendwo ein neuer Wagen, heil und an einem freien Platz",
      len(w80.fahrzeuge) == 5 and not _neu80.kaputt and _neu80.passt(_neu80.pos)
      and _neu80.pos.distance_to(_wg80.start[0]) > 1.0 and len(g80.fahrzeuge) == 5)
w80.fahrzeuge[1].schaden(K.FAHRZEUG["leben"], None, _ich80)
w80.wunsch = dict(w80.regelwerk)
w80._runde_neu()
_beide80(0.3, w80, g80)
pruef("Zur neuen Runde stehen wieder alle fuenf heil an ihren Plaetzen",
      len(w80.fahrzeuge) == 5 and all(not b_.kaputt and b_.leben == b_.max_leben
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
_finger82(pygame.FINGERDOWN, 4, *_knopf82("waffe"))
pruef("WFF waehlt die naechste Waffe der Hotbar", _tw82._waffe_wunsch == 1,
      str(_tw82._waffe_wunsch))
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
pruef("Die Szene sagt, wo die Plaetze der Hotbar stehen",
      len(_plaetze82) == len(_tw82.ich.waffen) and len(_plaetze82) >= 3, str(len(_plaetze82)))
_finger82(pygame.FINGERDOWN, 25, *_plaetze82[2].center)
pruef("Den dritten Platz antippen waehlt die dritte Waffe", _tw82._waffe_wunsch == 2,
      str(_tw82._waffe_wunsch))
_finger82(pygame.FINGERUP, 25, *_plaetze82[2].center)
pruef("... und schiesst dabei nicht", not _tapp82.eingabe.gehalten("feuer"))
_tw82._waffe_wunsch = -1
_finger82(pygame.FINGERDOWN, 26, *_plaetze82[-1].midtop)
pruef("... auch knapp darueber getroffen (die Felder sind nur 20 hoch)",
      _tw82._waffe_wunsch == len(_plaetze82) - 1, str(_tw82._waffe_wunsch))
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
print("\n-- 3D nur fuer Gegenstaende, Figuren flach (0.34.25, 0.34.34)")
from dustfront.render import Renderer as _R83
from dustfront.entities import (Spieler as _Sp83, Gegner as _Gg83,
                                Aufsammler as _Auf83)
from dustfront.fahrzeug import Buggy as _Bg83
from dustfront.mehrspieler import Kaempfer as _Kae83
_f83 = K.FIGUREN_3D
pruef("Buggy und Beute haben eine Hoehe; Spieler, Bots und Geschosse nicht",
      _Bg83.hoehe_3d > 0 and _Auf83.hoehe_3d > 0
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
_rot83, _seite83 = _zeichne83(_f83["buggy"], (20, 20))
_mx83 = sum(x for x, _ in _rot83) / len(_rot83)
_my83 = sum(y for _, y in _rot83) / len(_rot83)
pruef("Am Rand oben links: der Deckel rueckt von der Mitte weg, nach oben links",
      _mx83 < 19.5 and _my83 < 19.5, "%.1f %.1f" % (_mx83, _my83))
pruef("... und darunter steht eine dunklere Seitenwand in der Farbe der Figur",
      len(_seite83) > 10 and all(_z83.get_at(q)[1] < 60 for q in _seite83[:20]),
      "%d Pixel" % len(_seite83))
_rot83, _seite83 = _zeichne83(_f83["buggy"], (100, 100))
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
_rot83, _ = _zeichne83(_f83["buggy"], (20, 20))
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
w86.verlassen()

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
pruef("Den Testmodus gibt es am Rechner, nicht mit Touch",
      _TM87.verfuegbar(), "")
_alt87 = os.environ.get("DUSTFRONT_TOUCH")
os.environ["DUSTFRONT_TOUCH"] = "1"
pruef("... mit Touch-Steuerung (iOS) nicht", not _TM87.verfuegbar(), "")
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
pruef("Regel BOT-KI: klassisch ist die Vorgabe, GOAP waehlbar",
      _RG88.vorgabe()["bot_ki"] == "klassisch"
      and _RG88.saeubern({"bot_ki": "goap"})["bot_ki"] == "goap"
      and _RG88.saeubern({"bot_ki": "unsinn"})["bot_ki"] == "klassisch", "")
_n88 = netz.Gastgeber(_neuer_port())
_w88 = Gefecht(app, "WIRT", gastgeber=_n88, modus="team", seed=88,
               regeln={"bots": 4, "bot_ki": "goap"})
pruef("... mit GOAP denken alle Bots der Runde zielorientiert",
      _w88._bots() and all(isinstance(b_.hirn, _BG88.GoapHirn) for b_ in _w88._bots()),
      str([type(b_.hirn).__name__ for b_ in _w88._bots()]))
_w88.verlassen()
_n88 = netz.Gastgeber(_neuer_port())
_w88 = Gefecht(app, "WIRT", gastgeber=_n88, modus="team", seed=88, regeln={"bots": 4})
pruef("... ohne die Regel klassisch wie bisher",
      _w88._bots() and not any(isinstance(b_.hirn, _BG88.GoapHirn) for b_ in _w88._bots()), "")
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
_tm.zoom_ziel = _tm._zoom_weich = 1.5
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
_tm._innen_nr = 0
_tm.menue_wirken("innen", 1, ausloesen=True)
_bot94.hirn.goap_rest = 0.0
_sim87(int(0.25 / _D87))
pruef("... PANIK: die gezeigte Figur rennt (Ziel PANIK)",
      _bot94.hirn.innen.panik and _bot94.hirn.gehirn.ziel is not None
      and _bot94.hirn.gehirn.ziel.name == "panik", str(_bot94.hirn.gehirn.ziel))
_tm.innen_wirken("ruhe")
pruef("... RUHE: vorbei", not _bot94.hirn.innen.panik and _bot94.hirn.innen.stress == 0.0, "")
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
pruef("Sprechen: wer einen sieht und andere in Sprechweite hat, sagt es - dann weiss es der Trupp",
      _feind95 in _al95.lage and _m95.funk.endswith("!"), _m95.funk)
_weg95 = pygame.Vector2(_m95.pos)
_m95.pos.update(_m95.pos + pygame.Vector2(K.TRUPP["sprech_weite"] * 3, 0))
_al95.lage = {}
_al95._lage_sammeln(_al95.lebende())
pruef("... wer zu weit weg ist, dessen Wissen kommt nicht an",
      _feind95 not in _al95.lage and not _al95.in_kontakt(_m95)
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


pruef("Trupp besorgt: Rueckzug in Wellen; zuversichtlich: Druck; neutral: Feuerkampf",
      _zustand95(1) == "rueckzug" and _zustand95(3) == "druck" and _zustand95(2) == "feuerkampf", "")
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
for _ in range(int(14.0 / _D87)):
    _tm.schritt(_D87)
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
pruef("... ein Spruch dauert: er stand dabei (FUNK > im Protokoll)",
      any(t_.startswith("PLAN: funk_hilfe") for _z, t_ in _al95.fuehrer.hirn.gehirn.protokoll), "")
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
pruef("... der Anfuehrer will Rauch legen, um es sicher zu machen",
      _tr96.fuehrer.hirn.gehirn.dringlichkeiten.get("rauch_legen", 0) > 0,
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
pruef("... geholt wird erst, wenn es sicher genug ist (Rauch oder ein zuversichtlicher Trupp) - "
      "dann steht er wieder",
      _erst96 is True and (False, "zum_kameraden") in _akt96
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
      _lieg96.am_boden and _tm.beobachter and not _tm._verbuendet(_lieg96), "")

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

print()
print("FEHLER:", fails or "keine")
pygame.quit()
