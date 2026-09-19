# -*- coding: utf-8 -*-
"""
Bedient Pausenmenue, Einstellungen, Steuerung und Inventar ohne Bildschirm.

Der Test schreibt in einen Wegwerfordner, nicht in das echte Benutzerprofil.
Dafuer werden APPDATA, XDG_CONFIG_HOME und HOME umgebogen, **bevor** etwas aus
dustfront geladen wird - pfade.ordner() merkt sich sein Ergebnis beim ersten
Aufruf, danach hilft Umbiegen nichts mehr.

    python tests/test_menues.py

Ausgabe ist eine Liste von Pruefungen. Am Ende steht, was fehlt.
"""
import os
import shutil
import sys
import tempfile

_WEG = tempfile.mkdtemp(prefix="dustfront_test_")
os.environ["APPDATA"] = _WEG                       # Windows
os.environ["XDG_CONFIG_HOME"] = _WEG               # Linux
os.environ["HOME"] = _WEG                          # macOS (~/Library/...)
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pygame

from dustfront import config as K
from dustfront import einstellungen as E
from dustfront import menues as M
from dustfront import pfade
from dustfront import ui
from dustfront.core import App
from dustfront.inventar import Inventar
from dustfront.play import Spiel

fehler = []


def pruef(text, ok, zusatz=""):
    print(("  ok    " if ok else "FEHLER  ") + text
          + (("   " + zusatz) if zusatz and not ok else ""))
    if not ok:
        fehler.append(text)


def taste(szene, key):
    szene.ereignis(pygame.event.Event(pygame.KEYDOWN, key=key, mod=0,
                                      unicode="", scancode=0))


def zeiger(app, punkt):
    """Punkt der Spielflaeche in eine Fensterkoordinate umrechnen."""
    return (int(app.viewport.x + punkt[0] * app.skala),
            int(app.viewport.y + punkt[1] * app.skala))


def klick(szene, fensterpunkt, runter=True, knopf=1):
    art = pygame.MOUSEBUTTONDOWN if runter else pygame.MOUSEBUTTONUP
    szene.ereignis(pygame.event.Event(art, pos=fensterpunkt, button=knopf))


app = App("test", None, headless=True)
szene = Spiel(app)
app.schieben(szene)
held = szene.held

pruef("Ablage liegt im Wegwerfordner", str(pfade.ordner() or "").startswith(_WEG),
      str(pfade.ordner()))

# ── Pausenmenue ───────────────────────────────────────────────────────
print("Pausenmenue")
taste(szene, app.opt.codes("pause")[0])
pruef("Pausentaste oeffnet die Pause", isinstance(app.oben, M.Pause))
pause = app.oben
taste(pause, pygame.K_DOWN)
taste(pause, pygame.K_RETURN)
pruef("EINSTELLUNGEN oeffnet sich", isinstance(app.oben, M.Einstellungen))

# ── Einstellungen ─────────────────────────────────────────────────────
print("Einstellungen")
opt = app.oben
pruef("Auswahl steht auf der ersten Zeile, nicht auf dem Reiter",
      opt.wahl == len(opt.reiter))
alt = app.opt["fenstermodus"]
taste(opt, pygame.K_RIGHT)
pruef("Rechts aendert den Fenstermodus", app.opt["fenstermodus"] != alt,
      "%r -> %r" % (alt, app.opt["fenstermodus"]))
pruef("Aenderung steht sofort in der Datei",
      E.Einstellungen()["fenstermodus"] == app.opt["fenstermodus"])

opt.seite_wechseln(1)
regler = [el for el in opt.elemente if isinstance(el, ui.Regler)]
pruef("Tonseite hat drei Regler", len(regler) == 3, str(len(regler)))
opt.wahl = opt.elemente.index(regler[0])
vorher = app.opt["ton_gesamt"]
taste(opt, pygame.K_LEFT)
pruef("Links senkt die Lautstaerke", app.opt["ton_gesamt"] < vorher,
      "%s -> %s" % (vorher, app.opt["ton_gesamt"]))
pruef("Der Mischer uebernimmt den Wert sofort",
      abs(app.klaenge.gesamt - app.opt["ton_gesamt"] / 100.0) < 1e-6)

opt.seite_wechseln(2)
gesperrt = [el for el in opt.elemente if el.gesperrt]
pruef("Drei Zeilen sind als spaeter markiert", len(gesperrt) == 3,
      str(len(gesperrt)))
opt.wahl = opt.elemente.index(gesperrt[0])
taste(opt, pygame.K_RETURN)
pruef("Eine gesperrte Zeile tut nichts", app.oben is opt)

app.opt.zuruecksetzen_werte()
app.anzeige_uebernehmen()
taste(opt, pygame.K_ESCAPE)
pruef("ESC geht zurueck zur Pause", app.oben is pause)

# ── Steuerung ─────────────────────────────────────────────────────────
print("Steuerung")
pause.wahl = 2
taste(pause, pygame.K_RETURN)
st = app.oben
pruef("STEUERUNG oeffnet sich", isinstance(st, M.Steuerung))

zeile = next(el for el in st.elemente if el.name == "nachladen")
st.wahl = st.elemente.index(zeile)
taste(st, pygame.K_RETURN)
pruef("Die Zeile wartet auf eine Taste", st.wartet_auf == "nachladen")
taste(st, pygame.K_j)
pruef("J ist jetzt Nachladen", app.opt.tasten["nachladen"] == ["j"],
      str(app.opt.tasten["nachladen"]))
pruef("Die Eingabe kennt die neue Taste",
      pygame.K_j in app.eingabe.tabelle["nachladen"])
