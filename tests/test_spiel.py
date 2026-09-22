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

pruef("Hotbar hat sieben Plaetze", len(held.waffen) == 7,
      "%d" % len(held.waffen))
pruef("Alle sieben Waffen sind bekannt",
      all(w in K.WAFFEN for w in held.waffen))
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

# Mausrad verschiebt die Ansicht, wie im Einzelspieler
host.blick = 0
e.neues_bild(); e.rad = 1
host.knoepfe_sammeln()
e.neues_bild(); e.rad = 0
host.schritt(K.FIXED_DT)
pruef("Das Mausrad verschiebt die Ebenenansicht", host.blick == 1,
      "Ebene %d" % host.blick)

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
pruef("Rauch benutzt nur die Farben aus der Tabelle",
      len(farben) <= len(K.RAUCH["farben"]), "%d Farben" % len(farben))
pruef("Und jeder Block deckt voll", all(c[3] == 255 for c in farben))
# Blockig heisst: jede Kante sitzt auf dem Raster. Ein weicher Verlauf
# haette Kanten ueberall - und genau so etwas hat in einem Spiel aus
# Kacheln nichts zu suchen.
daneben = 0
zeile = bild_wolke.get_height() // 2
vor = None
for px in range(bild_wolke.get_width()):
    c = tuple(bild_wolke.get_at((px, zeile)))
    if vor is not None and c != vor and (px + wolke_ecke[0]) % K.RAUCH["block"]:
        daneben += 1
    vor = c
pruef("Jede Rauchkante sitzt auf dem Blockraster", daneben == 0,
      "%d daneben" % daneben)
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

# Der Gast faellt und wird nicht aufgehoben: seine Mannschaft ist leer,
# die Runde geht an die andere.
gast_k.unverwundbar = 0.0
gast_k.schaden(999, None, None)
pruef("Wer faellt, liegt erst einmal am Boden",
      gast_k.am_boden and gast_k.lebt)
pruef("Am Boden ist die Runde noch nicht entschieden",
      w.teampunkte == [0, 0], str(w.teampunkte))
gast_k.boden_rest = 0.0
w._revive(K.FIXED_DT)
w._tote_abrechnen(K.FIXED_DT)
pruef("Laeuft die Zeit am Boden ab, ist man fuer die Runde raus",
      gast_k.raus and not gast_k.lebt)
w._runden(K.FIXED_DT)
pruef("Die Runde geht an die Mannschaft, die noch steht",
      w.teampunkte[0] == 1, str(w.teampunkte))
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

# Genug Rundensiege beenden das Gefecht.
w.teampunkte[0] = K.VERSUS["runden_bis"] - 1
gast_k.lebt = False
gast_k.raus = True
w._runden(K.FIXED_DT)
pruef("Genug Rundensiege beenden das Gefecht",
      w.vorbei and w.sieger_team == 0,
      "%s, Sieger %d" % (w.teampunkte, w.sieger_team))
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
    pruef("%s hat einen echten Tonausgang" % wer,
          not noch_leer(wie.welt.klang) and wie.welt.klang == app.klaenge.spielen)
    pruef("%s spuert Treffer in der Kamera" % wer,
          wie.welt.ruckeln == wie.kamera.stossen)
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
pruef("Der Gast nur weiterspielen oder gehen",
      gast_eintraege == ["weiter", "raus"], str(gast_eintraege))
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
w.wunsch["runden_bis"] = 5
w.wunsch["schutz"] = False
w.kaempfer[0].abschuesse = 7
w._runde_neu()
pruef("Eine neue Runde uebernimmt die neuen Regeln",
      w.modus == "versus" and w.runden_bis == 5 and not w.schutz_an,
      "%s, bis %d, Schutz %s" % (w.modus, w.runden_bis, w.schutz_an))
pruef("Und setzt die Punkte zurueck",
      w.kaempfer[0].abschuesse == 0 and w.teampunkte == [0, 0])
netz_durchlassen(w, ga, 20)
pruef("Der Gast spielt die neuen Regeln mit",
      ga.modus == "versus" and ga.runden_bis == 5 and not ga.schutz_an,
      "%s, bis %d, Schutz %s" % (ga.modus, ga.runden_bis, ga.schutz_an))
w.verlassen(); ga.verlassen()

# Rundenzahl und Mannschaftswunsch beim Starten
w, ga = gefechtspaar("versus", runden=2, team=1)
pruef("Die Rundenzahl laesst sich beim Aufmachen waehlen",
      w.runden_bis == 2, "%d" % w.runden_bis)
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
      wirt_k.bild == "spieler_boden", wirt_k.bild)
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
w.welt.klang = lambda name, laut=1.0: gehoert.append(name)
wirt_k.ebene = 2
wirt_k.sturz_hoehe = 180.0
wirt_k.aufschlag()
pruef("Ein Aufschlag macht einen Staubring", len(w.welt.ringe) == 1)
pruef("Und einen Ton", "sturz" in gehoert, str(gehoert))
w.welt.klang = app.klaenge.spielen

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

# Ein Gast, der abbricht, darf den Gastgeber nicht mitreissen
verbindung.schliessen()
for _ in range(6):
    host.schritt(K.NETZ["takt"])
pruef("Gastgeber laeuft weiter, wenn ein Gast geht",
      len(host.kaempfer) == 1, "%d uebrig" % len(host.kaempfer))
host.verlassen()

print()
print("FEHLER:", fails or "keine")
pygame.quit()
