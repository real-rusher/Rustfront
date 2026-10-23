# -*- coding: utf-8 -*-
"""
Verhaltenstests der Bots (seit 0.34.52): ganze Szenen im Testmodus, jede
mit mehreren Seeds, gemessen wird, was die Bots tun - nicht, wie sie es
intern rechnen.

Gebaut, weil der Besitzer meldete: "viele von den Systemen funktionieren
einfach noch nicht richtig ... kannst du wirklich auch gerne mega viele
Test-Suites schreiben, um zu sehen, dass das Verhalten auch funktioniert."

    python tests/test_verhalten.py

Am Ende steht "FEHLER: keine" oder die Liste dessen, was nicht hielt.
"""
import math
import os
import random
import sys
import time

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pygame  # noqa: E402

from dustfront import config as K  # noqa: E402
from dustfront import testmodus as TM  # noqa: E402
from dustfront import bot_goap as BG  # noqa: E402
from dustfront import bots as BO  # noqa: E402
from dustfront.core import App  # noqa: E402
from dustfront import entities as ENT  # noqa: E402
from dustfront.entities import Geschoss  # noqa: E402

import werkzeug_aufnahme as W  # noqa: E402

app = App("verhalten", None, headless=True)
fails = []
DT = K.FIXED_DT


def pruef(text, ok, zusatz=""):
    print(("  ok    " if ok else "FEHLER  ") + text + (("   " + zusatz) if zusatz else ""))
    if not ok:
        fails.append(text)


def neu(seed):
    """Ein frischer Testmodus wie fuer eine Aufnahme, mit festem Zufall."""
    random.seed(seed)
    tm = TM.Testmodus(app, karte="staubtal")
    tm._bot_rnd.seed(seed)            # Merkmale, Namen, Aufstellung: jedes Mal dieselben
    ENT.RND.seed(seed)                # Streuung der Schuesse: unabhaengig vom Abschnitt davor
    tm.wiedereinstieg = False
    tm.verwundete_setzen(True)
    return tm


def laufen(tm, sekunden, je_schritt=None):
    for _ in range(int(sekunden / DT)):
        tm.schritt(DT)
        if je_schritt is not None:
            je_schritt()


class Schuesse:
    """Zaehlt jedes Geschoss, das ein Wesen aus `schuetzen` neu abfeuert -
    mit Ort und Richtung beim Abschuss."""

    def __init__(self, tm, schuetzen):
        self.tm = tm
        self.schuetzen = set(id(s) for s in schuetzen)
        # Die Wesen selbst festhalten, nicht nur ihre id(): ein verschwundenes
        # Geschoss gibt sonst seine Nummer frei, und ein neues mit derselben
        # wurde uebersehen (unter Python 3.8 oft).
        self.gesehen = {id(w): w for w in tm.welt.wesen}
        self.liste = []

    def schritt(self):
        for w in self.tm.welt.wesen:
            if id(w) in self.gesehen:
                continue
            self.gesehen[id(w)] = w
            if isinstance(w, Geschoss) and id(getattr(w, "von", None)) in self.schuetzen:
                self.liste.append((self.tm.welt.zeit, w.von, pygame.Vector2(w.pos),
                                   pygame.Vector2(1, 0).rotate(w.winkel)))


def abstand_zur_strecke(p, a, b):
    ab = b - a
    if ab.length_squared() < 1e-6:
        return p.distance_to(a)
    t = max(0.0, min(1.0, (p - a).dot(ab) / ab.length_squared()))
    return p.distance_to(a + ab * t)


def anteil(liste):
    return sum(1 for x in liste if x) / max(1, len(liste))


SEEDS = (11, 12, 13, 14, 15)


