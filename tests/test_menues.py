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
from pathlib import Path

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
szene = Spiel(app, seed=20250920)
app.schieben(szene)
held = szene.held

# Lange Beschriftungen bleiben innerhalb ihrer UI-Felder.
def ui_uebertritt(element, rect):
    flaeche = pygame.Surface((260, 30), pygame.SRCALPHA)
    element.zeichnen(flaeche)
    for x in range(flaeche.get_width()):
        for y in range(flaeche.get_height()):
            if not rect.collidepoint(x, y) and flaeche.get_at((x, y)).a:
                return True
    return False


_lang = "BESCHREIBUNG MIT EINEM ABSICHTLICH SEHR LANGEN TEXT " * 3
_r_ui = pygame.Rect(20, 5, 220, 16)
_ui_felder = [
    ui.Knopf(_r_ui, _lang),
    ui.Reiter(_r_ui, _lang),
    ui.Regler(_r_ui, _lang, "lang", 50),
    ui.Wahl(_r_ui, _lang, "lang", [_lang]),
    ui.Schalter(_r_ui, _lang, "lang", True),
    ui.Platzhalter(_r_ui, _lang),
]
pruef("Lange Beschriftungen bleiben in Knopf, Reiter und Einstellfeldern",
      all(not ui_uebertritt(el, _r_ui) for el in _ui_felder))
_spaltenbild = pygame.Surface((260, 30), pygame.SRCALPHA)
ui.spalteneintrag(_spaltenbild, _r_ui, _lang, True, wert=_lang)
_spalten_uebertritt = any(
    _spaltenbild.get_at((x, y)).a
    for x in range(_spaltenbild.get_width())
    for y in range(_spaltenbild.get_height())
    if not _r_ui.collidepoint(x, y))
pruef("Lange Pausenzeileneintraege bleiben im Feld", not _spalten_uebertritt)

pruef("Ablage liegt im Wegwerfordner", str(pfade.ordner() or "").startswith(_WEG),
      str(pfade.ordner()))

# ── Pausenmenue ───────────────────────────────────────────────────────
print("Pausenmenue")
taste(szene, app.opt.codes("pause")[0])
pruef("Pausentaste oeffnet die Pause", isinstance(app.oben, M.Pause))
pause = app.oben
# Ueber den Namen gesucht und nicht ueber die Zeilenzahl: die Pause
# bekommt immer wieder Eintraege dazu, und eine Pruefung, die zaehlt,
# geht dann kaputt, ohne dass etwas kaputt ist.
namen = [el.name for el in pause.elemente]
pruef("Die Pause fuehrt zum Konto und zur Ausruestung",
      "konto" in namen and "ausruestung" in namen, ", ".join(namen))
pause.wahl = namen.index("opt")
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
# Seit 0.34.79 steht hier auch das Brummen des Hauptmenues (das keine
# eigene Einstellungsseite mehr hat). Musik gibt es weiter nicht.
pruef("Tonseite: Gesamt und Effekte - kein Brummen (seit 0.34.136), keine Musik",
      [el.name for el in regler] == ["ton_gesamt", "ton_effekte"],   # seit 0.34.136 kein Brummen mehr
      str([el.name for el in regler]))
opt.wahl = opt.elemente.index(regler[0])
vorher = app.opt["ton_gesamt"]
taste(opt, pygame.K_LEFT)
pruef("Links senkt die Lautstaerke", app.opt["ton_gesamt"] < vorher,
      "%s -> %s" % (vorher, app.opt["ton_gesamt"]))
pruef("Der Mischer uebernimmt den Wert sofort",
      abs(app.klaenge.gesamt - app.opt["ton_gesamt"] / 100.0) < 1e-6)

opt.seite_wechseln(2)
# Seit 0.34.79 stehen keine grauen NICHT-VERFUEGBAR-Zeilen mehr in den
# Einstellungen (Menues aufgeraeumt). Auf keiner Seite.
_platzhalter = []
for _nr in (0, 1, 2, 4, 5):
    opt.seite_wechseln(_nr)
    _platzhalter += [el.text for el in opt.elemente if isinstance(el, ui.Platzhalter)]