pruef("Steht sofort in tasten.json",
      E.Einstellungen().tasten["nachladen"] == ["j"])

# Eine Taste gehoert immer nur einer Aktion: H vom Medkit auf Sprint legen
zeile = next(el for el in st.elemente if el.name == "sprint")
st.wahl = st.elemente.index(zeile)
taste(st, pygame.K_RETURN)
taste(st, pygame.K_h)
pruef("Sprint bekommt H", app.opt.tasten["sprint"] == ["h"])
pruef("Das Medkit verliert H dabei", "h" not in app.opt.tasten["heilen"],
      str(app.opt.tasten["heilen"]))

pruef("Pause ist gesperrt",
      next(el for el in st.elemente if el.name == "pause").gesperrt)
app.opt.belegen("pause", pygame.K_p)
pruef("belegen() weigert sich bei Pause", app.opt.tasten["pause"] == ["escape"],
      str(app.opt.tasten["pause"]))

st.ausloesen(next(el for el in st.elemente if el.name == "reset"))
pruef("Zuruecksetzen stellt die Vorgabe wieder her",
      app.opt.tasten["nachladen"] == ["r"] and app.opt.tasten["heilen"] == ["h"])
taste(st, pygame.K_ESCAPE)

# ── Mitwirkende ───────────────────────────────────────────────────────
print("Mitwirkende")
pause.wahl = 3
taste(pause, pygame.K_RETURN)
cr = app.oben
pruef("MITWIRKENDE oeffnet sich", isinstance(cr, M.Mitwirkende))
for _ in range(600):
    cr.schritt(K.FIXED_DT)
pruef("Der Abspann laeuft von selbst", cr.versatz > 0)
taste(cr, pygame.K_SPACE)
stand = cr.versatz
for _ in range(120):
    cr.schritt(K.FIXED_DT)
pruef("Die Leertaste haelt ihn an", cr.versatz == stand)
taste(cr, pygame.K_ESCAPE)
taste(pause, pygame.K_ESCAPE)
pruef("Zurueck im Spiel", app.oben is szene)

# ── Inventar ──────────────────────────────────────────────────────────
print("Inventar")
taste(szene, app.opt.codes("inventar")[0])
inv = app.oben
pruef("Inventartaste oeffnet das Inventar", isinstance(inv, Inventar))

vorher = list(held.waffen)
angelegt = held.waffen[held.waffe]
held.magazin[vorher[0]] = 7                     # Munition zum Wiedererkennen
inv.tauschen(0, 4)
pruef("Tauschen vertauscht zwei Plaetze",
      held.waffen[0] == vorher[4] and held.waffen[4] == vorher[0])
pruef("Die angelegte Waffe bleibt dieselbe",
      held.waffen[held.waffe] == angelegt)
pruef("Die Munition haengt an der Waffe, nicht am Platz",
      held.magazin[vorher[0]] == 7)

inv.ruesten(2)
pruef("Ruesten legt Platz 3 an", held.waffe == 2)
inv.ruesten(2)
pruef("Noch einmal Ruesten aendert nichts", held.waffe == 2)

inv.wahl = 0
taste(inv, pygame.K_RETURN)
pruef("Enter nimmt die Waffe auf", inv.greift == 0)
taste(inv, pygame.K_RIGHT)
taste(inv, pygame.K_RETURN)
pruef("Das zweite Enter legt sie ab",
      inv.greift is None and held.waffen[1] == vorher[4])

a, b = held.waffen[0], held.waffen[3]
klick(inv, zeiger(app, inv.plaetze[0].center))
pruef("Die Maus greift einen Platz", inv.zieht and inv.greift == 0)
klick(inv, zeiger(app, inv.plaetze[3].center), runter=False)
pruef("Loslassen ueber einem anderen Platz tauscht",
      held.waffen[0] == b and held.waffen[3] == a)

held.leben = 40.0
held.medkits = 1
taste(inv, app.opt.codes("heilen")[0])
pruef("Ein Medkit laesst sich aus dem Inventar ansetzen",
      held.medkits == 0 and held.heilt_rest > 0)
taste(inv, app.opt.codes("inventar")[0])
pruef("Dieselbe Taste schliesst wieder", app.oben is szene)
for _ in range(240):
    szene.schritt(K.FIXED_DT)
pruef("Die Heilung laeuft nach dem Schliessen durch", held.leben > 40.0,
      "%.0f Leben" % held.leben)

# ── Bilder zum Anschauen ──────────────────────────────────────────────
print("Bilder")


def schirm(neue_szene, name, schritte=0):
    app.schieben(neue_szene)
    for _ in range(schritte):
        neue_szene.schritt(K.FIXED_DT)
    app.flaeche.fill(K.C_VOID)
    for s in app._sichtbar():
        s.zeichnen(app.flaeche, 0.0)
    pygame.image.save(pygame.transform.scale(
        app.flaeche, (K.GAME_W * 2, K.GAME_H * 2)), name)
    app.werfen()
    print("  gespeichert " + name)


schirm(M.Pause(app, szene), "menue_1_pause.png")
schirm(M.Einstellungen(app, 0), "menue_2_anzeige.png")
schirm(M.Einstellungen(app, 1), "menue_3_ton.png")
schirm(M.Einstellungen(app, 2), "menue_4_grafik.png")
schirm(M.Steuerung(app), "menue_5_steuerung.png")
schirm(M.Mitwirkende(app), "menue_6_mitwirkende.png", schritte=360)
schirm(Inventar(app, szene), "menue_7_inventar.png")

print()
print("FEHLER:", ", ".join(fehler) if fehler else "keine")
pygame.quit()
shutil.rmtree(_WEG, ignore_errors=True)
sys.exit(1 if fehler else 0)
