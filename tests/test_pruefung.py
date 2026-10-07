# -*- coding: utf-8 -*-
"""Pruefungen ueber das ganze Projekt, seit 0.34.1.

Entstanden nach einer Runde Aenderungen mit anderen KI-Assistenten. Jede
Pruefung hier faengt einen Fehler, der dabei durchgerutscht war:

* tools/soundboard.py startete nicht (halb geloeschte Zeile).
* Drei der sechs STAUBTAL-Aufzuege lagen im Fels, das Suedwest-Plateau
  war unerreichbar - mitsamt zwei Spawnstellen.
* Hausturen lagen einzeln im Fels (Haeuser auf der falschen Ebene).
* Der Brecher war breiter als eine Kachel und kam durch keine Tuer.
* Gegner liefen zum ersten statt zum naechsten Aufzug.
* Die MG-Salve spielte ihre Ein-Sekunden-Aufnahme je Geschoss.
* Die Hotbar ragte mit zehn Waffen in den Waffenkasten.

Laeuft ohne Fenster, wie die anderen Tests:  python tests/test_pruefung.py
"""
from __future__ import annotations

import os
import sys
from collections import deque
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
WURZEL = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WURZEL))

import pygame  # noqa: E402

from dustfront import config as K  # noqa: E402
from dustfront import world as W  # noqa: E402

fails = []


def pruef(t, ok, zusatz=""):
    print(("  ok  " if ok else "FAIL  ") + t
          + (("   " + str(zusatz)) if zusatz else ""))
    if not ok:
        fails.append(t)


# ── 1. Jede Python-Datei laesst sich uebersetzen ──────────────────────
# Mit dem Python, das gerade laeuft. Wer das unter 3.8 aufruft, prueft
# damit auch, dass keine neuere Syntax hineingeraten ist.
print("\n-- Python-Dateien")
kaputt = []
anzahl = 0
for pfad in sorted(WURZEL.rglob("*.py")):
    if any(teil in ("__pycache__", ".git") for teil in pfad.parts):
        continue
    anzahl += 1
    try:
        compile(pfad.read_text(encoding="utf-8"), str(pfad), "exec")
    except SyntaxError as fehler:
        kaputt.append("%s:%s %s" % (pfad.relative_to(WURZEL), fehler.lineno,
                                     fehler.msg))
pruef("Alle %d Python-Dateien sind gueltig (Python %d.%d)"
      % (anzahl, sys.version_info[0], sys.version_info[1]), not kaputt,
      "; ".join(kaputt))


# ── 2. Karten: alles, was zaehlt, ist erreichbar ─────────────────────
def _geh(e, tx, ty):
    return e.begehbar(tx, ty) and not e.loch(tx, ty)


def erreichbar(welt, start):
    """Alle (ebene, tx, ty), die man von `start` aus zu Fuss und mit E
    an Treppen und Aufzuegen erreicht."""
    gesehen = {start}
    offen = deque([start])
    while offen:
        i, x, y = offen.popleft()
        e = welt.ebenen[i]
        nachbarn = [(i, x + 1, y), (i, x - 1, y), (i, x, y + 1), (i, x, y - 1)]
        rel = e.daten(x, y).get("treppe")
        if rel is not None and 0 <= i + rel < len(welt.ebenen):
            nachbarn.append((i + rel, x, y))
        for n in nachbarn:
            if n not in gesehen and _geh(welt.ebenen[n[0]], n[1], n[2]):
                gesehen.add(n)
                offen.append(n)
    return gesehen