pruef("Keine Seite der Einstellungen zeigt NICHT VERFUEGBAR", not _platzhalter,
      ", ".join(_platzhalter))
opt.seite_wechseln(2)
pruef("GRAFIK hat Roehrenbild und Intro des Hauptmenues",
      {"menue_crt", "intro"} <= {el.name for el in opt.elemente})
# Wie sich eine gesperrte Zeile verhaelt, gilt trotzdem weiter - der
# Platzhalter selbst ist nicht weg (ui.Platzhalter).
opt.elemente.append(ui.Platzhalter((40, 300, 200, 16), "PROBE", "probe_gesperrt"))
gesperrt = [el for el in opt.elemente if el.gesperrt]
pruef("Ein Platzhalter laesst sich nicht waehlen",
      not any(el in opt.waehlbar for el in gesperrt))
opt.wahl = opt.elemente.index(gesperrt[0])
taste(opt, pygame.K_RETURN)
pruef("Eine gesperrte Zeile tut nichts", app.oben is opt)
opt.maus_druck(pygame.Vector2(gesperrt[0].rect.center))
pruef("Auch ein Klick darauf nicht", app.oben is opt)

# Barrierefreiheit (seit 0.32)
opt.seite_wechseln(4)
namen4 = [el.name for el in opt.elemente]
pruef("Barrierefreiheit: Blendgranate, Bildwackeln, Blick voraus",
      {"blendung", "bildschirm_ruckeln", "kamera_blick"} <= set(namen4), str(namen4))
bl = next(el for el in opt.elemente if el.name == "blendung")
opt.wahl = opt.elemente.index(bl)
taste(opt, pygame.K_RIGHT)
pruef("Die Blendung laesst sich auf NUR WEISS stellen",
      app.opt["blendung"] == "weiss", app.opt["blendung"])
pruef("Und gehoert zum Konto", "blendung" in E.KONTO_WERTE)
pruef("Blick voraus ist aus, solange man ihn nicht anmacht",
      E.VORGABE["kamera_blick"] is False)
# Der Reiter STEUERUNG tauscht die Szene aus - und zurueck.
opt.seite_wechseln(3)
pruef("Der Reiter STEUERUNG zeigt die Tastenbelegung",
      isinstance(app.oben, M.Steuerung), type(app.oben).__name__)
st_r = app.oben
taste(st_r, pygame.K_e)
pruef("E blaettert weiter zu BARRIEREFREIHEIT",
      isinstance(app.oben, M.Einstellungen) and app.oben.seite == 4)
opt = app.oben

app.opt.zuruecksetzen_werte()
app.anzeige_uebernehmen()
taste(opt, pygame.K_ESCAPE)
pruef("ESC geht zurueck zur Pause", app.oben is pause)

# ── Steuerung ─────────────────────────────────────────────────────────
print("Steuerung")
pause.wahl = [el.name for el in pause.elemente].index("tasten")
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

# Eine Taste gehoert immer nur einer Aktion: H vom Medkit auf den Dash legen
zeile = next(el for el in st.elemente if el.name == "dash")
st.wahl = st.elemente.index(zeile)
taste(st, pygame.K_RETURN)
taste(st, pygame.K_h)
pruef("Der Dash bekommt H", app.opt.tasten["dash"] == ["h"])
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
pause.wahl = [el.name for el in pause.elemente].index("credits")
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
# ── LAN-Gefecht: Bestenliste und Rundenende ─────────────────────────
# Hier und nicht in test_spiel.py, weil dieser Test seine Pfade schon auf
# einen Wegwerfordner umgebogen hat - die Bestenliste des Spielers soll
# ein Testlauf niemals anfassen.
print("LAN-Gefecht")
from dustfront import bestenliste
from dustfront import netz
from dustfront.mehrspieler import Gefecht

pruef("Bestenliste faengt leer an", bestenliste.laden()["eintraege"] == [])
pruef("und liegt im Wegwerfordner", _WEG in bestenliste.beschreibung(),
      bestenliste.beschreibung())