# ══════════════════════════════════════════════════════════════════
def nach_der_schlacht():
    print("\n-- Nach der Schlacht: die andere Seite liegt")
    schuesse_danach, denken_liegend, zeiten = [], [], []
    for seed in SEEDS:
        tm = neu(seed)
        tx, ty, v = W.flaeche(tm, random.Random(seed), 20, 11)
        rot = [tm.bot_setzen(v(14, 3 + 2 * i), 0, {"team": 0, "hirn": "goap"}) for i in range(4)]
        blau = [tm.bot_setzen(v(4, 3 + 2 * i), 0, {"team": 1, "hirn": "goap"}) for i in range(4)]
        W.kennen(rot, blau, tm)
        W.kennen(blau, rot, tm)
        laufen(tm, 1.0)
        for b in blau:
            if b.lebt and not b.am_boden:
                tm.toeten(b)
        zaehler = Schuesse(tm, rot)
        gefallen = tm.welt.zeit
        gedacht = {"n": 0}
        alt = BG.GoapHirn.fuehlen

        def fuehlen(self, alt=alt, gedacht=gedacht, blau=blau):
            if self.k in blau:
                gedacht["n"] += 1
            return alt(self)

        BG.GoapHirn.fuehlen = fuehlen
        t0 = time.perf_counter()
        laufen(tm, 8.0, zaehler.schritt)
        zeiten.append(time.perf_counter() - t0)
        BG.GoapHirn.fuehlen = alt
        # Bis er das naechste Mal hinsieht (takt), darf noch eine Kugel fliegen.
        frist = K.BOTS["takt"] + 0.1
        schuesse_danach.append(sum(1 for z, *_ in zaehler.liste if z - gefallen > frist))
        denken_liegend.append(gedacht["n"])
        tm.verlassen()
    pruef("Liegt die andere Seite ganz, schiesst keiner mehr",
          all(n == 0 for n in schuesse_danach), str(schuesse_danach))
    pruef("... und wer liegt, denkt nicht (kein fuehlen)", all(n == 0 for n in denken_liegend), str(denken_liegend))

    # Die Last: was ein Liegender selbst kostet (sein Denken und sein
    # Schritt), verglichen mit einem, der steht - gemeldet: "die Framerate
    # geht oft runter, wenn die eine Partei quasi vollstaendig verwundet ist".
    # Gemessen je Figur, nicht die ganze Szene: was die Stehenden tun,
    # haengt davon ab, was sie hoeren, und schwankte von Lauf zu Lauf.
    from dustfront.mehrspieler import Kaempfer

    def last(trupps, seed):
        tm = neu(seed)
        tx, ty, v = W.flaeche(tm, random.Random(seed), 22, 12)
        if trupps:
            a = tm.trupp_setzen(v(18, 6), 0, {"groesse": 6, "team": 0, "fuehrer": "funk", "mischung": "gemischt"})
            b = tm.trupp_setzen(v(4, 6), 0, {"groesse": 6, "team": 1, "fuehrer": "funk", "mischung": "gemischt"})
            rot, blau = a.mitglieder, b.mitglieder
        else:
            rot = [tm.bot_setzen(v(16, 3 + 2 * i), 0, {"team": 0, "hirn": "goap"}) for i in range(4)]
            blau = [tm.bot_setzen(v(3 + (i % 2) * 3, 1 + i), 0, {"team": 1, "hirn": "goap"}) for i in range(8)]
        W.kennen(rot, blau, tm)
        W.kennen(blau, rot, tm)
        laufen(tm, 0.5)
        for x in blau:
            if x.lebt and not x.am_boden:
                tm.toeten(x)
        laufen(tm, 0.5)
        zeit = {True: 0.0, False: 0.0}
        zahl = {True: 0, False: 0}
        alt_schritt, alt_eingabe = Kaempfer.schritt, BO.BotHirn.eingabe

        def gemessen(alt, figur):
            def f(self, *a):
                k = figur(self)
                liegt = bool(getattr(k, "am_boden", False))
                t0 = time.perf_counter()
                r = alt(self, *a)
                zeit[liegt] += time.perf_counter() - t0
                zahl[liegt] += 1
                return r
            return f

        Kaempfer.schritt = gemessen(alt_schritt, lambda s: s)
        BO.BotHirn.eingabe = gemessen(alt_eingabe, lambda s: s.k)
        try:
            laufen(tm, 4.0)
        finally:
            Kaempfer.schritt, BO.BotHirn.eingabe = alt_schritt, alt_eingabe
        tm.verlassen()
        return zeit, zahl

    for trupps, text in ((False, "Ein Liegender"), (True, "Ein Liegender im Trupp")):
        zeit, zahl = {True: 0.0, False: 0.0}, {True: 0, False: 0}
        for seed in SEEDS[:3]:
            z, n = last(trupps, seed)
            for x in (True, False):
                zeit[x] += z[x]
                zahl[x] += n[x]
        liegt = zeit[True] / max(1, zahl[True])
        steht = zeit[False] / max(1, zahl[False])
        pruef("%s kostet je Bild hoechstens ein Fuenftel von einem, der steht" % text,
              zahl[True] > 0 and liegt <= steht * 0.2,
              "%.4f ms / %.4f ms (x%.2f)" % (liegt * 1e3, steht * 1e3, liegt / max(1e-9, steht)))


