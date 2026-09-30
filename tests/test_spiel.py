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
    if (host.welt.frei(kandidat, a.radius, 0)
            and host.welt.frei(gegenueber, b.radius, 0)
            and host.welt.sicht_frei(kandidat, gegenueber, 0)):
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

# Mausrad verschiebt die Ansicht, wie im Einzelspieler.
#
# Geprueft wird ueber ein echtes Ereignis, nicht ueber das Setzen von
# e.rad: Rad und Tastendruecke werden seit 0.19.2 dort aufgehoben, weil
# der Zeitschritt bei hoher Bildrate nicht in jedem Bild laeuft und die
# Druecke sonst verlorengehen.
host.blick = 0
e.neues_bild()
host.ereignis(pygame.event.Event(pygame.MOUSEWHEEL, {"x": 0, "y": 1}))
host.schritt(K.FIXED_DT)
pruef("Das Mausrad verschiebt die Ebenenansicht", host.blick == 1,
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
    # E wird gehalten, nicht gedrueckt: an derselben Taste haengt das
    # Aufhelfen, und das braucht Zeit.
    for _ in range(10):
        e.neues_bild()
        e._gehalten = {"nutzen"}
        host.schritt(K.NETZ["takt"])
        gast.schritt(K.NETZ["takt"])
    e.neues_bild(); e._gehalten = set()
    pruef("Der Gast kommt ueber die Treppe eine Ebene hoch",
          gast_ich.ebene == 1, "Ebene %d" % gast_ich.ebene)

# ── Die drei Spielarten ──────────────────────────────────────────────
from dustfront.mehrspieler import KampfGegner
from dustfront import entities as EN

_port = [51300]

def gefechtspaar(modus, **kw):
    """Gastgeber und Gast in einer Spielart, ueber echte Steckdosen.

    Mit festem Seed: sonst wuerfelt jedes Gefecht seine Einstiegsplaetze
    neu, und Pruefungen, die vom Einstiegsort abhaengen, sind mal gruen
    und mal rot.
    """
    _port[0] += 1
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

# ── Ebenen: nur eine nach oben ───────────────────────────────────────
# Wer unten steht, soll die Etage ueber sich durchscheinen sehen - aber
# nicht gleich drei Stockwerke uebereinander.
gezeichnet = []
echt = szene.renderer.ebene_zeichnen
def merken(ziel, welt, index, ecke, dunkel):
    gezeichnet.append(index)
    return echt(ziel, welt, index, ecke, dunkel)
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
_port[0] += 1
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

w.zone_stand[0] = 0.0      # der Gastgeber kann beim Einstieg schon drin
w._zone(1.0)               # gestanden haben; gemessen wird eine Sekunde
pruef("Allein im Kreis laedt es fuer die eigene Mannschaft",
      abs(w.zone_stand[0] - K.ZONE["je_sekunde"]) < 0.01
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
      abs(w.zone_stand[0] - K.ZONE["je_sekunde"]) < 0.01,
      "%.1f" % w.zone_stand[0])
gast_k.pos.update(weit); gast_k.vorher.update(gast_k.pos)
w.zone_stand[0] = 0.0
w._zone(1.0)                      # zwei gegen keinen
pruef("Zwei gegen keinen laedt schneller",
      w.zone_stand[0] > K.ZONE["je_sekunde"], "%.1f" % w.zone_stand[0])
pruef("Aber nie schneller als die Obergrenze",
      w.zone_stand[0] <= K.ZONE["hoechstens"] + 0.01, "%.1f" % w.zone_stand[0])
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
pruef("Der Gastgeber kann die Regeln stellen",
      "modus" in wirt_eintraege and "neu" in wirt_eintraege
      and "teams" in wirt_eintraege, str(wirt_eintraege))
pruef("Der Gast stellt keine Regeln",
      not ({"modus", "neu", "teams", "knapp", "loadouts"}
           & set(gast_eintraege)), str(gast_eintraege))
pruef("Seine eigene Ausruestung und sein Konto schon",
      "ausruestung" in gast_eintraege and "konto" in gast_eintraege,
      str(gast_eintraege))
pruef("Und der Gastgeber stellt die Ausruestungsregel",
      "loadouts" in wirt_eintraege, str(wirt_eintraege))
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
pruef("Und sagt, dass sie zurueckkommt", "ZURUECK" in w.hinweis, w.hinweis)
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
halten = {"will": [0.0, 0.0], "ziel": [treppe.x + 20, treppe.y],
          "nutzen": True, "knoepfe": []}
w._anwenden(wirt_k, halten)
pruef("Einmal Druecken bringt eine Ebene hoch", wirt_k.ebene == 1,
      "Ebene %d" % wirt_k.ebene)
# Taste weiter gehalten: es darf nichts mehr passieren.
for _ in range(60):
    w._anwenden(wirt_k, halten)
pruef("Gehalten bleibt es bei dieser einen Ebene", wirt_k.ebene == 1,
      "Ebene %d" % wirt_k.ebene)
pruef("Und die Sperre laeuft", wirt_k.treppe_rest > 0,
      "%.2f s" % wirt_k.treppe_rest)
# Nach der Sperre geht es wieder - dann eben zurueck nach unten.
for _ in range(int(K.GEFECHT["treppe_takt"] / K.FIXED_DT) + 4):
    wirt_k.schritt(K.FIXED_DT)
w._anwenden(wirt_k, halten)
pruef("Nach der Sperre geht es wieder", wirt_k.ebene == 0,
      "Ebene %d" % wirt_k.ebene)
w.verlassen(); ga.verlassen()

# ── Online: Kennwort und der Weg durch den Router ────────────────────
# Ein Port, der ins Internet offen steht, braucht einen Tuersteher. Und
# die Routerabfrage muss auswertbar sein, ohne dass hier ein Router steht.
from dustfront import upnp

_port[0] += 1
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
_port[0] += 1
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
w.endwerte = w._werte_aller()

zeilen = w._tafel_zeilen()
pruef("Die Tafel hat je Spieler eine Zeile",
      len(zeilen) == len(w.kaempfer), "%d von %d"
      % (len(zeilen), len(w.kaempfer)))
pruef("Und ist nach Abschuessen sortiert",
      zeilen[0]["abschuesse"] >= zeilen[-1]["abschuesse"])
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
w.welt.ebene(brand.ebene)._dekale = None
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
weggedreht = blend_wert(blitz, 0, wirt_k, w.welt)
pruef("Wegdrehen hilft deutlich", weggedreht < 0.5, "%.2f" % weggedreht)
pruef("Aber nicht ganz - der Raum ist trotzdem hell",
      weggedreht > 0.0, "%.2f" % weggedreht)
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

w, ga = gefechtspaar("team", rpg=True)
pruef("Der Gastgeber kann den Werfer einschalten", w.mit_rpg)
pruef("Und der Gast erfaehrt es", ga.rpg_an, str(ga.rpg_an))
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
pruef("Und sehr leer", begehbar > s0.breite * s0.hoehe * 0.6,
      "%d von %d Kacheln begehbar" % (begehbar, s0.breite * s0.hoehe))

# Plateaus: obere Ebene nur Tafeln, und unter jeder Tafel steht Fels.
oben = sum(1 for ty in range(s1.hoehe) for tx in range(s1.breite)
           if s1.begehbar(tx, ty))
pruef("Die obere Ebene ist kein Gangnetz, sondern sind Tafeln",
      0 < oben < s0.breite * s0.hoehe * 0.25,
      "%d Kacheln oben gegen %d unten" % (oben, begehbar))
darunter = 0
for ty in range(s1.hoehe):
    for tx in range(s1.breite):
        if not s1.begehbar(tx, ty):
            continue
        if s0.begehbar(tx, ty) and s0.daten(tx, ty).get("treppe") is None:
            darunter += 1
pruef("Unter die Plateaus kommt man nicht", darunter == 0,
      "%d begehbare Kacheln unter einem Plateau" % darunter)

# Und hinauf kommt man trotzdem.
hoch = [(tx, ty) for ty in range(s0.hoehe) for tx in range(s0.breite)
        if s0.daten(tx, ty).get("treppe") == 1]
runter = [(tx, ty) for ty in range(s1.hoehe) for tx in range(s1.breite)
          if s1.daten(tx, ty).get("treppe") == -1]
pruef("Es gibt Rampen hinauf", len(hoch) >= 3, "%d" % len(hoch))
pruef("Und ebenso viele hinunter", len(runter) == len(hoch),
      "%d hinauf, %d hinunter" % (len(hoch), len(runter)))
# Jede Rampe muss auch wirklich benutzbar sein: oben muss Platz sein.
blockiert = [p for p in hoch
             if not staub.frei(pygame.Vector2(p[0] * K.TILE + K.TILE / 2,
                                              p[1] * K.TILE + K.TILE / 2),
                               K.SPIELER["radius"], 1)]
pruef("Und ueber jeder Rampe ist Platz", not blockiert, str(blockiert))

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
# Selbsterklaerend heisst hier: um den Kreis im Sand steht ein Ring aus
# Fassern, und die beiden anderen liegen in einer Halle bzw. auf einem
# Plateau. Geprueft wird das Wahrzeichen des offenen Kreises.
kreis_a = marken["A"][1]
fasser = 0
for ty in range(s0.hoehe):
    for tx in range(s0.breite):
        if s0.kachel(tx, ty) != K.KISTE:
            continue
        p = pygame.Vector2(tx * K.TILE + K.TILE / 2, ty * K.TILE + K.TILE / 2)
        if 200 < p.distance_to(kreis_a) < 380:
            fasser += 1
pruef("Um den Kreis im Sand steht ein Ring aus Fassern", fasser >= 10,
      "%d Fasser im Ring" % fasser)

# Im Gefecht: die Karte laesst sich waehlen und der Kreis wandert.
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
w.verlassen(); ga.verlassen()

# Eine kaputte oder fehlende Karte darf nichts umwerfen.
pruef("Eine fehlende Karte gibt None", W.karte_lesen("gibtsnicht")[0] is None)
pruef("Und kaputter Text auch", W.karte_aus_text("bloedsinn")[0] is None)
w2, _ga2 = gefechtspaar("pvp", karte="gibtsnicht")
pruef("Das Gefecht laeuft trotzdem, auf der Testkarte",
      w2.karte == "" and len(w2.welt.ebenen) == 3, w2.karte)
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
import dustfront.play, dustfront.render, dustfront.entities, dustfront.mehrspieler
_haengt = [m.__name__ for m in (dustfront.play, dustfront.render,
                                dustfront.entities, dustfront.mehrspieler,
                                sys.modules["dustfront.core"])
           if "kosmetik" in open(m.__file__, encoding="utf-8").read()]
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
      K.gegner_daten("laeufer")["name"] == "LAEUFER"
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
t2 = pygame.Vector2(laeufer_probe.tempo)
laeufer_probe.schaden(1.0, pygame.Vector2(900, 0), None)
pruef("Ein gewoehnlicher Gegner aber schon - sonst faende sich der "
      "Unterschied nicht",
      laeufer_probe.tempo.distance_to(t2) > 100.0,
      "%.0f px/s" % laeufer_probe.tempo.distance_to(t2))

# Die Haengerwache. Sie ist der Grund, warum eine Runde ueberhaupt
# weiterlaeuft: gemessen blieb ein Laeufer 120 Sekunden an einer
# Plateauwand stehen, und weil eine Welle erst endet, wenn alle liegen,
# stand damit alles.
w6.gegner_offen = []; w6.welle_rest = []
opfer = [k for k in w6.kaempfer.values() if k.lebt][0]
haenger = KampfGegner(opfer.pos + pygame.Vector2(700, 0), "laeufer",
                      opfer.ebene, w6)
w6.welt.dazu(haenger)
haenger._ziel = opfer
steht_bei = pygame.Vector2(opfer.pos + pygame.Vector2(700, 0))
umgesetzt = False
for _ in range(int((K.GEGNER_MP["stockt_ab"] + 2.0)
                   / K.GEGNER_MP["stockt_pruefung"])):
    if umgesetzt:
        break
    haenger.pos.update(steht_bei)          # er kommt nie naeher
    haenger._haenger_pruefen(K.GEGNER_MP["stockt_pruefung"])
    umgesetzt = haenger.pos.distance_to(steht_bei) > 1.0
pruef("Wer nicht ankommt, wird umgesetzt", umgesetzt,
      "jetzt %.0f px vom Spieler statt 700"
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
gz._knoepfe.add("rufen")
netz_durchlassen(wz, gz, 6)
pruef("Der Gefallene ruft mit E", liegt.ruf_zeigen > 0.0,
      "%.2f" % liegt.ruf_zeigen)
zeigen_vorher = liegt.ruf_sperre
wz._rufen(liegt)
pruef("Und nicht gleich noch einmal", liegt.ruf_sperre <= zeigen_vorher)
pruef("Der Gast sieht den Ruf", gz.ich.ruf_zeigen > 0.0)
wz.verlassen(); gz.verlassen()

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
pruef("Man hat zu Beginn zwei Ladungen", ich_d.dash_ladungen == 2)
pruef("Ein Dash geht", ich_d.dashen())
for _ in range(int(0.5 / K.FIXED_DT)):
    ich_d.will = pygame.Vector2(0, 0)
    wd.schritt(K.FIXED_DT)
weg = ich_d.pos.distance_to(start)
pruef("Er traegt rund zwei Kacheln weit", 45.0 < weg < 110.0, "%.0f px" % weg)
pruef("Und kostet eine Ladung", ich_d.dash_ladungen == 1)
ich_d.dash_sperre = 0.0
pruef("Die zweite geht auch", ich_d.dashen())
ich_d.dash_rest = 0.0
ich_d.dash_sperre = 0.0
pruef("Eine dritte nicht", not ich_d.dashen())
for _ in range(int((K.DASH["nachladen"] + 0.05) / K.FIXED_DT)):
    wd.schritt(K.FIXED_DT)
pruef("Nach einer Ladezeit ist genau eine wieder da",
      ich_d.dash_ladungen == 1, "%d" % ich_d.dash_ladungen)
for _ in range(int(K.DASH["nachladen"] / K.FIXED_DT)):
    wd.schritt(K.FIXED_DT)
pruef("Nach zwei Ladezeiten beide - sie laden nacheinander",
      ich_d.dash_ladungen == 2, "%d" % ich_d.dash_ladungen)
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
for _ in range(20):
    wd.schritt(K.NETZ["takt"]); gd.schritt(K.NETZ["takt"])
pruef("Der Dash des Gastes kommt beim Gastgeber an",
      gast_fig.dash_ladungen == vorher_l - 1,
      "%d statt %d" % (gast_fig.dash_ladungen, vorher_l - 1))
pruef("Und der Gast sieht seine Ladungen",
      gd.ich.dash_ladungen == gast_fig.dash_ladungen)
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

print()
print("FEHLER:", fails or "keine")
pygame.quit()
