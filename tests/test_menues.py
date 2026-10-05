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
pruef("Tonseite hat zwei Regler (Musik gibt es noch nicht)", len(regler) == 2,
      str(len(regler)))
opt.wahl = opt.elemente.index(regler[0])
vorher = app.opt["ton_gesamt"]
taste(opt, pygame.K_LEFT)
pruef("Links senkt die Lautstaerke", app.opt["ton_gesamt"] < vorher,
      "%s -> %s" % (vorher, app.opt["ton_gesamt"]))
pruef("Der Mischer uebernimmt den Wert sofort",
      abs(app.klaenge.gesamt - app.opt["ton_gesamt"] / 100.0) < 1e-6)

opt.seite_wechseln(2)
gesperrt = [el for el in opt.elemente if el.gesperrt]
pruef("Was es noch nicht gibt, ist als NICHT VERFUEGBAR markiert",
      len(gesperrt) == 4 and all(isinstance(el, ui.Platzhalter) for el in gesperrt),
      str(len(gesperrt)))
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
app.opt.zuruecksetzen_werte()

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
pruef("Ein Satz, zwei Waffen, eine Wurfwaffe",
      waehler[:4] == ["satz", "waffe0", "waffe1", "wurf0"], str(waehler))

w0 = next(el for el in aus.elemente if el.name == "waffe0")
w0.index = list(K.LOADOUT["auswahl_waffen"]).index("scharf")
aus.geaendert(w0)
pruef("Eine geaenderte Waffe steht sofort im Loadout",
      "scharf" in app.konto.loadout["waffen"],
      str(app.konto.loadout["waffen"]))
pruef("Und sofort auf der Platte",
      "scharf" in KONTO_M.Konto(ablage_=ABLAGE.LokaleAblage(ordner=pfade.ordner()),
                                ordner=pfade.ordner(),
                                mit_faden=False).loadout["waffen"])

# Zweimal dieselbe Waffe waere ein Platz weniger, kein Vorteil.
w1 = next(el for el in aus.elemente if el.name == "waffe1")
w1.index = list(K.LOADOUT["auswahl_waffen"]).index("scharf")
aus.geaendert(w1)
pruef("Zweimal dieselbe Waffe gibt es nicht",
      len(set(app.konto.loadout["waffen"])) == 2,
      str(app.konto.loadout["waffen"]))

satz = next(el for el in aus.elemente if el.name == "satz")
satz.index = 2
aus.geaendert(satz)
pruef("Ein anderer Satz laesst sich waehlen", app.konto.gewaehlt == 2)
pruef("Und die Waehler zeigen dann dessen Waffen",
      next(el for el in aus.elemente if el.name == "waffe0").wert
      == app.konto.loadout["waffen"][0])

pruef("Vorher wurde noch nie ausgeruestet", not app.konto.loadout_gewaehlt_je)
taste(aus, pygame.K_ESCAPE)
pruef("Nach dem Schliessen gilt es als erledigt",
      app.konto.loadout_gewaehlt_je)
pruef("Und wir sind wieder bei der Anmeldung", app.oben is an)
taste(an, pygame.K_ESCAPE)

# Bilder der beiden neuen Masken, wie bei den anderen auch.
schirm(M.Anmeldung(app), "menue_8_konto.png")
schirm(M.Ausruestung(app), "menue_9_ausruestung.png")

print()
print("FEHLER:", ", ".join(fehler) if fehler else "keine")
pygame.quit()
shutil.rmtree(_WEG, ignore_errors=True)
sys.exit(1 if fehler else 0)