daten = bestenliste.eintragen([
    {"name": "MEISTER", "abschuesse": 7, "tode": 2,
     "mvp_punkte": 90, "mvp": False},
    {"name": "BESUCH", "abschuesse": 3, "tode": 5,
     "mvp_punkte": 130, "mvp": True},
])
pruef("Ergebnis wird eingetragen", len(daten["eintraege"]) == 2)
pruef("Die beste Rundenwertung steht oben", daten["eintraege"][0]["name"] == "BESUCH",
      daten["eintraege"][0]["name"])

# Eine zweite Runde muss dazuzaehlen, nicht ersetzen
daten = bestenliste.eintragen([{"name": "MEISTER", "abschuesse": 4, "tode": 1,
                                "mvp_punkte": 80, "mvp": True}])
meister = [e for e in daten["eintraege"] if e["name"] == "MEISTER"][0]
pruef("Abschuesse und MVP-Punkte werden zusammengezaehlt",
      meister["abschuesse"] == 11 and meister["mvp_punkte"] == 170
      and meister["mvp_auszeichnungen"] == 1,
      "%d Abschuesse, %.1f MVP-Punkte, %d MVP-Auszeichnungen"
      % (meister["abschuesse"], meister["mvp_punkte"], meister["mvp_auszeichnungen"]))
pruef("Die Liste ueberlebt einen Neustart",
      bestenliste.laden()["eintraege"][0]["abschuesse"] == 11
      and bestenliste.laden()["eintraege"][0]["mvp_punkte"] == 170)

# Kaputte Datei darf nichts kosten
from dustfront import pfade
pfade.datei(bestenliste.DATEI).write_text("{kein json", encoding="utf-8")
pruef("Kaputte Bestenliste kostet nur die Liste",
      bestenliste.laden()["eintraege"] == [])

# Rundenende beim Gastgeber
wirt = netz.Gastgeber(51007)
gefecht = Gefecht(app, "MEISTER", gastgeber=wirt)
gefecht.rest = 0.02
for _ in range(4):
    gefecht.schritt(K.NETZ["takt"])
pruef("Runde endet, wenn die Zeit um ist", gefecht.vorbei)
pruef("Endstand steht", len(gefecht.liste) == 1, str(gefecht.liste))
pruef("und ist in der Bestenliste gelandet",
      any(e["name"] == "MEISTER" for e in bestenliste.laden()["eintraege"]))
gefecht.verlassen()

# Namen, die aus dem Netz kommen, muessen anzeigbar werden
pruef("Name wird gesaeubert", netz.name_saeubern("  m\u00e4x!! ") == "MX",
      netz.name_saeubern("  m\u00e4x!! "))
pruef("Leerer Name wird ersetzt", netz.name_saeubern("") == "GAST")
pruef("Langer Name wird gekuerzt",
      len(netz.name_saeubern("A" * 40)) == K.NETZ["namenslaenge"])
pruef("Adresse mit Port wird zerlegt",
      netz.adresse_lesen("192.168.1.7:50505") == ("192.168.1.7", 50505))
pruef("Adresse ohne Port bekommt den Standard",
      netz.adresse_lesen("192.168.1.7") == ("192.168.1.7", K.NETZ["port"]))

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


schirm(M.Pause(app, szene), "menue_1_pause.png", schritte=60)   # aufgeklappt
schirm(M.Einstellungen(app, 0), "menue_2_anzeige.png")
schirm(M.Einstellungen(app, 1), "menue_3_ton.png")
schirm(M.Einstellungen(app, 2), "menue_4_grafik.png")
schirm(M.Einstellungen(app, 4), "menue_4b_barrierefreiheit.png")
schirm(M.Steuerung(app), "menue_5_steuerung.png")
schirm(M.Mitwirkende(app), "menue_6_mitwirkende.png", schritte=360)
schirm(Inventar(app, szene), "menue_7_inventar.png")

# ── Konto und Ausruestung ────────────────────────────────────────────
# ── 0.32: Umlaute, Inventar, Hauptmenue teilt die Einstellungen ───────
print("Umlaute, Inventar, Hauptmenue")
from dustfront.font import SCHRIFT as _S, GH as _GH, UEBER as _UE
_u = _S.flaeche("ZURÜCK", (255, 255, 255))
_n = _S.flaeche("ZURUCK", (255, 255, 255))
pruef("Ein Umlaut ist so gross wie die anderen Buchstaben, die Punkte ragen darueber",
      _u.get_height() == _GH + _UE and _n.get_height() == _GH
      and _u.get_at((_S.breite("ZUR") + 2, _UE + _GH - 1))[3] > 0,
      "%d / %d" % (_u.get_height(), _n.get_height()))