print("\n-- Karten")
for name in W.karten_liste():
    welt, kopf = W.karte_lesen(name)
    pruef("%s laesst sich lesen" % name, welt is not None)
    if welt is None:
        continue
    # Start: die erste Marke, sonst `start:` aus dem Kopf, sonst die erste
    # begehbare Kachel unten.
    start = None
    for i, e in enumerate(welt.ebenen):
        for marke, stellen in sorted(e.marken.items()):
            if marke != "Z" and start is None:
                start = (i, int(stellen[0].x // K.TILE), int(stellen[0].y // K.TILE))
    if start is None and kopf.get("start"):
        sx, sy = (int(v) for v in str(kopf["start"]).split()[:2])
        start = (0, sx, sy)
    if start is None or not _geh(welt.ebenen[start[0]], start[1], start[2]):
        e0 = welt.ebenen[0]
        start = next((0, x, y) for y in range(e0.hoehe) for x in range(e0.breite)
                     if _geh(e0, x, y))
    da = erreichbar(welt, start)

    # Jede Treppe und jeder Aufzug: erreichbar, und am Ziel Boden.
    treppen, ohne_ziel, abseits = 0, [], []
    for i, e in enumerate(welt.ebenen):
        for ty in range(e.hoehe):
            for tx in range(e.breite):
                rel = e.daten(tx, ty).get("treppe")
                if rel is None:
                    continue
                treppen += 1
                z = i + rel
                if not (0 <= z < len(welt.ebenen)) or not _geh(welt.ebenen[z], tx, ty):
                    ohne_ziel.append((i, tx, ty))
                if (i, tx, ty) not in da:
                    abseits.append((i, tx, ty))
    pruef("%s: jede Treppe fuehrt auf Boden" % name, not ohne_ziel, ohne_ziel[:6])
    pruef("%s: jede der %d Treppen ist erreichbar" % (name, treppen),
          not abseits, abseits[:6])

    # Spawnstellen und Kreise: dort, wo man hinkommt.
    marken_weg = []
    for i, e in enumerate(welt.ebenen):
        for marke, stellen in e.marken.items():
            for p in stellen:
                k = (i, int(p.x // K.TILE), int(p.y // K.TILE))
                if k not in da:
                    marken_weg.append((marke,) + k)
    pruef("%s: jede Spawnstelle und jeder Kreis ist erreichbar" % name,
          not marken_weg, marken_weg[:6])

    # Kein einzelnes Feld im Fels: ein begehbares Feld, um das herum
    # alles fest ist, ist immer ein Kartenfehler. Ausnahme: eine Treppe
    # (die Kabine eines Aufzugs ist ja nur eine Kachel).
    einzeln = []
    for i, e in enumerate(welt.ebenen):
        for ty in range(e.hoehe):
            for tx in range(e.breite):
                if not _geh(e, tx, ty) or e.daten(tx, ty).get("treppe") is not None:
                    continue
                if not any(_geh(e, a, b) for a, b in ((tx + 1, ty), (tx - 1, ty),
                                                      (tx, ty + 1), (tx, ty - 1))):
                    einzeln.append((i, tx, ty))
    pruef("%s: kein einzelnes Bodenfeld mitten im Fels" % name,
          not einzeln, einzeln[:8])


# ── 3. Gegner passen durch eine Tuer ─────────────────────────────────
print("\n-- Gegner")
zu_breit = [(art, K.gegner_daten(art)["radius"]) for art in K.GEGNER
            if not K.ist_boss(art)
            and K.gegner_daten(art)["radius"] >= K.TILE / 2]
pruef("Jeder Gegner, der Treppen nimmt, passt durch eine Kachel breite Tuer",
      not zu_breit, zu_breit)


# ── 4. Klaenge ───────────────────────────────────────────────────────
print("\n-- Klaenge")
import tempfile  # noqa: E402

from dustfront.audio import Klaenge  # noqa: E402

leer = Path(tempfile.mkdtemp())
(leer / K.ASSETS["sfx"]).mkdir(parents=True)
try:
    pygame.mixer.init(44100, -16, 2)
except pygame.error:
    pass
kl = Klaenge(leer)
if kl.ok:
    stumm = [n for n in K.KLANG_NAMEN if not kl.klang(n)]
    pruef("Jeder Klang hat einen Rueckfall aus dem Code, auch ohne Dateien",
          not stumm, ", ".join(stumm))
else:
    print("  --  ohne Tonausgabe uebersprungen")


class _Zaehler:
    """Eine Welt, die nur mitschreibt, welche Klaenge sie spielt."""

    def __init__(self):
        self.klaenge = []
        self.welt = W.Welt([W.Ebene.aus_text(["...."], 0)])
        self.welt.klang = lambda name, *a, **k: self.klaenge.append(name)


class _Schuetze:
    modus = "salve"
    salve_rest = 0


z = _Zaehler()
schuetze = _Schuetze()
salve = K.WAFFEN["lmg"]["modus_daten"]["salve"]["salve"]
for rest in range(salve - 1, -1, -1):        # so zaehlt eine Salve herunter
    schuetze.salve_rest = rest
    z.welt.schussknall(pygame.Vector2(10, 10), 0.0, 0, "lmg", schuetze)
pruef("Die MG-Salve klingt einmal je Abzug, nicht je Geschoss",
      z.klaenge.count("lmg_salve") == 1, z.klaenge)
z = _Zaehler()
schuetze.modus = "dauer"
for _ in range(3):
    z.welt.schussknall(pygame.Vector2(10, 10), 0.0, 0, "lmg", schuetze)
pruef("Im Dauerfeuer klingt jeder Schuss", z.klaenge.count("lmg_dauer") == 3,
      z.klaenge)


# ── 5. Anzeige ───────────────────────────────────────────────────────
print("\n-- Anzeige")
from dustfront import anzeige as AZ  # noqa: E402

hud = AZ.Anzeige(None)
ueber = [n for n in range(1, len(K.HOTBAR) + 2)
         if hud.hotbar_rechteck(n).colliderect(AZ.LINKS)
         or hud.hotbar_rechteck(n).colliderect(AZ.RECHTS)]
pruef("Die Hotbar ueberdeckt die Kaesten nicht, auch mit einer Waffe mehr",
      not ueber, "bei %s Waffen" % ueber)


# ── 6. Wegfindung auf STAUBTAL: der naechste Aufzug, und jeder geht ──
print("\n-- Aufzuege auf STAUBTAL")
from dustfront import netz  # noqa: E402
from dustfront.core import App  # noqa: E402
from dustfront.mehrspieler import Gefecht, KampfGegner  # noqa: E402

app = App("pruefung", None, headless=True)


def _freier_port(ab=52900):
    import socket
    port = ab
    while True:
        port += 1
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            s.bind(("", port))
            return port
        except OSError:
            continue
        finally:
            s.close()


w = Gefecht(app, "WIRT", gastgeber=netz.Gastgeber(_freier_port()),
            modus="pve", karte="staubtal", seed=3)
for _ in range(30):
    w.schritt(K.NETZ["takt"])
w.pause_rest = 1e9
netz_w = w.welt.wege


def _gerade(e, tx, ty, r_von, r_bis):
    """Ein Feld r Kacheln geradeaus von der Treppe, mit freiem Weg."""
    for dx, dy in ((0, 1), (0, -1), (1, 0), (-1, 0)):
        for r in range(r_von, r_bis):
            if all(_geh(e, tx + dx * i, ty + dy * i) for i in range(1, r + 1)):
                return tx + dx * r, ty + dy * r
    return None


# Wer direkt vor einem Aufzug steht, nimmt diesen - nicht den ersten der
# Karte. Bis 0.34.0 liefen alle zum westlichsten.
falsch = []
for nr, (eb, tx, ty, ziel) in enumerate(netz_w.treppen):
    vor = _gerade(w.welt.ebene(eb), tx, ty, 2, 3)
    oben = _gerade(w.welt.ebene(ziel), tx, ty, 3, 5)
    if not vor or not oben:
        continue
    gewaehlt = netz_w.naechste_treppe(
        eb, pygame.Vector2((vor[0] + .5) * K.TILE, (vor[1] + .5) * K.TILE),
        ziel, pygame.Vector2((oben[0] + .5) * K.TILE, (oben[1] + .5) * K.TILE))
    if gewaehlt != nr:
        falsch.append(((eb, tx, ty), netz_w.treppen[gewaehlt][:3]
                       if gewaehlt is not None else None))
pruef("Vor einem Aufzug waehlt der Gegner diesen Aufzug", not falsch, falsch[:4])

# Und jeder Aufzug traegt Laeufer und Brecher, hinauf wie hinunter.
haengt = []
for (eb, tx, ty, ziel) in netz_w.treppen:
    for art in ("brecher", "laeufer"):
        for x in list(w.welt.wesen):
            if isinstance(x, KampfGegner):
                x.lebt = False
        w.welt.wesen = [x for x in w.welt.wesen if x.lebt]
        w.gegner_offen = []
        w.welle_rest = []
        start = _gerade(w.welt.ebene(eb), tx, ty, 3, 4)
        ziel_k = _gerade(w.welt.ebene(ziel), tx, ty, 5, 7)
        if not start or not ziel_k:
            haengt.append((art, eb, tx, ty, "kein Platz davor"))
            continue
        ziel_p = w.welt.landeplatz(pygame.Vector2((ziel_k[0] + .5) * K.TILE,
                                                  (ziel_k[1] + .5) * K.TILE),
                                   9, ziel)
        g = KampfGegner(pygame.Vector2((start[0] + .5) * K.TILE,
                                       (start[1] + .5) * K.TILE), art, eb, w)
        g.wartet = 0.0
        w.welt.dazu(g)
        w.gegner_offen.append(g)
        oben_an = False
        for _ in range(int(10.0 / K.FIXED_DT)):
            for k in w.kaempfer.values():
                k.leben = k.max_leben
                k.ebene = ziel
                k.pos.update(ziel_p)
                k.tempo.update(0, 0)
            w.schritt(K.FIXED_DT)
            if g.ebene == ziel and w.welt.frei(g.pos, g.radius, ziel, True):
                oben_an = True
                break
        if not oben_an:
            haengt.append((art, eb, tx, ty))
pruef("Jeder Aufzug traegt Laeufer und Brecher, in beide Richtungen (%d Faelle)"
      % (2 * len(netz_w.treppen)), not haengt, haengt[:6])
w.verlassen()

print("\nFEHLER:", fails if fails else "keine")
sys.exit(1 if fails else 0)