# ══════════════════════════════════════════════════════════════════
def kein_fehlfeuer():
    print("\n-- Kein Feuer ins Leere, auf Geraeusche, auf Kameraden")
    leer, kamerad = [], []
    for seed in SEEDS:
        # Er hoert nur einen Schuss - sieht aber niemanden.
        tm = neu(seed)
        tx, ty, v = W.flaeche(tm, random.Random(seed), 20, 11)
        b = tm.bot_setzen(v(14, 5), 0, {"team": 0, "hirn": "goap"})
        zaehler = Schuesse(tm, [b])

        def hoeren(tm=tm, v=v):
            g = tm.__dict__.setdefault("_bot_geraeusche", [])
            if int(tm.welt.zeit / DT) % 60 == 0:
                g.append((v(2, 5), 0, tm.welt.zeit, "fremd", 900.0))

        laufen(tm, 5.0, lambda: (hoeren(), zaehler.schritt()))
        leer.append(len(zaehler.liste))
        tm.verlassen()

        # Ein Kamerad steht in der Schusslinie.
        tm = neu(seed)
        tx, ty, v = W.flaeche(tm, random.Random(seed), 20, 11)
        a = tm.bot_setzen(v(15, 5), 0, {"team": 0, "hirn": "goap", "waffe": "sturm"})
        a.unverwundbar = 1e9
        mitte = tm.puppe_setzen(v(9, 5), 0, {"team": 0, "leben": 10.0})
        mitte.unverwundbar = 1e9
        ziel = tm.puppe_setzen(v(3, 5), 0, {"team": 1, "leben": 10.0})
        ziel.unverwundbar = 1e9
        zaehler = Schuesse(tm, [a])
        laufen(tm, 4.0, zaehler.schritt)
        durch = [1 for _z, _w, p, r in zaehler.liste
                 if abstand_zur_strecke(mitte.pos, p, p + r * p.distance_to(ziel.pos)) < 14.0]
        kamerad.append(len(durch))
        tm.verlassen()
    pruef("Wer nur einen Schuss hoert und niemanden sieht, schiesst nicht ins Leere",
          all(n == 0 for n in leer), str(leer))
    pruef("Steht ein Kamerad in der Schusslinie, schiesst er nicht durch ihn hindurch",
          all(n == 0 for n in kamerad), str(kamerad))