_t = pygame.Surface((80, 30), pygame.SRCALPHA)
_S.zeichnen(_t, "Ü", 10, 12, (255, 255, 255))
pruef("Und steht auf derselben Grundlinie",
      _t.get_at((10, 12 + _GH - 1))[3] == 0 and _t.get_at((11, 12 + _GH - 1))[3] > 0
      and _t.get_at((11, 12 - _UE))[3] > 0)

_inv = Inventar(app, szene)
_felder = [_inv.hotbar_feld(i) for i in range(len(K.HOTBAR))]
from dustfront.inventar import TAFEL as _TAFEL
pruef("Alle Hotbar-Plaetze passen in die Inventartafel",
      all(_TAFEL.contains(f) for f in _felder), str(_felder[-1]))
pruef("Die Waffenplaetze liegen ueber den zwei Hinweiszeilen",
      max(f.bottom for f in _inv.plaetze) <= 54 + 136 - 22 - 2,
      str(max(f.bottom for f in _inv.plaetze)))

import importlib
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
RM = importlib.import_module("rustfront_menu")
RM.SETTINGS_PATH = Path(_WEG) / "rustfront_settings.json"
_au = RM.Audio(RM.Settings())
pruef("Das Hauptmenue spielt keinen Dauerton mehr (seit 0.34.136: das Brummen ist weg)",
      not hasattr(_au, "drone") and not hasattr(RM.Audio, "start_drone")
      and all(k_.get_length() < 0.5 for k_ in _au.sounds.values()),
      str({n_: round(k_.get_length(), 2) for n_, k_ in _au.sounds.items()}))
pruef("... und oeffnet den Mischer mit demselben Puffer wie das Spiel", RM.MIX_PUFFER == K.AUDIO["puffer"])

# Vorab uebersetzen (seit 0.34.137, gemeldet: auf schwachen Rechnern beim
# ersten Start jeder Version ein langer schwarzer Schirm vor der ersten Runde).
import shutil as _sh137
_pk137 = Path(_WEG) / "paket137"
_sh137.copytree(Path(__file__).resolve().parent.parent / "dustfront", _pk137,
                ignore=_sh137.ignore_patterns("__pycache__"))
_vor137 = len(RM._veraltet(_pk137))
_proc137 = RM.vorab_uebersetzen(_pk137)
pruef("Neue Version: ein eigener Prozess uebersetzt das ganze Paket, waehrend man im Menue steht",
      _vor137 > 20 and _proc137 is not None and _proc137.wait(120) == 0 and not RM._veraltet(_pk137),
      "%d veraltet, danach %d" % (_vor137, len(RM._veraltet(_pk137))))