# ══════════════════════════════════════════════════════════════════
def luecke(tm, k):
    """Wie viele Pixel zwischen dem Rand der Figur und der naechsten festen
    Kachel frei sind (negativ: sie beruehrt sie schraeg)."""
    T = K.TILE
    e = tm.welt.ebene(k.ebene)
    cx, cy = int(k.pos.x // T), int(k.pos.y // T)
    best = 1e9
    for ty in range(cy - 3, cy + 4):
        for tx in range(cx - 3, cx + 4):
            if not K.KACHELN[e.kachel(tx, ty)]["fest"]:
                continue
            nx = max(tx * T, min(k.pos.x, (tx + 1) * T))
            ny = max(ty * T, min(k.pos.y, (ty + 1) * T))
            best = min(best, math.hypot(k.pos.x - nx, k.pos.y - ny) - k.radius)
    return best


def mitte_von(liste, sonst=99.0):
    return sorted(liste)[len(liste) // 2] if liste else sonst


def deckung_dicht():
    print("\n-- Dicht an die Deckung, wenn auf ihn geschossen wird")
    dicht, gedeckt_ende = [], []
    for seed in SEEDS:
        tm = neu(seed)
        tx, ty, v = W.flaeche(tm, random.Random(seed), 20, 11)
        W.setzen(tm, tx, ty, [(9, 4), (9, 5), (9, 6)], K.KISTE)
        b = tm.bot_setzen(v(13, 5), 0, {"team": 0, "hirn": "goap", "waffe": "sturm"})
        b.hirn.merkmale["mut"] = 0.2
        # Nicht unverwundbar: Treffer muss er spueren (Stress), sonst hat er
        # keinen Grund, sich zu decken. Viel Leben, damit er nicht faellt.
        b.max_leben = b.leben = 2000.0
        # Der Gegner schiesst wirklich - sonst hat er keinen Grund, sich zu
        # decken. Er geht nicht zu Boden.
        g = tm.bot_setzen(v(3, 5), 0, {"team": 1, "hirn": "goap", "waffe": "sturm"})
        g.hirn.merkmale["mut"] = 0.9
        g.unverwundbar = 1e9
        W.kennen([b], [g], tm)
        W.kennen([g], [b], tm)
        proben = []

        def messen(tm=tm, b=b, proben=proben):
            if int(tm.welt.zeit / DT) % 12 != 0 or not b.hirn._in_deckung():
                return
            if b.hirn._lehnen is not None and b.hirn._lehnen["phase"] != "drin":
                return
            proben.append(luecke(tm, b))

        laufen(tm, 10.0, messen)
        if len(proben) >= 3:
            dicht.append(mitte_von(proben))
        gedeckt_ende.append(len(proben) >= 3)
        tm.verlassen()
    # Die Luecke zaehlt nur, wo er in Deckung war - ob er es war, prueft
    # die naechste Zeile.
    pruef("Wer in Deckung geht, steht dicht dahinter (Mitte der Proben hoechstens 12 px Luecke)",
          len(dicht) >= 3 and anteil([d <= 12.0 for d in dicht]) >= 0.75, "Luecken %s" % [round(d) for d in dicht])
    pruef("... und er ist ueberhaupt in Deckung gegangen", anteil(gedeckt_ende) >= 0.8, str(gedeckt_ende))


# ══════════════════════════════════════════════════════════════════
def abschnitte():
    print("\n-- Geknickte Front (die Szene aus der Aufnahme): jeder Abschnitt schiesst auf seine Gruppe")
    treu, beide, dicht, wechsel = [], [], [], []
    for seed in SEEDS:
        tm = neu(seed)
        titel, leute, _f, dauer, _z = W.szene_abschnitte(tm, random.Random(seed))
        trupp = leute[0].hirn.trupp
        feinde = [k for k in tm.kaempfer.values() if k.team == 1]
        ziele, luecken, gruppe_von = [], [], {}
        st = {"wechsel": 0}

        def gruppe(ort, feinde=feinde):
            # Die Gruppe, deren Mitte dem Blickpunkt am naechsten ist.
            nah = min(feinde, key=lambda q: q.pos.distance_to(ort))
            return "W" if nah.pos.x < min(q.pos.x for q in feinde) + 64 else "N"

        def merken(tm=tm, trupp=trupp, ziele=ziele, luecken=luecken, gruppe_von=gruppe_von, st=st):
            if trupp.abschnitte < 2:
                return
            for m in trupp.lebende():
                bl = trupp.blick_fuer(m)
                if bl is None:
                    continue
                g = gruppe(bl)
                if gruppe_von.get(m.nummer, g) != g:
                    st["wechsel"] += 1
                gruppe_von[m.nummer] = g
                z = m.hirn.ziel
                if m.feuert and z is not None:
                    ziele.append((gruppe(z.pos) == g, gruppe(z.pos)))
                if tm.welt.zeit > dauer * 0.5 and int(tm.welt.zeit / DT) % 30 == 0:
                    luecken.append(luecke(tm, m))

        laufen(tm, dauer, merken)
        treu.append(anteil([a for a, _g in ziele]) if ziele else 0.0)
        beide.append(len(set(g for _a, g in ziele)) == 2)
        dicht.append(mitte_von(luecken))
        wechsel.append(st["wechsel"])
        tm.verlassen()
    pruef("Wer zu einer Gruppe schaut, schiesst auf sie (wenigstens 90 Prozent)",
          anteil([t >= 0.9 for t in treu]) >= 0.8, str([round(t, 2) for t in treu]))
    pruef("... beide Gruppen bekommen Feuer", anteil(beide) >= 0.8, str(beide))
    pruef("... in der zweiten Haelfte stehen sie dicht an den Kisten (Mitte hoechstens 16 px)",
          anteil([d <= 16.0 for d in dicht]) >= 0.8, str([round(d) for d in dicht]))
    pruef("... und keiner wechselt dauernd den Abschnitt (hoechstens 3 Wechsel je Szene)",
          all(n <= 3 for n in wechsel), str(wechsel))


# ══════════════════════════════════════════════════════════════════
def bergen():
    print("\n-- Bergen: der Naechste zieht ihn hinter die Mauer, dort hilft er auf - die anderen bleiben in Deckung")
    from dustfront.trupp import sieht_durch_rauch
    gelungen, gedeckt, gezogen, naechster = [], [], [], []
    einer, andere_offen, werfer_offen = [], [], []
    reicht = max(K.BOTS["reichweite"].values())
    for seed in SEEDS:
        tm = neu(seed)
        tx, ty, v = W.flaeche(tm, random.Random(seed), 20, 11)
        W.setzen(tm, tx, ty, [(13, y) for y in range(2, 9)], K.WAND)
        trupp = tm.trupp_setzen(v(15, 5), 0, {"groesse": 4, "team": 0, "fuehrer": "funk", "mischung": "gemischt"})
        feinde = [tm.puppe_setzen(v(2, 4 + 2 * i), 0, {"team": 1, "leben": 10.0}) for i in range(2)]
        for f in feinde:
            f.unverwundbar = 1e9
        opfer = next(m for m in trupp.mitglieder if m is not trupp.fuehrer)
        opfer.pos.update(v(9, 5))
        opfer.vorher.update(opfer.pos)
        W.kennen(trupp.mitglieder, feinde, tm)
        laufen(tm, 1.0)
        tm.toeten(opfer)
        nah = sorted((m for m in trupp.lebende() if m is not opfer and m is not trupp.fuehrer),
                     key=lambda m: m.pos.distance_to(opfer.pos))[:1]
        st = {"zieh": 0, "zieher": None, "hilf_ort": None, "holen": set(), "werfer": set(), "offen": {}}

        def offen(m, tm=tm, feinde=feinde):
            # Offen ist, wen ein Gegner in Reichweite sieht und treffen kann.
            return any(f.pos.distance_to(m.pos) <= reicht and tm.welt.deckung(f.pos, m.pos, 0) == ""
                       and sieht_durch_rauch(tm.welt, f.pos, m.pos, 0) for f in feinde)

        def beobachten(trupp=trupp, opfer=opfer, st=st):
            for m in trupp.mitglieder:
                if m is opfer or m.am_boden:
                    continue
                a = m.hirn.gehirn.aktion.name if m.hirn.gehirn.aktion else ""
                if a in ("zum_kameraden", "kamerad_ziehen", "aufhelfen", "aufhelfen_offen") \
                        or m.zieht == opfer.nummer or m.hilft == opfer.nummer:
                    st["holen"].add(m.nummer)
                if a == "rauch_werfen":
                    st["werfer"].add(m.nummer)
                # Zum Feuerschutz darf er sich herauslehnen (seit 0.34.54,
                # gemeldet: "dass sie Gegner davon abhalten, die Person, die
                # gerade am Bergen ist, anzugreifen") - sonst nicht offen.
                lehnt = (m.hirn._lehnen is not None and m.hirn._lehnen["phase"] == "raus") or m.feuert
                if offen(m) and not lehnt:
                    st["offen"][m.nummer] = st["offen"].get(m.nummer, 0.0) + DT
                if m.zieht == opfer.nummer:
                    st["zieh"] += 1
                    st["zieher"] = st["zieher"] or m
                if m.hilft == opfer.nummer and st["hilf_ort"] is None:
                    st["hilf_ort"] = pygame.Vector2(opfer.pos)

        for _ in range(int(30.0 / DT)):
            tm.schritt(DT)
            beobachten()
            if opfer.lebt and not opfer.am_boden:
                break
        gelungen.append(opfer.lebt and not opfer.am_boden)
        # Gedeckt vor jedem, der ihn von dort aus treffen koennte - weiter
        # weg als jede Waffe reicht, schadet freie Sicht nicht.
        reicht = max(K.BOTS["reichweite"].values())
        gedeckt.append(st["hilf_ort"] is not None
                       and all(tm.welt.deckung(f.pos, st["hilf_ort"], 0) != ""
                               or f.pos.distance_to(st["hilf_ort"]) > reicht for f in feinde))
        gezogen.append(st["zieh"] * DT >= 1.0)
        naechster.append(st["zieher"] is not None and st["zieher"] in nah)
        einer.append(len(st["holen"]) == 1)
        andere_offen.append(max([t for n, t in st["offen"].items()
                                 if n not in st["holen"] and n not in st["werfer"]] or [0.0]))
        werfer_offen.append(max([st["offen"].get(n, 0.0) for n in st["werfer"]] or [0.0]))
        tm.verlassen()
    pruef("Der Verwundete steht nach hoechstens 30 Sekunden wieder (wenigstens 4 von 5)",
          anteil(gelungen) >= 0.8, str(gelungen))
    pruef("... aufgeholfen wird gedeckt vor jedem Gegner, der ihn treffen koennte", anteil(gedeckt) >= 0.8, str(gedeckt))
    pruef("... vorher wurde er wirklich gezogen (wenigstens eine Sekunde)", anteil(gezogen) >= 0.8, str(gezogen))
    pruef("... und gezogen hat der, der ihm am naechsten war (nicht der Anfuehrer)", anteil(naechster) >= 0.8, str(naechster))
    # Gemeldet (0.34.53): "alle Bots haben ihre Deckung verlassen, um zu
    # bergen" - das macht das Bergen zur Todesfalle.
    pruef("Nur einer holt ihn - nicht der ganze Trupp", all(einer), str(einer))
    pruef("... wer weder holt noch Rauch wirft, steht waehrenddessen nicht offen, ausser zum Feuern (hoechstens 0,5 s)",
          all(t <= 0.5 for t in andere_offen), str([round(t, 1) for t in andere_offen]))
    pruef("... und wer den Rauch wirft, steht nur kurz offen, ausser zum Feuern (hoechstens 3 s)",
          all(t <= 3.0 for t in werfer_offen), str([round(t, 1) for t in werfer_offen]))


# ══════════════════════════════════════════════════════════════════
def feuerschutz():
    print("\n-- Feuerschutz beim Bergen: ein Gegner, der schiesst - die anderen halten ihn nieder")
    # Gemeldet (0.34.54): "Wenn ich spiele, dann kann ich tatsaechlich einfach
    # einen anschiessen, bis er stirbt. Dann kommt ein anderer raus und ich
    # kann ihn einfach wieder anschiessen, werde dabei nicht beschossen."
    from dustfront.trupp import sieht_durch_rauch
    reicht = max(K.BOTS["reichweite"].values())
    je_s, nieder, offen_anteil = [], [], []
    for seed in SEEDS:
        tm = neu(seed)
        tx, ty, v = W.flaeche(tm, random.Random(seed), 20, 11)
        W.setzen(tm, tx, ty, [(13, y) for y in range(2, 9)], K.WAND)
        W.setzen(tm, tx, ty, [(14, 1), (14, 9)], K.KISTE)
        trupp = tm.trupp_setzen(v(15, 5), 0, {"groesse": 4, "team": 0, "fuehrer": "funk", "mischung": "gemischt"})
        # Der Gegner steht fuer den Spieler: er schiesst, und er faellt nicht.
        g = tm.bot_setzen(v(6, 2), 0, {"team": 1, "hirn": "goap", "waffe": "sturm"})
        g.unverwundbar = 1e9
        g.hirn.merkmale["mut"] = 0.9
        opfer = next(m for m in trupp.mitglieder if m is not trupp.fuehrer)
        opfer.pos.update(v(9, 5))
        opfer.vorher.update(opfer.pos)
        for m in trupp.mitglieder:
            m.max_leben = m.leben = 2000.0      # sie spueren Treffer, fallen aber nicht
        W.kennen(trupp.mitglieder, [g], tm)
        W.kennen([g], trupp.mitglieder, tm)
        laufen(tm, 1.0)
        tm.toeten(opfer)
        zaehler = Schuesse(tm, trupp.mitglieder)
        gort, st = [], {"nieder": 0.0, "offen": 0.0, "da": 0.0}
        for _ in range(int(20.0 / DT)):
            n = len(zaehler.liste)
            tm.schritt(DT)
            zaehler.schritt()
            gort += [pygame.Vector2(g.pos)] * (len(zaehler.liste) - n)
            if getattr(g.hirn, "unterdrueckt", 0.0) > 0.0:
                st["nieder"] += DT
            b = trupp.bergung or {}
            for m in trupp.lebende():
                if m is opfer or m.nummer in b.get("retter", ()):
                    continue
                st["da"] += DT
                lehnt = (m.hirn._lehnen is not None and m.hirn._lehnen["phase"] == "raus") or m.feuert
                if (not lehnt and g.pos.distance_to(m.pos) <= reicht and tm.welt.deckung(g.pos, m.pos, 0) == ""
                        and sieht_durch_rauch(tm.welt, g.pos, m.pos, 0)):
                    st["offen"] += DT
            if opfer.lebt and not opfer.am_boden:
                break
        dauer = max(1.0, tm.welt.zeit - 2.0)
        retter = set((trupp.bergung or {}).get("retter", ()))
        auf_ihn = [1 for (_z, w, p, r), go in zip(zaehler.liste, gort)
                   if w.nummer not in retter and abs((r.angle_to(go - p) + 180.0) % 360.0 - 180.0) < 15.0]
        je_s.append(len(auf_ihn) / dauer)
        nieder.append(st["nieder"] / dauer)
        offen_anteil.append(st["offen"] / max(1e-6, st["da"]))
        tm.verlassen()
    pruef("Die anderen schiessen auf den, der den Retter bedroht (im Schnitt wenigstens 0,8 Schuss je Sekunde, keiner unter 0,3)",
          sum(je_s) / len(je_s) >= 0.8 and min(je_s) >= 0.3, str([round(x, 2) for x in je_s]))
    pruef("... er ist dabei meist niedergehalten (wenigstens 40 Prozent der Zeit)",
          sum(nieder) / len(nieder) >= 0.4, str([round(x, 2) for x in nieder]))
    pruef("... und offen stehen sie nur zum Feuern - sonst hoechstens ein Viertel der Zeit",
          sum(offen_anteil) / len(offen_anteil) <= 0.25, str([round(x, 2) for x in offen_anteil]))


# ══════════════════════════════════════════════════════════════════
def mauern():
    print("\n-- Nicht durch Mauern: zwei Trupps, Mauern und Kisten dazwischen")
    # Gemeldet (0.34.54): "Bots versuchen oft durch Mauern zu schiessen" -
    # gemessen waren es 17 Prozent aller Bilder, in denen sie feuerten.
    zahl = {"wand": 0, "hindernis": 0, "frei": 0}
    alt = BO.BotHirn.eingabe

    def eingabe(self, dt):
        ein = alt(self, dt)
        k = self.k
        if ein.get("feuert") and k.waffe_daten.get("art") == "schuss":
            d = self.g.welt.deckung(k.pos, pygame.Vector2(ein["ziel"]), k.ebene)
            zahl[d or "frei"] += 1
        return ein

    BO.BotHirn.eingabe = eingabe
    try:
        for seed in SEEDS[:3]:
            tm = neu(seed)
            tx, ty, v = W.flaeche(tm, random.Random(seed), 24, 13)
            W.setzen(tm, tx, ty, [(12, y) for y in (2, 3, 4, 8, 9, 10)] + [(7, 6), (17, 6)], K.WAND)
            W.setzen(tm, tx, ty, [(9, 3), (15, 9)], K.KISTE)
            a = tm.trupp_setzen(v(20, 6), 0, {"groesse": 5, "team": 0, "fuehrer": "funk", "mischung": "gemischt"})
            b = tm.trupp_setzen(v(4, 6), 0, {"groesse": 5, "team": 1, "fuehrer": "funk", "mischung": "gemischt"})
            for m in a.mitglieder + b.mitglieder:
                m.max_leben = m.leben = 1500.0
            W.kennen(a.mitglieder, b.mitglieder, tm)
            W.kennen(b.mitglieder, a.mitglieder, tm)
            laufen(tm, 15.0)
            tm.verlassen()
    finally:
        BO.BotHirn.eingabe = alt
    pruef("Keiner feuert, wenn eine Mauer zwischen ihm und dem Punkt steht, auf den er zielt",
          zahl["wand"] == 0, str(zahl))
    pruef("... gefeuert wird trotzdem (das Gefecht findet statt)", zahl["frei"] > 500, str(zahl))


# Einzeln: python tests/test_verhalten.py bergen abschnitte
TEILE = [nach_der_schlacht, kein_fehlfeuer, deckung_dicht, abschnitte, bergen, feuerschutz, mauern]
NUR = sys.argv[1:]
for teil in TEILE:
    if not NUR or teil.__name__ in NUR:
        teil()
print()
print("FEHLER:", fails or "keine")
pygame.quit()