pruef("... beim naechsten Start ist nichts zu tun (kein Prozess)", RM.vorab_uebersetzen(_pk137) is None)
_bild137 = pygame.Surface((RM.VW, RM.VH))
_gezeigt137 = []
_fake137 = type("A", (), {"canvas": _bild137, "present": lambda self_: _gezeigt137.append(1)})()
RM.ladebild(_fake137)
pruef("... und beim Uebergang ins Spiel steht LAEDT im Bild statt schwarz",
      _gezeigt137 and any(_bild137.get_at((x_, RM.VH // 2))[:3] != RM.C_VOID for x_ in range(RM.VW)))
RM.uebersetzer_abwarten(_fake137, 5.0)
app.opt["bildrate"] = 144
app.opt["ton_gesamt"] = 40
app.opt["fenstermodus"] = "randlos"
app.opt.speichern()
_rm = RM.Settings()
pruef("Das Hauptmenue zeigt die Werte aus dem Spiel",
      RM.BILDRATEN[_rm.fps_index] == 144 and _rm.vol_master == 40 and _rm.fullscreen,
      "%s / %s" % (RM.BILDRATEN[_rm.fps_index], _rm.vol_master))
_rm.set("vol_sfx", 30)
_neu = E.Einstellungen()
pruef("Und schreibt, was man dort aendert, ins Spiel",
      _neu["ton_effekte"] == 30, str(_neu["ton_effekte"]))
pruef("Ohne etwas anderes umzustellen (RANDLOS bleibt RANDLOS)",
      _neu["fenstermodus"] == "randlos" and _neu["bildrate"] == 144,
      "%s / %s" % (_neu["fenstermodus"], _neu["bildrate"]))
_zeilen = dict(RM.steuerung_zeilen())
pruef("Die Steuerung im Hauptmenue ist die des Spiels",
      _zeilen.get("NACHLADEN") == E.belegung_text(app.opt.tasten["nachladen"])
      and "BAUEN" not in _zeilen, str(_zeilen))
# Das Hauptmenue (seit 0.34.79 aufgeraeumt): keine Knoepfe, die nichts
# tun, eine Erklaerkarte je Punkt, und Einstellungen nur noch im Spiel.
pruef("Hauptmenue: ohne FORTSETZEN, Region und eigene Optionsseite",
      "newgame" not in RM.PAGES and "options" not in RM.PAGES)
_hm = RM.MainPage.__new__(RM.MainPage)
_hm.app = None
_hm.build()
_labels = [it.label for it in _hm.items if isinstance(it, RM.Action)]
pruef("Hauptmenue: Spielen, Ausruestung, Konto, Einstellungen, Hilfe",
      {"EINZELSPIELER", "MEHRSPIELER", "TESTMODUS", "AUSRÜSTUNG", "KONTO",
       "EINSTELLUNGEN", "SO SPIELST DU", "BEENDEN"} <= set(_labels), str(_labels))
pruef("Jeder Punkt hat eine Erklaerung",
      all(it.info for it in _hm.items if isinstance(it, RM.Action)))
pruef("Roehrenbild, Intro und Brummen kommen aus dem Spiel",
      {"crt", "splash", "vol_ambient"} <= set(RM.GETEILT))
app.opt["menue_crt"] = False
app.opt["intro"] = False
app.opt.speichern()
_rm2 = RM.Settings()
pruef("... und das Hauptmenue uebernimmt sie", _rm2.crt is False and _rm2.splash is False)
app.opt.zuruecksetzen_werte()
app.opt.speichern()
pruef("Die Einstellungen des Spiels kennen sie", {"menue_crt", "intro", "ton_menue"} <= set(E.VORGABE))

# Direkt in den Testmodus (seit 0.34.63): so startet ios/aufspielen.sh
# --testmodus die App auf dem iPhone oder iPad.
_alt_start = os.environ.pop("DUSTFRONT_START", None)
pruef("Ohne DUSTFRONT_START beginnt das Spiel im Hauptmenue", RM._startauftrag() is None)
os.environ["DUSTFRONT_START"] = "testmodus"
os.environ["DUSTFRONT_KARTE"] = "Wueste"
pruef("Mit DUSTFRONT_START=testmodus gleich im Testmodus, auf der gewuenschten Karte",
      RM._startauftrag() == {"action": "testmodus", "karte": "wueste"}, str(RM._startauftrag()))
os.environ.pop("DUSTFRONT_KARTE", None)
pruef("... ohne Karte auf STAUBTAL", RM._startauftrag()["karte"] == "staubtal")
os.environ.pop("DUSTFRONT_START", None)
if _alt_start is not None:
    os.environ["DUSTFRONT_START"] = _alt_start

print("Konto und Ausruestung")
from dustfront import konto as KONTO_M
from dustfront import ablage as ABLAGE

app._konto = KONTO_M.Konto(ablage_=ABLAGE.LokaleAblage(ordner=pfade.ordner()),
                           ordner=pfade.ordner(), mit_faden=False)

pause.wahl = [el.name for el in pause.elemente].index("konto")
taste(pause, pygame.K_RETURN)
an = app.oben
pruef("KONTO oeffnet sich", isinstance(an, M.Anmeldung))
pruef("Zwei Felder: Name und Kennwort",
      [f.name for f in an.felder] == ["name", "wort"],
      str([f.name for f in an.felder]))
pruef("Das Kennwortfeld ist verdeckt", an.felder[1].verdeckt)

# Getippt wird ins Feld und nicht ins Menue. Genau hier geht es sonst
# schief: ein "w" waehlte frueher eine Zeile weiter, statt ein w zu
# schreiben.
def tippen(szene, text):
    for c in text:
        szene.ereignis(pygame.event.Event(pygame.KEYDOWN, key=ord(c[0]),
                                          unicode=c))

vorher_wahl = an.wahl
tippen(an, "MeisterW")
pruef("Getippt wird ins Feld, nicht ins Menue",
      an.felder[0].wert == "MeisterW" and an.wahl == vorher_wahl,
      "%r, Wahl %d" % (an.felder[0].wert, an.wahl))
tippen(an, "!? ")
pruef("Was kein Kontoname sein darf, kommt nicht hinein",
      an.felder[0].wert == "MeisterW", an.felder[0].wert)
taste(an, pygame.K_BACKSPACE)
pruef("Rueckschritt loescht ein Zeichen", an.felder[0].wert == "Meister")
taste(an, pygame.K_TAB)
pruef("TAB springt ins naechste Feld", an.tippt == 1)
tippen(an, "geheim12345")
pruef("Und dort steht das Kennwort", an.felder[1].wert == "geheim12345")

# Ein zu kurzes Kennwort muss eine Auskunft geben, keine stille Ablehnung.
an.felder[1].wert = "kurz"
an.ausloesen(ui.Knopf((0, 0, 1, 1), "", "anlegen"))
pruef("Ein zu kurzes Kennwort wird erklaert",
      "KENNWORT" in app.konto.fehler, app.konto.fehler)

an.felder[1].wert = "geheim12345"
an.ausloesen(ui.Knopf((0, 0, 1, 1), "", "anlegen"))
pruef("Mit einem guten Kennwort geht es durch",
      app.konto.angemeldet and app.konto.name == "Meister",
      app.konto.fehler or app.konto.name)
an.schritt(0.1)
namen = [el.name for el in an.elemente]
pruef("Die Maske zeigt danach, was ein Angemeldeter braucht",
      "abmelden" in namen and not an.felder, str(namen))

an.ausloesen(ui.Knopf((0, 0, 1, 1), "", "ausruestung"))
aus = app.oben
pruef("AUSRUESTUNG oeffnet sich", isinstance(aus, M.Ausruestung))
waehler = [el.name for el in aus.elemente]
# Seit 0.34.73 steht die Klasse zwischen Satz und Waffen, seit 0.34.91
# heissen die Waffenzeilen nach ihrem Platz.
# Seit 0.34.94 mit dem Namen des Satzes zum Selbertippen.
pruef("Ein Satz, sein Name, eine Klasse, Haupt- und Seitenwaffe, eine Wurfwaffe",
      waehler[:6] == ["satz", "satzname", "klasse", "waffe0", "waffe1", "wurf0"], str(waehler))
pruef("... und Knoepfe fuer einen neuen Satz und zum Loeschen",
      "neu" in waehler and "loeschen" in waehler, str(waehler))
_n_vor = len(app.konto.loadouts)
_gew_vor = app.konto.gewaehlt
aus.ausloesen(next(el for el in aus.elemente if el.name == "neu"))
_feld = next(el for el in aus.elemente if el.name == "satzname")
pruef("NEUER SATZ legt einen an, waehlt ihn und stellt die Wahl auf seinen Namen",
      len(app.konto.loadouts) == _n_vor + 1 and app.konto.gewaehlt == _n_vor
      and aus.gewaehlt() is _feld, "%d Saetze" % len(app.konto.loadouts))
_feld.wert = ""
for _z in "Wüste #2!":  # "#" kann die Schrift nicht - faellt heraus
    aus.taste(pygame.event.Event(pygame.KEYDOWN, key=0, unicode=_z, mod=0))
pruef("Der Name ist frei waehlbar - getippt, gross, sofort im Konto (auch w und s gehen ins Feld)",
      app.konto.loadout["name"] == "WÜSTE 2!", app.konto.loadout["name"])
aus.ausloesen(next(el for el in aus.elemente if el.name == "loeschen"))
pruef("LÖSCHEN nimmt ihn wieder weg", len(app.konto.loadouts) == _n_vor, str(len(app.konto.loadouts)))
app.konto.loadout_waehlen(_gew_vor)
aus.aufbauen()
waehler = [el.name for el in aus.elemente]
w0 = next(el for el in aus.elemente if el.name == "waffe0")
w1 = next(el for el in aus.elemente if el.name == "waffe1")
pruef("... die erste Zeile ist die Hauptwaffe, die zweite die Seitenwaffe",
      w0.text == K.PLATZ_NAMEN["haupt"] and w1.text == K.PLATZ_NAMEN["seite"]
      and all(K.WAFFEN_PLATZ[w] == "haupt" for w in w0.optionen)
      and all(K.WAFFEN_PLATZ[w] == "seite" for w in w1.optionen), "%s %s" % (w0.optionen, w1.optionen))

_neu_w0 = next(w for w in w0.optionen if w != w0.wert)
w0.index = w0.optionen.index(_neu_w0)
aus.geaendert(w0)
pruef("Eine geaenderte Waffe steht sofort im Loadout",
      _neu_w0 in app.konto.loadout["waffen"],
      str(app.konto.loadout["waffen"]))
pruef("Und sofort auf der Platte",
      _neu_w0 in KONTO_M.Konto(ablage_=ABLAGE.LokaleAblage(ordner=pfade.ordner()),
                               ordner=pfade.ordner(),
                               mit_faden=False).loadout["waffen"])

# Zwei Hauptwaffen gibt es nicht mehr (seit 0.34.91): jede Zeile waehlt
# aus ihrer eigenen Liste.
pruef("Zweimal dieselbe Waffe oder zwei Hauptwaffen gibt es nicht",
      not set(w0.optionen) & set(w1.optionen)
      and len(set(app.konto.loadout["waffen"])) == 2,
      str(app.konto.loadout["waffen"]))

satz = next(el for el in aus.elemente if el.name == "satz")
satz.index = 2
aus.geaendert(satz)
pruef("Ein anderer Satz laesst sich waehlen", app.konto.gewaehlt == 2)
pruef("Und die Waehler zeigen dann dessen Waffen",
      next(el for el in aus.elemente if el.name == "waffe0").wert
      == app.konto.loadout["waffen"][0])

# Das Aussehen (seit 0.34.60): eine Zeile mehr, gilt sofort, liegt in den
# Einstellungen und wandert mit dem Konto.
pruef("AUSSEHEN steht unter den Waffen, als Vorgabe die alte Figur",
      "aussehen" in waehler and next(el for el in aus.elemente
                                     if el.name == "aussehen").wert == "", str(waehler))
_aus = next(el for el in aus.elemente if el.name == "aussehen")
_aus.index = _aus.optionen.index("wolf")
aus.geaendert(_aus)
pruef("Ein gewaehltes Aussehen steht sofort in den Einstellungen und auf der Platte",
      app.opt["aussehen"] == "wolf" and E.Einstellungen()["aussehen"] == "wolf",
      app.opt["aussehen"])
pruef("Es wandert mit dem Konto", "aussehen" in E.KONTO_WERTE)
pruef("Die Vorschau passt neben die Waehler (alles auf der Tafel, im Bild)",
      K.GAME_W >= aus.tafel.right and aus.tafel.x >= 0
      and all(aus.tafel.contains(el.rect) for el in aus.elemente))
schirm(M.Ausruestung(app), "menue_9b_aussehen.png")
_aus.index = 0
aus.geaendert(_aus)
pruef("Vorher wurde noch nie ausgeruestet", not app.konto.loadout_gewaehlt_je)
taste(aus, pygame.K_ESCAPE)
pruef("Nach dem Schliessen gilt es als erledigt",
      app.konto.loadout_gewaehlt_je)
pruef("Und wir sind wieder bei der Anmeldung", app.oben is an)
taste(an, pygame.K_ESCAPE)

# Bilder der beiden neuen Masken, wie bei den anderen auch.
schirm(M.Anmeldung(app), "menue_8_konto.png")
schirm(M.Ausruestung(app), "menue_9_ausruestung.png")

# ══════════════════════════════════════════════════════════════════
# Kosmetik im Spiel bearbeiten (seit 0.34.135, gewuenscht)
print("\n-- Kosmetik im Spiel --")
import array as _arr, math as _m, wave as _wave
from dustfront import kosmetik_bearbeiten as KB
from dustfront import ablage as _ablage
pruef("PAUSE hat einen Eintrag KOSMETIK",
      any(el.name == "kosmetik" for el in M.Pause(app, szene).elemente))
_ko = KB.ordner()
with _wave.open(str(_ko / "knall.wav"), "wb") as _w:
    _w.setnchannels(2); _w.setsampwidth(2); _w.setframerate(44100)
    _a = _arr.array("h")
    for _i in range(44100 * 5):
        _v = int(9000 * _m.sin(_i * 2 * _m.pi * 110 / 44100)); _a.extend((_v, _v))
    _w.writeframes(_a.tobytes())
_bf = pygame.Surface((800, 450)); _bf.fill((30, 90, 200))
pygame.draw.circle(_bf, (250, 220, 60), (400, 225), 180)
pygame.image.save(_bf, str(_ko / "bild.jpg"))
kb = KB.KosmetikBearbeiten(app)
app.schieben(kb)
kb.ausloesen(next(e for e in kb.elemente if e.name == "ton_laden"))
pruef("TON LADEN nimmt die WAV aus dem Ordner (Stereo, 44100 Hz)",
      kb.ton_quelle is not None and kb.ton_quelle[2] == "knall.wav", kb.meldung)
kb.ausloesen(next(e for e in kb.elemente if e.name == "bild_laden"))
pruef("BILD LADEN nimmt das JPG und macht es klein genug",
      kb.bild_quelle is not None and max(kb.bild_quelle.get_size()) <= K.SPIELERKOSMETIK["bild_max"])
_fw = next(e for e in kb.elemente if e.name == "filter")
_fw.blaettern(2); kb.geaendert(_fw)
_rx = next(e for e in kb.elemente if e.name == "x"); _rx.wert = 30; kb.geaendert(_rx)
_rl = next(e for e in kb.elemente if e.name == "laenge"); _rl.wert = 50; kb.geaendert(_rl)
_ton, _bild = kb.paket()
_pk = __import__("dustfront.spielerkosmetik", fromlist=["aus_konto"]).aus_konto(_ton, _bild)
pruef("Das Paket besteht dieselbe Pruefung wie jedes fremde (Laenge, Lage, Filter)",
      abs(_pk.dauer - 2.5) < 0.05 and abs(_pk.lage["x"] - 0.3) < 0.01 and kb.filter == "sepia",
      "%.2f %s" % (_pk.dauer, _pk.lage))
schirm(kb, "menue_10_kosmetik.png")
kb = KB.KosmetikBearbeiten(app)
app.schieben(kb)
_png = _ko / "zweit.png"
pygame.image.save(_bf, str(_png))
kb.ereignis(pygame.event.Event(pygame.DROPFILE, file=str(_png)))
pruef("Eine Datei ins Fenster ziehen laedt sie", kb.bild_name == "zweit.png", kb.meldung)
if isinstance(app.konto.ablage, _ablage.LokaleAblage) and app.konto.angemeldet:
    kb.ausloesen(next(e for e in kb.elemente if e.name == "ton_laden"))
    kb.ausloesen(next(e for e in kb.elemente if e.name == "speichern"))
    pruef("SPEICHERN legt Ton und Bild ins Konto",
          app.konto.kosmetik is not None and app.konto.kosmetik.bild is not None
          and app.konto.kosmetik_meldung == "GESPEICHERT", app.konto.kosmetik_meldung)
    app.werfen()
    kb2 = KB.KosmetikBearbeiten(app)
    pruef("... und beim naechsten Oeffnen steht es wieder da",
          kb2.ton_quelle is not None and kb2.bild_name == "IM KONTO")
else:
    pruef("(Speichern nur mit lokaler Ablage geprueft)", True)
    app.werfen()

print()
print("FEHLER:", ", ".join(fehler) if fehler else "keine")
pygame.quit()
shutil.rmtree(_WEG, ignore_errors=True)
sys.exit(1 if fehler else 0)
