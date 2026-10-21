"""
DUSTFRONT - Testmodus (seit 0.34.28)
====================================

Gemeldet: "Mach mir bitte einen separaten Gamemode, den man aus dem
Hauptmenue waehlt. Das soll quasi ein temporaerer Testmodus sein, wo ich
neue Features schneller testen kann ... im Spectator-Modus spawnen ... mit
extrem hoher Geschwindigkeit ueber die Map fliegen ... ELEMENTAR, dass
NICHTS in der kompletten Welt, auch spaeter nicht, mich wahrnehmen oder
beeinflussen kann ... alle Spezialaktionen ueber das Numpad ... das Numpad
soll immer on screen angezeigt werden ... alles mit Fokus auf Effizienz
und Kontrolle statt auf Verstaendlichkeit und Gefuehl."

Ein Gefecht (mehrspieler.Gefecht) als Gastgeber, das nur lokal lauscht
und ein Zufallskennwort hat - beitreten kann niemand. Gebucht wird nichts
(`_runde_buchen` und `_abbruch_buchen` sind leer): Statistiken sollen nie
auseinanderlaufen, und ein Test ist keine Runde.

**Der Beobachter.** Die eigene Figur des Gastgebers wird nach dem
Anlegen sofort wieder aus der Welt (`welt.wesen`) und aus der
Kaempferliste (`kaempfer`) genommen. Alles, was in diesem Spiel etwas
wahrnimmt oder trifft, schaut in eine dieser beiden Listen - Kugeln und
Explosionen ins Raster der Welt, Bots und Gegner in die Kaempfer, Beute
auch. Die Figur ist danach nur noch der Punkt, dem die Kamera folgt, und
kann von nichts gefunden werden, auch nicht von etwas, das spaeter dazu
kommt. Blendgranaten und Kameraruckeln treffen den Beobachter auch nicht
(abschaltbar, `blend_beobachter` / `ruckeln_beobachter`).

**Die Zeit.** Gerechnet wird in festen Schritten wie immer; der Zeitfaktor
sagt nur, wie viele davon je Bild laufen (Zeitlupe laesst Bilder aus,
Zeitraffer rechnet mehrere). Steht die Zeit, laeuft gar nichts - kein
Wesen, kein Partikel, keine Uhr eines Bots. Kamera, Menues und Spawner
laufen weiter, und was man dann spawnt, steht sofort in der Welt.

**Steuerung** (alles auch per Klick auf den Ziffernblock am Bildrand):

    0  Zeit an/aus            .  ein Schritt (1/10 s)
    +  schneller              -  langsamer
    /  KI an/aus             *  alles weg (ausser der eigenen Figur)
    7  Ebene runter           9  Ebene hoch           8  Info an/aus
    4  Spawner                5  nochmal spawnen      6  Gottmodus weiter
    1  Bot am Zeiger          2  Puppe am Zeiger      3  Figur uebernehmen
    Enter  loeschen, was am Zeiger liegt
    NUM (angeklickt)  Testmenue
    Esc  Testmenue (Karte, Einstellungen, Gottmodus einzeln, Hauptmenue)
    W A S D  fliegen, Umschalt  schneller, Mausrad  Sichtweite

**Neue Features gehoeren hierher.** Was ab 0.34.28 neu ins Spiel kommt,
muss hier ausprobierbar sein: als Eintrag im Spawner (`EINTRAEGE`), als
Taste oder als Zeile im Testmenue. Siehe AGENTS.md und docs/TESTMODUS.md.
"""

from __future__ import annotations

import math
import random
import types

import pygame

from . import config as K
from . import konto as konto_modul
from . import netz
from . import plattform
from . import ui
from .anzeige import Anzeige
from .entities import Granate, Wesen
from .fahrzeug import Buggy
from .font import SCHRIFT
from .goap import erfuellt as goap_erfuellt
from .mehrspieler import Gefecht, Kaempfer, KampfBeute, KampfGegner


def verfuegbar() -> bool:
    """Den Testmodus gibt es nur mit Tastatur und Ziffernblock - nicht auf
    iPhone und iPad, und nicht mit der Touch-Steuerung."""
    return not plattform.IOS and not plattform.touch_an()


# ══════════════════════════════════════════════════════════════════
# Der Ziffernblock
# ══════════════════════════════════════════════════════════════════

# (Taste, Spalte, Zeile, Breite, Hoehe, Aufschrift auf der Taste)
# Wie ein echter Ziffernblock: + und Enter sind zwei Zeilen hoch, die 0
# zwei Spalten breit.
TASTEN = (
    ("num", 0, 0, 1, 1, "NUM"),
    ("/", 1, 0, 1, 1, "/"), ("*", 2, 0, 1, 1, "*"), ("-", 3, 0, 1, 1, "-"),
    ("7", 0, 1, 1, 1, "7"), ("8", 1, 1, 1, 1, "8"), ("9", 2, 1, 1, 1, "9"),
    ("+", 3, 1, 1, 2, "+"),
    ("4", 0, 2, 1, 1, "4"), ("5", 1, 2, 1, 1, "5"), ("6", 2, 2, 1, 1, "6"),
    ("1", 0, 3, 1, 1, "1"), ("2", 1, 3, 1, 1, "2"), ("3", 2, 3, 1, 1, "3"),
    ("enter", 3, 3, 1, 2, "ENT"),
    ("0", 0, 4, 2, 1, "0"), (".", 2, 4, 1, 1, "."),
)

# pygame-Taste -> Name im Ziffernblock. Ueber den Tastencode und, falls
# der fehlt, ueber den Scancode: mit ausgeschaltetem NumLock schicken
# manche Systeme statt KP_7 ein HOME, der Scancode bleibt aber derselbe.
_CODES = {
    pygame.K_KP0: "0", pygame.K_KP1: "1", pygame.K_KP2: "2", pygame.K_KP3: "3",
    pygame.K_KP4: "4", pygame.K_KP5: "5", pygame.K_KP6: "6", pygame.K_KP7: "7",
    pygame.K_KP8: "8", pygame.K_KP9: "9", pygame.K_KP_PERIOD: ".",
    pygame.K_KP_PLUS: "+", pygame.K_KP_MINUS: "-", pygame.K_KP_MULTIPLY: "*",
    pygame.K_KP_DIVIDE: "/", pygame.K_KP_ENTER: "enter",
}
_SCANCODES = {}
for _name, _taste in (("0", "KP_0"), ("1", "KP_1"), ("2", "KP_2"), ("3", "KP_3"),
                      ("4", "KP_4"), ("5", "KP_5"), ("6", "KP_6"), ("7", "KP_7"),
                      ("8", "KP_8"), ("9", "KP_9"), (".", "KP_PERIOD"),
                      ("+", "KP_PLUS"), ("-", "KP_MINUS"), ("*", "KP_MULTIPLY"),
                      ("/", "KP_DIVIDE"), ("enter", "KP_ENTER")):
    _code = getattr(pygame, "KSCAN_" + _taste, None)
    if _code is not None:
        _SCANCODES[_code] = _name


def numpad_name(ev):
    """Welche Taste des Ziffernblocks ein KEYDOWN ist, oder None."""
    name = _CODES.get(getattr(ev, "key", None))
    if name is None:
        name = _SCANCODES.get(getattr(ev, "scancode", None))
    return name


# Gottmodus. Die Stufen, durch die die 6 schaltet; einzeln an und aus im
# Testmenue. Gilt fuer die Figur, die man gerade steuert.
GOTT = (
    ("AUS", frozenset()),
    ("UNVERWUNDBAR", frozenset({"unverwundbar"})),
    ("UNSTERBLICH", frozenset({"unsterblich"})),
    ("UNSICHTBAR", frozenset({"unsichtbar"})),
    ("ALLES", frozenset({"unverwundbar", "unsichtbar", "munition"})),
)
GOTT_ARTEN = (
    ("unverwundbar", "UNVERWUNDBAR", "KEIN SCHADEN, KEIN RÜCKSTOSS"),
    ("unsterblich", "UNSTERBLICH", "NIMMT SCHADEN, FÄLLT NIE UNTER 1 LEBEN"),
    ("unsichtbar", "UNSICHTBAR FÜR KI", "BOTS UND GEGNER NEHMEN DICH NICHT WAHR"),
    ("munition", "UNENDLICH MUNITION", "MAGAZIN UND VORRAT BLEIBEN VOLL"),
)


# ══════════════════════════════════════════════════════════════════
# Der Spawner
# ══════════════════════════════════════════════════════════════════

def _team_text(v) -> str:
    return K.TEAMS["namen"][v] if 0 <= v < len(K.TEAMS["namen"]) else "FREI"


# Einstellungen, die ein Eintrag haben kann: (Beschriftung, Werte, Text).
OPTIONEN = {
    "anzahl": ("ANZAHL", lambda: list(K.TESTMODUS["anzahlen"]), str),
    "streuung": ("STREUUNG", lambda: list(K.TESTMODUS["streuungen"]),
                 lambda v: "%d PX" % v),
    "team": ("TEAM", lambda: list(range(len(K.TEAMS["namen"]))) + [-1], _team_text),
    "waffe": ("WAFFE", lambda: ["zufall"] + list(K.LOADOUT["auswahl_waffen"]),
              lambda v: "ZUFALL" if v == "zufall" else K.WAFFEN[v]["name"]),
    "leben": ("LEBEN", lambda: list(K.TESTMODUS["leben"]),
              lambda v: "%d %%" % round(v * 100)),
    "ki": ("KI", lambda: [True, False], lambda v: "AN" if v else "AUS"),
    "winkel": ("RICHTUNG", lambda: [0, 90, 180, 270], lambda v: "%d GRAD" % v),
    "zuender": ("ZÜNDER", lambda: ["liegt", "sofort"],
                lambda v: "LIEGT, ZÜNDET" if v == "liegt" else "SOFORT"),
    # Seit 0.34.29: klassische oder zielorientierte KI (bot_goap.py).
    "hirn": ("HIRN", lambda: list(K.GOAP["arten"]), lambda v: v.upper()),
    # Seit 0.34.39: Trupps (trupp.py).
    "groesse": ("GRÖSSE", lambda: list(K.TRUPP["groessen"]), lambda v: "%d MANN" % v),
    "fuehrer": ("ANFÜHRER", lambda: ["funk", "ohne", "keiner"],
                lambda v: {"funk": "MIT FUNK", "ohne": "OHNE FUNK", "keiner": "KEINER"}[v]),
    "mischung": ("WAFFEN", lambda: ["gemischt", "zufall"],
                 lambda v: "GEMISCHT" if v == "gemischt" else "ZUFALL"),
    "wichtig": ("WICHTIG", lambda: [True, False], lambda v: "JA" if v else "NEIN"),
}

# Taste 8 schaltet durch: aus, kurz (Linien und Zustand), Gedanken (dazu
# links die Ziele, der Plan und das Protokoll einer GOAP-Figur).
INFO_STUFEN = ("AUS", "KURZ", "GEDANKEN")


class Eintrag:
    """Ein Ding, das der Spawner setzen kann."""

    def __init__(self, name: str, gruppe: str, optionen, setzen, mehrfach=True):
        self.name = name
        self.gruppe = gruppe
        self.optionen = tuple(optionen)
        self.setzen = setzen          # setzen(testmodus, pos, ebene, werte)
        self.mehrfach = mehrfach      # einmal je Anzahl (sonst einmal ueberhaupt)


def eintraege() -> list:
    """Alles, was sich spawnen laesst - in Gruppen, in Menuereihenfolge.

    HIER GEHOERT JEDES NEUE DING HIN (seit 0.34.28, siehe AGENTS.md):
    eine neue Gegnerart, Waffe, Wurfwaffe, Beute oder ein neues Objekt
    bekommt einen Eintrag, damit es sich im Testmodus setzen laesst.
    Gegner, Bosse und Zielpuppen kommen von selbst aus der Tabelle."""
    raus = [
        Eintrag("BOT", "FIGUREN", ("anzahl", "streuung", "team", "waffe", "leben", "hirn"),
                lambda t, p, e, w: t.bot_setzen(p, e, w)),
        Eintrag("SPIELER, STEHT", "FIGUREN", ("anzahl", "streuung", "team", "leben"),
                lambda t, p, e, w: t.puppe_setzen(p, e, w)),
        Eintrag("SPIELER, ICH", "FIGUREN", ("team", "leben"),
                lambda t, p, e, w: t.ich_setzen(p, e, w), mehrfach=False),
        # Seit 0.34.39: ein ganzer Trupp mit Anfuehrer (trupp.py), und was
        # der naechste Trupp einer Mannschaft tun soll.
        Eintrag("TRUPP", "TRUPPS", ("groesse", "team", "fuehrer", "mischung", "leben"),
                lambda t, p, e, w: t.trupp_setzen(p, e, w), mehrfach=False),
        Eintrag("TRUPP: HALTEN HIER", "TRUPPS", ("team", "wichtig"),
                lambda t, p, e, w: t.trupp_auftrag("halten", p, e, w), mehrfach=False),
        Eintrag("TRUPP: ANGRIFF HIER", "TRUPPS", ("team",),
                lambda t, p, e, w: t.trupp_auftrag("angriff", p, e, w), mehrfach=False),
        Eintrag("TRUPP: FREI", "TRUPPS", ("team",),
                lambda t, p, e, w: t.trupp_auftrag("frei", p, e, w), mehrfach=False),
        # Seit 0.34.41: einigeln, wo der Zeiger ist (sonst nur, wenn er
        # von allen Seiten bedroht wird).
        Eintrag("TRUPP: IGEL HIER", "TRUPPS", ("team",),
                lambda t, p, e, w: t.trupp_auftrag("igel", p, e, w), mehrfach=False),
    ]
    for art in sorted(K.GEGNER):
        raus.append(Eintrag(K.GEGNER[art].get("name", art.upper()), "GEGNER",
                            ("anzahl", "streuung", "leben", "ki", "hirn"),
                            _gegner_setzer(art)))
    for art in sorted(K.BOSSE):
        raus.append(Eintrag(K.BOSSE[art].get("name", art.upper()), "BOSSE",
                            ("anzahl", "streuung", "leben", "ki", "hirn"),
                            _gegner_setzer(art)))
    for art in sorted(K.UEBUNG):
        raus.append(Eintrag(K.UEBUNG[art].get("name", art.upper()), "ZIELE",
                            ("anzahl", "streuung"), _gegner_setzer(art)))
    raus += [
        Eintrag("BUGGY", "OBJEKTE", ("anzahl", "streuung", "winkel"),
                lambda t, p, e, w: t.buggy_setzen(p, e, w)),
        Eintrag("HOTZONE HIER", "OBJEKTE", (),
                lambda t, p, e, w: t.zone_setzen(p, e), mehrfach=False),
        Eintrag("HOTZONE AUS", "OBJEKTE", (),
                lambda t, p, e, w: t.zone_aus(), mehrfach=False),
        Eintrag("MEDKIT", "BEUTE", ("anzahl", "streuung"), _beute_setzer("medkit")),
        Eintrag("MUNITIONSKISTE", "BEUTE", ("anzahl", "streuung"),
                _beute_setzer("munition")),
        Eintrag("RAKETENWERFER", "BEUTE", ("anzahl", "streuung"),
                _beute_setzer("rakete")),
    ]
    for art in ("granate", "rauch", "molotov", "blend"):
        raus.append(Eintrag(K.WAFFEN[art]["name"], "WURF",
                            ("anzahl", "streuung", "zuender"), _wurf_setzer(art)))
    return raus


def _gegner_setzer(art):
    return lambda t, p, e, w: t.gegner_setzen(art, p, e, w)


def _beute_setzer(art):
    return lambda t, p, e, w: t.beute_setzen(art, p, e)


def _wurf_setzer(art):
    return lambda t, p, e, w: t.wurf_setzen(art, p, e, w)


class Leiche(Wesen):
    """Die zweite Leiche eines Bots (seit 0.34.40, VERWUNDETE BOTS): wer
    nach dem Wiederbeleben noch einmal faellt - oder am Boden verblutet -,
    bleibt so liegen (ein eigenes Bild, art._figur_leiche) und ist nach
    K.VERWUNDET["leiche_zeit"] weg. Nichts nimmt sie wahr, nichts trifft sie."""

    fraktion = "leiche"
    schiebt = False
    trefferbar = False
    schatten = False
    radius = 8.0

    def __init__(self, pos, ebene: int, team: int, winkel: float) -> None:
        super().__init__(pos, ebene)
        teams = K.TEAMS["kombi"]
        self.bild = ("leiche_%s" % teams[team]["name"].lower()
                     if 0 <= team < len(teams) else "leiche")
        self.winkel = winkel
        self.rest = K.VERWUNDET["leiche_zeit"]

    def schritt(self, dt: float) -> None:
        self.rest -= dt
        if self.rest <= 0.0:
            self.lebt = False

    def schaden(self, menge, schub=None, von=None) -> None:
        """Eine Leiche nimmt keinen Schaden mehr."""


def _aufhelfen_einmal(k) -> None:
    """Statt Kaempfer.aufhelfen bei Bots mit VERWUNDETE BOTS: einmal geht
    es - danach ist er geschwaecht (weniger Leben, langsamer, zielt
    schlechter, haelt Abstand), und der naechste Fall ist der letzte."""
    type(k).aufhelfen(k)
    v = K.VERWUNDET
    k.wiederbelebt = True
    k.revive_an = False
    k.max_leben = getattr(k, "_max_leben_voll", k.max_leben) * v["danach_max"]
    k.leben = min(k.leben, k.max_leben)
    k.tempo_anteil = v["danach_tempo"]
    hirn = getattr(k, "hirn", None)
    if hirn is not None:
        hirn.geschwaecht = True
        hirn.abstand_mehr = v["danach_abstand"]


def _schaden_mit_gott(k, menge, schub=None, von=None):
    """Statt Kaempfer.schaden, solange der Testmodus die Figur steuert:
    UNSTERBLICH laesst das Leben nie unter 1 fallen."""
    tm = getattr(k, "_testmodus", None)
    if tm is not None and tm.ich is k and not tm.beobachter and "unsterblich" in tm.gott:
        menge = min(float(menge), max(0.0, k.leben - 1.0))
    type(k).schaden(k, menge, schub, von)


class _TestAnzeige(Anzeige):
    """Die gewoehnliche Anzeige der gesteuerten Figur, ohne Rundenuhr und
    ohne Wellenzaehler - beides heisst im Testmodus nichts (Wellen nur,
    wenn sie im Testmenue an sind)."""

    @property
    def _mit_uhr(self) -> bool:
        return False

    def _welle(self, ziel, mitte, y) -> int:
        if not getattr(self.g, "wellen_an", False):
            return y
        return super()._welle(ziel, mitte, y)


# ══════════════════════════════════════════════════════════════════
# Das Gefecht
# ══════════════════════════════════════════════════════════════════

class Testmodus(Gefecht):
    """Ein Gefecht zum Ausprobieren. Siehe oben."""

    ki_stopp = False

    def __init__(self, app, karte: str = "staubtal", zustand: dict | None = None) -> None:
        z = dict(zustand or {})
        # Was den Kartenwechsel ueberlebt (Zeitfaktor, Gottmodus ...).
        self.zeit_stopp = bool(z.get("zeit_stopp", False))
        self.faktor_nr = int(z.get("faktor_nr", list(K.TESTMODUS["zeitfaktoren"]).index(1.0)))
        self.ki_stopp = bool(z.get("ki_stopp", False))
        self.gott = frozenset(z.get("gott", ()))
        self.info = int(z.get("info", 1)) % len(INFO_STUFEN)
        self._denker = None           # wessen Gedanken die INFO zeigt
        self._innen_nr = 0            # was INNENLEBEN im Testmenue ausloest
        self.flug_nr = int(z.get("flug_nr", 1))
        self.wiedereinstieg = bool(z.get("wiedereinstieg", True))
        self.wellen_an = bool(z.get("wellen_an", False))
        self.beute_an = bool(z.get("beute_an", False))
        self.blend_beobachter = bool(z.get("blend_beobachter", False))
        self.ruckeln_beobachter = bool(z.get("ruckeln_beobachter", False))
        # Saubere Ansicht (seit 0.34.32): nur die Welt und ueber jedem Kopf,
        # was er gerade tut - fuer Aufnahmen (werkzeug_aufnahme.py).
        self.sauber = bool(z.get("sauber", False))
        # Was ENTF mit dem tut, was am Zeiger liegt (seit 0.34.33): loeschen
        # (verschwindet, keine Leiche) oder toeten (stirbt wie im Spiel).
        self.entf_toetet = bool(z.get("entf_toetet", False))
        # Verwundete Bots (seit 0.34.40): ein Bot faellt erst zu Boden und
        # kann einmal gerettet werden. Gemeldet: "im Testmodus mal so, dass
        # immer Leichen ... gedroppt werden, nur bei den Bots".
        self.verwundete = bool(z.get("verwundete", True))
        self._sp_werte = dict(z.get("sp_werte", {}))
        self._sp_nr = int(z.get("sp_nr", 0))
        self._welt_schritte = 1
        self._einzel = 0
        self._konto = 0.0
        self._zone_an = False
        self.beobachter = True
        self.spawner_offen = False
        self.menue_offen = False
        self._sp_fokus = "liste"
        self._sp_opt = 0
        self._tm_zeile = 0
        self._zeiger_welt = pygame.Vector2(0, 0)
        self._zuletzt = None          # der zuletzt gespawnte Eintrag (Taste 5)
        self._meldung_tm = ""
        self._meldung_tm_rest = 0.0
        self._naechste_figur = K.TESTMODUS["figur_ab"]
        self.eintraege = eintraege()
        wirt = None
        for versuch in range(20):
            try:
                wirt = netz.Gastgeber(K.TESTMODUS["port"] + versuch, nur_lokal=True)
                break
            except OSError:
                continue
        if wirt is None:
            raise OSError("Kein freier Port fuer den Testmodus")
        super().__init__(app, "BEOBACHTER", gastgeber=wirt, modus="team",
                         karte=karte, lobby=False, heimkehr=False,
                         passwort="%08x" % random.getrandbits(32),
                         regeln={"bots": 0, "schutz": False})
        # Der Beobachter: aus Welt und Kaempferliste heraus (siehe oben).
        self._geist = self.ich
        self.kaempfer.pop(self._geist.nummer, None)
        self.welt.neue[:] = [w for w in self.welt.neue if w is not self._geist]
        self.welt.wesen[:] = [w for w in self.welt.wesen if w is not self._geist]
        self._geist.ebene = 0
        self._geist.unverwundbar = 0.0
        self.hud = _TestAnzeige(self)
        self.melde("TESTMODUS - ZIFFERNBLOCK STEUERT, ESC FÜR DAS MENÜ")

    # ── Was ein Test nicht tut ─────────────────────────────────────
    def _start_masken(self) -> None:
        """Keine Anmeldung, kein Loadout-Dialog."""

    def _runde_buchen(self, werte=None, abgebrochen: bool = False, *a, **kw):
        """Nichts buchen: ein Test ist keine Runde."""

    def _abbruch_buchen(self) -> None:
        pass

    def _zwischenstand_schicken(self, dt: float) -> None:
        pass

    def _bots_fuehren(self, dt: float, sofort: bool = False) -> None:
        """Bots kommen nur aus dem Spawner."""

    def _ende_pruefen(self, dt: float) -> None:
        pass

    def _runden(self, dt: float) -> None:
        pass

    def _wellen(self, dt: float) -> None:
        if self.wellen_an:
            super()._wellen(dt)

    def _beute_nachlegen(self, dt: float) -> None:
        if self.beute_an:
            super()._beute_nachlegen(dt)

    def bergen_an(self) -> bool:
        """Mit VERWUNDETE BOTS darf man Gefallene ziehen und aufheben, auch
        ohne die Regel AUFHELFEN - die abzuschalten hiesse sonst: keiner
        steigt mehr von selbst ein (Gefecht._tote_abrechnen)."""
        return bool(getattr(self, "verwundete", False)) or super().bergen_an()

    def _verbuendet(self, k) -> bool:
        """Der Beobachter hilft niemandem auf - also auch kein "[E] AUF"
        ueber einem Liegenden (seit 0.34.41, gesehen in der Aufnahme)."""
        if self.beobachter:
            return False
        return super()._verbuendet(k)

    def _darf_helfen(self, helfer, liegender) -> bool:
        """Dasselbe fuer den Hinweis ueber dem Kopf: der fragt hier, nicht
        _verbuendet - mit 0.34.42 stand "[E] AUF" darum weiter in der
        Aufnahme (seit 0.34.44)."""
        if self.beobachter and helfer is self.ich:
            return False
        return super()._darf_helfen(helfer, liegender)

    def _regeln_anlegen(self, k) -> None:
        super()._regeln_anlegen(k)
        k.revive_an = (bool(getattr(self, "verwundete", False)) and getattr(k, "ist_bot", False)
                       and not getattr(k, "wiederbelebt", False))
        k.boden_zeit = K.VERWUNDET["boden_zeit"]

    def verwundete_setzen(self, an: bool) -> None:
        """VERWUNDETE BOTS an oder aus - fuer alle Bots, die schon da sind."""
        self.verwundete = bool(an)
        for k in self._bots():
            k.revive_an = self.verwundete and not getattr(k, "wiederbelebt", False)

    def _wieder_einsteigen(self, k) -> None:
        """Ein neues Leben: wieder ganz, und wieder einmal zu retten."""
        k.wiederbelebt = False
        k.tempo_anteil = 1.0
        if hasattr(k, "_max_leben_voll"):
            k.max_leben = k._max_leben_voll
        super()._wieder_einsteigen(k)
        k.revive_an = self.verwundete and getattr(k, "ist_bot", False)

    def _regeln_setzen(self, d: dict) -> None:
        """Wie ein TEAM-Gefecht, aber mit Gegnern und ohne Kreis, bis einer
        gesetzt wird. Eine eigene Kopie: K.MODI selbst bleibt unberuehrt."""
        super()._regeln_setzen(d)
        self.regeln = dict(K.MODI["team"])
        self.regeln.update(gegner=True, zone=bool(getattr(self, "_zone_an", False)))

    # ── Der Beobachter wird von nichts beruehrt ────────────────────
    def _blitz(self, pos, ebene: int, von=None) -> bool:
        if not self.beobachter or self.blend_beobachter:
            return super()._blitz(pos, ebene, von)
        # Nur die Bots: sie sollen geblendet werden wie immer.
        from . import world as welt_modul
        b = K.BLENDEN
        for k in self._bots():
            st = welt_modul.blend_wert(pos, ebene, k, self.welt)
            if st > 0.0 and k.hirn is not None:
                k.hirn.blenden(b["mindest"] + (b["dauer"] - b["mindest"]) * st)
        return False

    def _ruckeln(self, kraft: float, anlass: str = "", pos=None,
                 ebene: int = 0, quelle=None) -> None:
        if self.beobachter and not self.ruckeln_beobachter:
            return
        super()._ruckeln(kraft, anlass, pos, ebene, quelle)

    def _meine_eingabe(self) -> dict:
        ein = super()._meine_eingabe()
        if self.beobachter or self._tm_offen:
            ein.update(will=[0.0, 0.0], feuert=False, zielt=False, nutzen=False,
                       ziehen=False, hb=False, knoepfe=[], waffe=-1)
        return ein

    @property
    def _tm_offen(self) -> bool:
        return self.spawner_offen or self.menue_offen

    @property
    def pausiert(self) -> bool:
        return self._tm_offen or Gefecht.pausiert.fget(self)

    def _bots_steuern(self, dt: float) -> None:
        if not self.ki_stopp:
            super()._bots_steuern(dt)
            return
        # KI aus: jeder Bot steht und tut nichts - dieselbe Eingabe wie
        # ein Gast, der die Hand von der Tastatur nimmt.
        for k in self._bots():
            self._anwenden(k, {"t": "ein", "will": [0.0, 0.0],
                               "ziel": [k.ziel.x, k.ziel.y], "feuert": False,
                               "zielt": False, "knoepfe": []})

    def _tote_abrechnen(self, dt: float) -> None:
        if self.verwundete:
            # Wer jetzt erst richtig tot ist, bleibt als Leiche liegen -
            # ein paar Sekunden lang (Leiche).
            for k in self.kaempfer.values():
                if (not k.lebt and not k.abgerechnet and getattr(k, "ist_bot", False)
                        and getattr(k, "_leiche_gelegt", None) is not k.tode):
                    k._leiche_gelegt = k.tode
                    self._einsetzen(Leiche(k.pos, k.ebene, k.team, k.winkel))
        super()._tote_abrechnen(dt)
        if self.wiedereinstieg:
            return
        for nummer, k in list(self.kaempfer.items()):
            if not k.lebt and k.abgerechnet:
                self.kaempfer.pop(nummer, None)
                if k is self.ich:
                    self.beobachten()

    # ── Die Zeit ───────────────────────────────────────────────────
    @property
    def zeitfaktor(self) -> float:
        f = K.TESTMODUS["zeitfaktoren"]
        return float(f[max(0, min(len(f) - 1, self.faktor_nr))])

    def schritt(self, dt: float) -> None:
        self._meldung_tm_rest = max(0.0, self._meldung_tm_rest - dt)
        self._fliegen(dt)
        self._gott_anwenden()
        if self.zeit_stopp:
            n, self._einzel = self._einzel, 0
        else:
            self._konto += dt * self.zeitfaktor
            n = int(self._konto / dt + 1e-9)
            self._konto -= n * dt
        self._welt_schritte = min(n, max(K.TESTMODUS["hoechstens_schritte"],
                                         K.TESTMODUS["einzelschritt"]))
        super().schritt(dt)
        self._gott_anwenden()

    def _schritt_gastgeber(self, dt: float) -> None:
        """So oft rechnen, wie der Zeitfaktor sagt - auch keinmal."""
        n = self._welt_schritte
        if n <= 0:
            # Die Leitung bleibt offen, gerechnet wird nichts.
            self.gastgeber.annehmen()
            for _nummer, _nachricht in self.gastgeber.holen():
                pass
            self.hinweis = self._meldung_tm if self._meldung_tm_rest > 0 else ""
            return
        for _ in range(n):
            super()._schritt_gastgeber(dt)
        if self._meldung_tm_rest > 0:
            self.hinweis = self._meldung_tm

    def melde(self, text: str, dauer: float = 2.5) -> None:
        self._meldung_tm = text
        self._meldung_tm_rest = dauer
        self.hinweis = text

    # ── Fliegen ────────────────────────────────────────────────────
    def _fliegen(self, dt: float) -> None:
        e = self.app.eingabe
        if not self._tm_offen and self.menue is None:
            self._zeiger_welt = pygame.Vector2(e.ziel_welt(self.kamera, self.ich.pos))
        if not self.beobachter or self._tm_offen or self.menue is not None:
            return
        g = self._geist
        richtung = e.richtung()
        tempo = K.TESTMODUS["flug"][self.flug_nr % len(K.TESTMODUS["flug"])]
        if pygame.key.get_mods() & pygame.KMOD_SHIFT:
            tempo *= K.TESTMODUS["turbo"]
        # Mit Zoom fliegt man im Bild gleich schnell: weiter herausgezoomt
        # ist die Welt kleiner, also muss man in ihr schneller sein.
        tempo *= max(1.0, self.kamera.zoom)
        g.pos += richtung * tempo * dt
        ebene = self.welt.ebene(g.ebene)
        g.pos.x = max(0.0, min(float(ebene.pixel_breite), g.pos.x))
        g.pos.y = max(0.0, min(float(ebene.pixel_hoehe), g.pos.y))
        g.vorher.update(g.pos)
        # Kein Vorausschauen zur Maus: die Kamera bleibt, wo man hinfliegt.
        g.ziel = pygame.Vector2(g.pos)

    # ── Figuren uebernehmen ────────────────────────────────────────
    def uebernehmen(self, k) -> None:
        """Eine Figur steuern. War sie ein Bot, ruht sein Hirn so lange."""
        if not self.beobachter:
            self.beobachten()
        if getattr(k, "ist_bot", False):
            k._bot_hirn = k.hirn
            k.hirn = None
            k.ist_bot = False
        k._testmodus = self
        k.schaden = types.MethodType(_schaden_mit_gott, k)
        self._geist.pos.update(k.pos)
        self.ich = k
        self.meine_nummer = k.nummer
        self.beobachter = False
        self.blick = k.ebene
        self.melde("DU STEUERST %s - 3: ZURÜCK ZUM BEOBACHTER" % k.name)

    def beobachten(self) -> None:
        """Zurueck zum Beobachter. Ein Bot bekommt sein Hirn zurueck, eine
        Figur ohne Hirn bleibt stehen, wo sie ist."""
        k = self.ich
        if k is not None and k is not self._geist:
            self._gott_aufheben(k)
            hirn = getattr(k, "_bot_hirn", None)
            if hirn is not None:
                k.hirn = hirn
                k.ist_bot = True
                k._bot_hirn = None
                hirn.neues_leben()
            self._geist.pos.update(k.pos)
            self._geist.ebene = k.ebene
        self.ich = self._geist
        self.meine_nummer = self._geist.nummer
        self.beobachter = True
        self.melde("BEOBACHTER")

    def _gott_anwenden(self) -> None:
        k = self.ich
        if self.beobachter or k is None:
            return
        if "unverwundbar" in self.gott:
            k.unverwundbar = max(k.unverwundbar, 0.5)
        elif getattr(k, "_gott_unverwundbar", False):
            k.unverwundbar = 0.0
        k._gott_unverwundbar = "unverwundbar" in self.gott
        k.ki_unsichtbar = "unsichtbar" in self.gott
        if "munition" in self.gott:
            for name in k.waffen:
                d = K.WAFFEN[name]
                if d.get("magazin"):
                    k.magazin[name] = d["magazin"]
                k.vorrat[name] = max(k.vorrat.get(name, 0),
                                     K.MUNITION["vorrat"].get(name, 0))

    def _gott_aufheben(self, k) -> None:
        if getattr(k, "_gott_unverwundbar", False):
            k.unverwundbar = 0.0
        k._gott_unverwundbar = False
        k.ki_unsichtbar = False

    # ── Setzen ─────────────────────────────────────────────────────
    def _einsetzen(self, w) -> None:
        """In die Welt - sofort, auch wenn die Zeit steht."""
        self.welt.dazu(w)
        self.welt.wesen.extend(self.welt.neue)
        self.welt.neue.clear()

    def _stelle(self, pos, ebene: int, radius: float, streuung: float, rnd):
        p = pygame.Vector2(pos)
        if streuung > 0:
            p += pygame.Vector2(rnd.uniform(0, streuung), 0).rotate(rnd.uniform(0, 360))
        if not self.welt.frei(p, radius, ebene, True):
            p = pygame.Vector2(self.welt.landeplatz(p, radius, ebene))
        return p

    def _figur_platz(self, k, pos, ebene: int) -> None:
        k.pos.update(pos)
        k.vorher.update(pos)
        k.ebene = ebene
        k.tempo.update(0, 0)
        k.unverwundbar = 0.0

    def _figur_einstellen(self, k, team: int, leben: float) -> None:
        k.team = team
        k.team_wunsch = team
        k.team_fest = True
        k.fraktion = self._fraktion_fuer(k.nummer, team)
        k.max_leben = K.SPIELER["leben"] * float(leben)
        k.leben = k.max_leben

    def bot_setzen(self, pos, ebene: int, w: dict):
        k = self._bot_dazu(w.get("team", 0), w.get("hirn"))
        self._figur_einstellen(k, w.get("team", 0), w.get("leben", 1.0))
        if w.get("waffe", "zufall") != "zufall":
            andere = [x for x in K.LOADOUT["auswahl_waffen"] if x != w["waffe"]]
            lo = {"name": "BOT", "waffen": [w["waffe"], self._bot_rnd.choice(andere)],
                  "wuerfe": ["granate"]}
            k.loadout = lo
            k.waffen = konto_modul.hotbar_aus_loadout(lo)
            k.waffe = k.waffen.index(w["waffe"])
            self._bot_munition(k)
        self._figur_platz(k, pos, ebene)
        self.welt.wesen.extend(self.welt.neue)
        self.welt.neue.clear()
        k.hirn.neues_leben()
        k._max_leben_voll = k.max_leben
        k.aufhelfen = types.MethodType(_aufhelfen_einmal, k)
        k.revive_an = self.verwundete
        return k

    def trupp_setzen(self, pos, ebene: int, w: dict):
        """Ein Trupp aus GOAP-Bots mit einem Anfuehrer (seit 0.34.39). Der
        Anfuehrer traegt einen Repetierer und eine Rauchgranate, mit FUNK
        dazu das Funkgeraet. GEMISCHT: einer mit MG, einer mit Schrot, einer
        mit Scharfschuetzengewehr, der Rest Sturmgewehr."""
        from .trupp import Trupp, trupps
        team = w.get("team", 0)
        liste = trupps(self)
        vergeben = {t.name for t in liste}
        name = next((n for n in K.TRUPP["namen"] if n not in vergeben),
                    "TRUPP %d" % (len(liste) + 1))
        trupp = Trupp(self, team, name)
        n = int(w.get("groesse", 4))
        rnd = random.Random()
        fuehrer = w.get("fuehrer", "funk")
        for i in range(n):
            p = self._stelle(pos + pygame.Vector2(26 * (i % 3) - 26, 26 * (i // 3)),
                             ebene, 12.0, 0.0, rnd)
            ist_fuehrer = i == 0 and fuehrer != "keiner"
            waffe = "zufall"
            if not ist_fuehrer and w.get("mischung", "gemischt") == "gemischt":
                nr = i - (1 if fuehrer != "keiner" else 0)
                mischung = K.TRUPP["mischung"]
                waffe = mischung[nr] if nr < len(mischung) else "sturm"
            k = self.bot_setzen(p, ebene, {"team": team, "hirn": "goap", "waffe": waffe,
                                           "leben": w.get("leben", 1.0)})
            if ist_fuehrer:
                lo = dict(K.TRUPP["fuehrer_loadout"], name="BOT")
                k.loadout = lo
                k.waffen = konto_modul.hotbar_aus_loadout(lo)
                k.waffe = 0
                self._bot_munition(k)
                k.funkgeraet = fuehrer == "funk"
                trupp.fuehrer = k
            k.hirn.trupp = trupp
            trupp.mitglieder.append(k)
        if trupp.fuehrer is None:
            trupp.fuehrer = trupp.mitglieder[0]
        liste.append(trupp)
        return trupp

    def trupp_auftrag(self, art: str, pos, ebene: int, w: dict):
        """Dem naechsten Trupp der Mannschaft einen Auftrag: hier halten,
        hierher angreifen, oder frei suchen."""
        from .trupp import trupps
        team = w.get("team", 0)
        eigene = [t for t in trupps(self) if t.team == team and t.lebende()]
        if not eigene:
            self.melde("KEIN TRUPP IN %s" % _team_text(team))
            return None
        t = min(eigene, key=lambda t: t.lebende()[0].pos.distance_to(pos))
        if art == "frei":
            t.auftrag = dict(art="frei", ort=None, ebene=ebene, wichtig=False)
        else:
            t.auftrag = dict(art=art, ort=pygame.Vector2(pos), ebene=ebene,
                             wichtig=bool(w.get("wichtig", False)) and art == "halten")
        return t

    def puppe_setzen(self, pos, ebene: int, w: dict, name: str = ""):
        nummer = self._naechste_figur
        while nummer in self.kaempfer:
            nummer += 1
        self._naechste_figur = nummer + 1
        k = self._dazu(nummer, name or "PUPPE %d" % (nummer - K.TESTMODUS["figur_ab"] + 1),
                       w.get("team", 0), None)
        self._figur_einstellen(k, w.get("team", 0), w.get("leben", 1.0))
        self._figur_platz(k, pos, ebene)
        self.welt.wesen.extend(self.welt.neue)
        self.welt.neue.clear()
        return k

    def ich_setzen(self, pos, ebene: int, w: dict):
        k = self.puppe_setzen(pos, ebene, w, name="ICH")
        self.uebernehmen(k)
        return k

    def gegner_setzen(self, art: str, pos, ebene: int, w: dict):
        g = KampfGegner(pygame.Vector2(pos), art, ebene, self)
        g.max_leben *= float(w.get("leben", 1.0))
        g.leben = g.max_leben
        g.ki_aus = not w.get("ki", True)
        if w.get("hirn"):
            g.hirn_setzen(w["hirn"])
        self._einsetzen(g)
        if K.ist_boss(art):
            self.boss = g
        return g

    def buggy_setzen(self, pos, ebene: int, w: dict):
        b = Buggy(pygame.Vector2(pos), ebene, float(w.get("winkel", 0)))
        b.start = (pygame.Vector2(b.pos), b.ebene, b.winkel)
        self.fahrzeuge.append(b)
        self._einsetzen(b)
        return b

    def beute_setzen(self, art: str, pos, ebene: int):
        b = KampfBeute(pygame.Vector2(pos), art, ebene, self.kaempfer)
        self._einsetzen(b)
        return b

    def wurf_setzen(self, art: str, pos, ebene: int, w: dict):
        gr = Granate(pygame.Vector2(pos), 0.0, K.WAFFEN[art], ebene, von=None, weite=0.0)
        if w.get("zuender") == "sofort":
            gr.welt = self.welt
            gr.zuenden()
            return gr
        self._einsetzen(gr)
        return gr

    def zone_setzen(self, pos, ebene: int) -> None:
        """Den Kreis hierher. Ab jetzt wird um ihn gekaempft wie in HUEGEL,
        und die Bots wollen hinein."""
        self._zone_an = True
        self.regeln["zone"] = True
        self.kreise = [(ebene, pygame.Vector2(pos), "T")]
        self.kreis_nr = 0
        self.kreis_rest = 1e9         # er wandert nicht
        self._kreis_setzen(0)
        self.zone_stand = [0.0] * len(K.TEAMS["namen"])
        self.zone_halter = -1

    def zone_aus(self) -> None:
        self._zone_an = False
        self.regeln["zone"] = False

    def spawnen(self, eintrag=None, pos=None, ebene=None) -> list:
        """Den Eintrag so oft setzen, wie eingestellt ist. Gibt zurueck,
        was gesetzt wurde."""
        eintrag = eintrag or self.eintraege[self._sp_nr]
        pos = pygame.Vector2(self._zeiger_welt if pos is None else pos)
        ebene = self.blick if ebene is None else ebene
        w = self.werte(eintrag)
        anzahl = int(w.get("anzahl", 1)) if eintrag.mehrfach else 1
        rnd = random.Random()
        raus = []
        for _ in range(anzahl):
            p = self._stelle(pos, ebene, 12.0, float(w.get("streuung", 0)), rnd)
            ding = eintrag.setzen(self, p, ebene, w)
            if ding is not None:
                raus.append(ding)
        self._zuletzt = eintrag
        self.melde("%d x %s" % (max(1, len(raus)), eintrag.name))
        return raus

    def werte(self, eintrag) -> dict:
        """Die eingestellten Werte eines Eintrags (Schluessel -> Wert)."""
        gemerkt = self._sp_werte.setdefault(eintrag.name, {})
        raus = {}
        for o in eintrag.optionen:
            werte = OPTIONEN[o][1]()
            i = gemerkt.get(o, 0)
            raus[o] = werte[max(0, min(len(werte) - 1, i))]
        return raus

    def wert_verstellen(self, eintrag, option: str, schritt: int) -> None:
        gemerkt = self._sp_werte.setdefault(eintrag.name, {})
        werte = OPTIONEN[option][1]()
        gemerkt[option] = (gemerkt.get(option, 0) + schritt) % len(werte)

    # ── Wegnehmen ──────────────────────────────────────────────────
    def alles_weg(self) -> None:
        """Alles aus der Welt ausser der Figur, die man steuert."""
        bleibt = None if self.beobachter else self.ich
        for w in self.welt.wesen + self.welt.neue:
            if w is not bleibt:
                w.lebt = False
        self.welt.neue.clear()
        self.welt.wesen[:] = [w for w in self.welt.wesen if w is bleibt]
        for nummer, k in list(self.kaempfer.items()):
            if k is not bleibt:
                self.kaempfer.pop(nummer, None)
        self.fahrzeuge = []
        self._fahrzeug_warte = []
        self.welt.feuer.clear()
        self.welt.rauch.clear()
        self.welt.partikel.clear()
        self.welt.muendungen.clear()
        self.gegner_offen = []
        self.welle_rest = []
        self.boss = None
        self._stuerme = []
        self._bot_rollen = {}
        self._trupps = []
        self._funknetz = []
        self.zone_aus()
        self.melde("ALLES WEG")

    def am_zeiger(self, pos=None):
        """Das Wesen, das dem Zeiger am naechsten liegt (auf der angeschauten
        Ebene), oder None."""
        pos = pygame.Vector2(self._zeiger_welt if pos is None else pos)
        bestes, weite = None, K.TESTMODUS["greifen"]
        for w in self.welt.wesen + self.welt.neue:
            if not w.lebt or w is self.ich or w.ebene != self.blick:
                continue
            d = w.pos.distance_to(pos) - getattr(w, "radius", 0.0)
            if d < weite:
                bestes, weite = w, d
        return bestes

    def toeten(self, w) -> bool:
        """Sterben lassen wie im Spiel - mit Fleck und Todeslaut (seit 0.34.33).
        Ein Buggy geht hoch. Was nicht sterben kann (Zielpuppe, Beute, eine
        Granate), gibt False zurueck und wird stattdessen geloescht."""
        if getattr(w, "ist_puppe", False):
            return False
        if isinstance(w, Buggy):
            if not w.kaputt:
                w._zerstoeren(None)
            return True
        if not isinstance(w, (Kaempfer, KampfGegner)):
            return False
        if (self.verwundete and getattr(w, "revive_an", False) and w.lebt
                and not getattr(w, "am_boden", False)):
            # Mit VERWUNDETE BOTS erst zu Boden - nochmal ENTF, und er ist tot.
            # So laesst sich das Bergen ausprobieren.
            w.leben = 0.0
            w.sterben(None)
            return True
        for _ in range(2):
            # Zweimal: mit AUFHELFEN liegt einer nach dem ersten Mal nur.
            if w.lebt:
                w.leben = 0.0
                w.sterben(None)
        return True

    def loeschen(self, w) -> None:
        w.lebt = False
        self.welt.wesen[:] = [x for x in self.welt.wesen if x is not w]
        self.welt.neue[:] = [x for x in self.welt.neue if x is not w]
        for nummer, k in list(self.kaempfer.items()):
            if k is w:
                self.kaempfer.pop(nummer, None)
        if w in self.fahrzeuge:
            self.fahrzeuge.remove(w)
        if w is self.boss:
            self.boss = None

    # ── Der Ziffernblock ───────────────────────────────────────────
    def taste(self, name: str) -> None:
        """Eine Taste des Ziffernblocks - gedrueckt oder angeklickt."""
        f = K.TESTMODUS
        if name == "0":
            self.zeit_stopp = not self.zeit_stopp
            self.melde("ZEIT STEHT" if self.zeit_stopp else "ZEIT LÄUFT")
        elif name == ".":
            self.zeit_stopp = True
            self._einzel = f["einzelschritt"]
            self.melde("EIN SCHRITT")
        elif name in ("+", "-"):
            n = len(f["zeitfaktoren"])
            self.faktor_nr = max(0, min(n - 1, self.faktor_nr + (1 if name == "+" else -1)))
            self.melde("ZEIT x%g" % self.zeitfaktor)
        elif name == "/":
            self.ki_stopp = not self.ki_stopp
            self.melde("KI STEHT" if self.ki_stopp else "KI LÄUFT")
        elif name == "*":
            self.alles_weg()
        elif name in ("7", "9"):
            schritt = 1 if name == "9" else -1
            if self.beobachter:
                g = self._geist
                g.ebene = max(0, min(len(self.welt.ebenen) - 1, g.ebene + schritt))
                self.melde("EBENE %d" % g.ebene)
            else:
                self._rad += schritt
        elif name == "8":
            self.info = (self.info + 1) % len(INFO_STUFEN)
            self.melde("INFO: %s" % INFO_STUFEN[self.info])
        elif name == "4":
            self.spawner_offen = not self.spawner_offen
            self.menue_offen = False
        elif name == "5":
            self.spawnen(self._zuletzt or self.eintraege[self._sp_nr])
        elif name == "6":
            stufen = [s for _n, s in GOTT]
            i = stufen.index(self.gott) if self.gott in stufen else 0
            self.gott = stufen[(i + 1) % len(stufen)]
            self.melde("GOTT: %s" % self.gott_name())
        elif name == "1":
            self._schnell_figur("BOT")
        elif name == "2":
            self._schnell_figur("SPIELER, STEHT")
        elif name == "3":
            if not self.beobachter:
                self.beobachten()
            else:
                w = self.am_zeiger()
                if isinstance(w, Kaempfer):
                    self.uebernehmen(w)
                else:
                    self.spawnen(self._eintrag("SPIELER, ICH"))
        elif name == "num":
            # Die NumLock-Taste selbst schaltet nur NumLock; angeklickt
            # oeffnet das Feld das Testmenue (wie Esc).
            self.menue_offen = not self.menue_offen
            self.spawner_offen = False
        elif name == "enter":
            w = self.am_zeiger()
            if w is not None:
                name_w = getattr(w, "name", None) or getattr(w, "art", type(w).__name__).upper()
                if self.entf_toetet and self.toeten(w):
                    self.melde("GETÖTET: %s" % name_w)
                else:
                    self.loeschen(w)
                    self.melde("GELÖSCHT: %s" % name_w)

    def _eintrag(self, name: str):
        for e in self.eintraege:
            if e.name == name:
                return e
        return self.eintraege[0]

    def _schnell_figur(self, name: str) -> None:
        """1 und 2: eine einzelne Figur, mit den Einstellungen aus dem
        Spawner, aber immer nur eine."""
        e = self._eintrag(name)
        w = self.werte(e)
        p = self._stelle(self._zeiger_welt, self.blick, 12.0, 0.0, random.Random())
        e.setzen(self, p, self.blick, w)
        self.melde("1 x %s (%s)" % (name, _team_text(w.get("team", 0))))

    def gott_name(self) -> str:
        for name, stufe in GOTT:
            if stufe == self.gott:
                return name
        return "+".join(sorted(self.gott)).upper() or "AUS"

    def _tastentext(self, name: str) -> tuple:
        """(Aufschrift, an?) einer Taste des Ziffernblocks."""
        if name == "0":
            return ("ZEIT STEHT" if self.zeit_stopp else "ZEIT LÄUFT"), self.zeit_stopp
        if name == "/":
            return ("KI AUS" if self.ki_stopp else "KI AN"), self.ki_stopp
        if name == "8":
            return ("DENKT" if self.info == 2 else "INFO"), bool(self.info)
        if name == "6":
            return "GOTT", bool(self.gott)
        if name == "4":
            return "SPAWN", self.spawner_offen
        if name == "num":
            return "MENÜ", self.menue_offen
        if name == "3":
            return ("BEOB." if not self.beobachter else "ICH"), not self.beobachter
        # Hoechstens sechs Zeichen: mehr passt nicht auf eine Taste.
        return {"*": "LEEREN", "-": "ZEIT-", "+": "ZEIT+",
                "7": "EBENE-", "9": "EBENE+", "5": "WIEDER", "1": "BOT",
                "2": "PUPPE", "enter": "TÖTEN" if self.entf_toetet else "ENTF",
                ".": "EINZEL"}.get(name, ""), False

    def tasten_flaechen(self) -> list:
        """(Name, Rechteck) je Taste, am rechten Bildrand."""
        b, h, l = 44, 22, 2
        x0 = K.GAME_W - 4 * b - 3 * l - 4
        y0 = 104
        raus = []
        for name, sp, ze, br, ho, _a in TASTEN:
            raus.append((name, pygame.Rect(x0 + sp * (b + l), y0 + ze * (h + l),
                                           br * b + (br - 1) * l, ho * h + (ho - 1) * l)))
        return raus

    # ── Ereignisse ─────────────────────────────────────────────────
    def ereignis(self, ev) -> None:
        if ev.type == pygame.KEYDOWN:
            name = numpad_name(ev)
            if name is not None:
                self.taste(name)
                return
            if ev.key in self.app.opt.codes("pause") and self.menue is None:
                if self.spawner_offen:
                    self.spawner_offen = False
                else:
                    self.menue_offen = not self.menue_offen
                return
            if self.spawner_offen:
                self._spawner_taste(ev)
                return
            if self.menue_offen:
                self._menue_taste_tm(ev)
                return
        if ev.type == pygame.MOUSEBUTTONDOWN and ev.button in (1, 3):
            pos = self.app.zu_spiel(ev.pos)
            for name, r in self.tasten_flaechen():
                if r.collidepoint(pos):
                    if ev.button == 1:
                        self.taste(name)
                    self._feuer_sperre = True     # der Klick ist kein Schuss
                    return
            if self.spawner_offen:
                self._spawner_maus(ev, pos)
                return
            if self.menue_offen:
                self._menue_maus_tm(ev, pos)
                return
        if self._tm_offen and ev.type in (pygame.MOUSEWHEEL, pygame.MOUSEBUTTONDOWN):
            return
        super().ereignis(ev)

    # ── Spawner: Bedienung ─────────────────────────────────────────
    SPAWNER = pygame.Rect(6, 96, 300, 258)

    def _spawner_zeilen(self) -> list:
        """("kopf", Gruppe) oder ("eintrag", Nummer), in Menuereihenfolge."""
        raus, gruppe = [], None
        for i, e in enumerate(self.eintraege):
            if e.gruppe != gruppe:
                gruppe = e.gruppe
                raus.append(("kopf", gruppe))
            raus.append(("eintrag", i))
        return raus

    def _spawner_taste(self, ev) -> None:
        e = self.eintraege[self._sp_nr]
        hoch = ev.key in (pygame.K_UP, pygame.K_w)
        runter = ev.key in (pygame.K_DOWN, pygame.K_s)
        links = ev.key in (pygame.K_LEFT, pygame.K_a)
        rechts = ev.key in (pygame.K_RIGHT, pygame.K_d)
        if ev.key == pygame.K_TAB:
            self._sp_fokus = "optionen" if (self._sp_fokus == "liste" and e.optionen) else "liste"
            self._sp_opt = 0
        elif ev.key in (pygame.K_RETURN, pygame.K_SPACE):
            self.spawnen(e)
        elif self._sp_fokus == "liste":
            if hoch or runter:
                self._sp_nr = (self._sp_nr + (1 if runter else -1)) % len(self.eintraege)
            elif rechts and e.optionen:
                self._sp_fokus = "optionen"
                self._sp_opt = 0
        else:
            if not e.optionen:
                self._sp_fokus = "liste"
            elif hoch or runter:
                self._sp_opt = (self._sp_opt + (1 if runter else -1)) % len(e.optionen)
            elif links or rechts:
                self.wert_verstellen(e, e.optionen[self._sp_opt], 1 if rechts else -1)

    def _spawner_flaechen(self) -> tuple:
        """(Zeilen der Liste als (Nummer, Rechteck), Optionen als
        (Schluessel, Rechteck))."""
        r = self.SPAWNER
        zeilen = self._spawner_zeilen()
        sichtbar = (r.height - 40) // 10
        wo = next((i for i, z in enumerate(zeilen) if z == ("eintrag", self._sp_nr)), 0)
        anfang = max(0, min(len(zeilen) - sichtbar, wo - sichtbar // 2))
        liste = []
        for j, z in enumerate(zeilen[anfang:anfang + sichtbar]):
            liste.append((z, pygame.Rect(r.x + 6, r.y + 22 + j * 10, 146, 10)))
        e = self.eintraege[self._sp_nr]
        optionen = [(o, pygame.Rect(r.x + 158, r.y + 34 + i * 12, 136, 11))
                    for i, o in enumerate(e.optionen)]
        return liste, optionen

    def _spawner_maus(self, ev, pos) -> None:
        r = self.SPAWNER
        if not r.collidepoint(pos):
            if ev.button == 1:
                # Ein Klick in die Welt: dort spawnen.
                welt = self.kamera.zu_welt(pos)
                self._zeiger_welt = pygame.Vector2(welt)
                self.spawnen(pos=welt)
                self._feuer_sperre = True
            return
        liste, optionen = self._spawner_flaechen()
        for z, rr in liste:
            if rr.collidepoint(pos) and z[0] == "eintrag":
                self._sp_nr = z[1]
                self._sp_fokus = "liste"
                return
        e = self.eintraege[self._sp_nr]
        for i, (o, rr) in enumerate(optionen):
            if rr.collidepoint(pos):
                self._sp_fokus = "optionen"
                self._sp_opt = i
                self.wert_verstellen(e, o, 1 if ev.button == 1 else -1)
                return

    # ── Testmenue ──────────────────────────────────────────────────
    # Hoch genug fuer alle Zeilen (seit 0.34.32 geprueft: mit den Zeilen aus
    # 0.34.29 lief das Menue unten aus seinem Kasten).
    MENUE = pygame.Rect(150, 22, 340, 316)

    def _menue_zeilen(self) -> list:
        """(Schluessel, Beschriftung, Wert) - was im Testmenue steht."""
        karte = self._karten()[self._karte_nr()]
        raus = [
            ("karte", "KARTE (ENTER LÄDT)", (karte or "testkarte").upper()),
            ("neu", "NEU LADEN", ""),
            ("zeit", "ZEIT", "STEHT" if self.zeit_stopp else "LÄUFT"),
            ("faktor", "ZEITFAKTOR", "x%g" % self.zeitfaktor),
            ("ki", "KI", "STOP" if self.ki_stopp else "AN"),
            ("flug", "FLUGTEMPO", "%d PX/S" % K.TESTMODUS["flug"][self.flug_nr % len(K.TESTMODUS["flug"])]),
            ("info", "INFO (TASTE 8)", INFO_STUFEN[self.info]),
            ("ki_daten", "KI-DATEN NEU LADEN (WESEN/)", ""),
            ("erzwingen", "ZIEL ERZWINGEN (GEDANKEN)", self._erzwungen_text()),
            ("innen", "INNENLEBEN (ENTER: AM GEZEIGTEN)",
             self.INNEN_WAHL[self._innen_nr % len(self.INNEN_WAHL)][1]),
        ]
        for schluessel, name, _hilfe in GOTT_ARTEN:
            raus.append(("gott:" + schluessel, "GOTT: " + name,
                         "AN" if schluessel in self.gott else "AUS"))
        raus += [
            ("wieder", "WIEDEREINSTIEG", "AN" if self.wiedereinstieg else "AUS"),
            ("wellen", "ZOMBIEWELLEN", "AN" if self.wellen_an else "AUS"),
            ("beute", "BEUTE NACHLEGEN", "AN" if self.beute_an else "AUS"),
            ("blend", "BEOBACHTER BLENDEN", "AN" if self.blend_beobachter else "AUS"),
            ("ruckeln", "BEOBACHTER RUCKELN", "AN" if self.ruckeln_beobachter else "AUS"),
            ("sauber", "SAUBERE ANSICHT (NUR AKTIONEN)", "AN" if self.sauber else "AUS"),
            ("entf", "ENTF-TASTE", "TÖTET" if self.entf_toetet else "LÖSCHT"),
            ("verwundete", "VERWUNDETE BOTS (LIEGEN, BERGEN)", "AN" if self.verwundete else "AUS"),
            ("einstellungen", "EINSTELLUNGEN", ""),
            ("hauptmenue", "ZUM HAUPTMENÜ", ""),
        ]
        return raus

    def _karten(self) -> list:
        from . import world as welt_modul
        return [""] + list(welt_modul.karten_liste())

    def _karte_nr(self) -> int:
        karten = self._karten()
        wahl = getattr(self, "_karte_wahl", None)
        if wahl is None:
            wahl = self.karte if self.karte in karten else ""
        return karten.index(wahl) if wahl in karten else 0

    def zustand(self) -> dict:
        """Was ueber einen Kartenwechsel erhalten bleibt."""
        return dict(zeit_stopp=self.zeit_stopp, faktor_nr=self.faktor_nr,
                    ki_stopp=self.ki_stopp, gott=sorted(self.gott), info=self.info,
                    flug_nr=self.flug_nr, wiedereinstieg=self.wiedereinstieg,
                    wellen_an=self.wellen_an, beute_an=self.beute_an,
                    blend_beobachter=self.blend_beobachter,
                    ruckeln_beobachter=self.ruckeln_beobachter, sauber=self.sauber,
                    entf_toetet=self.entf_toetet, verwundete=self.verwundete,
                    sp_werte=self._sp_werte, sp_nr=self._sp_nr)

    def menue_wirken(self, schluessel: str, schritt: int = 1, ausloesen: bool = False) -> None:
        if schluessel == "karte":
            karten = self._karten()
            if ausloesen:
                self.karte_laden(karten[self._karte_nr()])
                return
            self._karte_wahl = karten[(self._karte_nr() + schritt) % len(karten)]
        elif schluessel == "neu" and ausloesen:
            self.karte_laden(self.karte)
        elif schluessel == "zeit":
            self.taste("0")
        elif schluessel == "faktor":
            self.taste("+" if schritt > 0 else "-")
        elif schluessel == "ki":
            self.taste("/")
        elif schluessel == "flug":
            self.flug_nr = (self.flug_nr + schritt) % len(K.TESTMODUS["flug"])
        elif schluessel == "info":
            self.info = (self.info + schritt) % len(INFO_STUFEN)
        elif schluessel == "ki_daten" and ausloesen:
            self.ki_daten_laden()
        elif schluessel == "erzwingen":
            self.ziel_erzwingen(schritt)
        elif schluessel == "innen":
            if ausloesen:
                self.innen_wirken()
            else:
                self._innen_nr = (self._innen_nr + schritt) % len(self.INNEN_WAHL)
        elif schluessel.startswith("gott:"):
            art = schluessel[5:]
            self.gott = frozenset(self.gott ^ {art})
        elif schluessel == "wieder":
            self.wiedereinstieg = not self.wiedereinstieg
        elif schluessel == "wellen":
            self.wellen_an = not self.wellen_an
        elif schluessel == "beute":
            self.beute_an = not self.beute_an
        elif schluessel == "blend":
            self.blend_beobachter = not self.blend_beobachter
        elif schluessel == "ruckeln":
            self.ruckeln_beobachter = not self.ruckeln_beobachter
        elif schluessel == "sauber":
            self.sauber = not self.sauber
        elif schluessel == "entf":
            self.entf_toetet = not self.entf_toetet
        elif schluessel == "verwundete":
            self.verwundete_setzen(not self.verwundete)
        elif schluessel == "einstellungen" and ausloesen:
            from .menues import Einstellungen
            self.menue_offen = False
            self.app.schieben(Einstellungen(self.app))
        elif schluessel == "hauptmenue" and ausloesen:
            self.app.laeuft = False

    def karte_laden(self, karte: str) -> None:
        """Eine andere Karte (oder dieselbe frisch): ein neuer Testmodus mit
        denselben Einstellungen."""
        neu = Testmodus(self.app, karte=karte, zustand=self.zustand())
        self.app.ersetzen(neu)

    def _menue_taste_tm(self, ev) -> None:
        zeilen = self._menue_zeilen()
        self._tm_zeile = max(0, min(len(zeilen) - 1, self._tm_zeile))
        schluessel = zeilen[self._tm_zeile][0]
        if ev.key in (pygame.K_UP, pygame.K_w):
            self._tm_zeile = (self._tm_zeile - 1) % len(zeilen)
        elif ev.key in (pygame.K_DOWN, pygame.K_s):
            self._tm_zeile = (self._tm_zeile + 1) % len(zeilen)
        elif ev.key in (pygame.K_LEFT, pygame.K_a):
            self.menue_wirken(schluessel, -1)
        elif ev.key in (pygame.K_RIGHT, pygame.K_d):
            self.menue_wirken(schluessel, 1)
        elif ev.key in (pygame.K_RETURN, pygame.K_SPACE):
            self.menue_wirken(schluessel, 1, ausloesen=True)

    def _menue_flaechen(self) -> list:
        r = self.MENUE
        return [pygame.Rect(r.x + 8, r.y + 26 + i * 12, r.width - 16, 11)
                for i in range(len(self._menue_zeilen()))]

    def _menue_maus_tm(self, ev, pos) -> None:
        zeilen = self._menue_zeilen()
        for i, rr in enumerate(self._menue_flaechen()):
            if rr.collidepoint(pos):
                self._tm_zeile = i
                self.menue_wirken(zeilen[i][0], 1 if ev.button == 1 else -1,
                                  ausloesen=ev.button == 1)
                return

    # ── Zeichnen ───────────────────────────────────────────────────
    def _funk_hoerbar(self, k) -> bool:
        """Der Beobachter liest den Funk beider Mannschaften mit - ausser in
        der sauberen Ansicht: dort steht ueber dem Kopf nur die Aktion."""
        return not self.sauber

    def _welt_bild(self, ziel, misch: float) -> None:
        if not self.beobachter:
            super()._welt_bild(ziel, misch)
            return
        # Keine Ziellinie am Beobachter: er hat keine Waffe in der Welt.
        g = self._geist
        g.lebt = False
        try:
            super()._welt_bild(ziel, misch)
        finally:
            g.lebt = True

    def _anzeige(self, ziel) -> None:
        if not self.beobachter:
            super()._anzeige(ziel)

    def sicht_welt(self):
        """In der sauberen Ansicht kein Nebel: herausgezoomt zeichnet das
        Gefecht Figuren sonst nur im normalen Bild um den Beobachter - am
        Rand fehlten sie in den ersten Aufnahmen ganz."""
        if self.sauber:
            return None
        return super().sicht_welt()

    def zeichnen(self, ziel, alpha: float) -> None:
        super().zeichnen(ziel, alpha)
        if self.sauber:
            # Nur die Welt und die Aktionen. Spawner und Menue bleiben
            # bedienbar, wenn man sie oeffnet (Esc, Taste 4). Wer funkt,
            # ist auch hier zu sehen (seit 0.34.39; die Wellen liegen seit 0.34.46
            # am Boden, _funkwellen_zeichnen).
            self._aktionen_zeichnen(ziel)
            if self.spawner_offen:
                self._spawner_zeichnen(ziel)
            if self.menue_offen:
                self._testmenue_zeichnen(ziel)
            return
        if self.info:
            self._info_zeichnen(ziel)
            self._trupps_zeichnen(ziel)
            self._funk_liste_zeichnen(ziel)
        if self.info == 2:
            self._gedanken_zeichnen(ziel)
        self._zeiger_zeichnen(ziel)
        self._status_zeichnen(ziel)
        self._numpad_zeichnen(ziel)
        if self.spawner_offen:
            self._spawner_zeichnen(ziel)
        if self.menue_offen:
            self._testmenue_zeichnen(ziel)

    def _zeiger_zeichnen(self, ziel) -> None:
        """Wo gespawnt wird: ein Fadenkreuz mit Weltkoordinaten."""
        p = self.kamera.zu_bild(self._zeiger_welt)
        x, y = int(p.x), int(p.y)
        pygame.draw.line(ziel, K.C_AMBER, (x - 6, y), (x - 2, y))
        pygame.draw.line(ziel, K.C_AMBER, (x + 2, y), (x + 6, y))
        pygame.draw.line(ziel, K.C_AMBER, (x, y - 6), (x, y - 2))
        pygame.draw.line(ziel, K.C_AMBER, (x, y + 2), (x, y + 6))
        SCHRIFT.zeichnen(ziel, "%d,%d E%d" % (self._zeiger_welt.x, self._zeiger_welt.y,
                                               self.blick), x + 8, y + 4, K.C_MUTED, 1)
        w = self.am_zeiger()
        if w is not None:
            q = self.kamera.zu_bild(w.pos)
            pygame.draw.circle(ziel, K.C_RED, (int(q.x), int(q.y)),
                               int(getattr(w, "radius", 8) / self.kamera.zoom) + 4, 1)

    def _status_zeichnen(self, ziel) -> None:
        bots = len(self._bots())
        gegner = sum(1 for w in self.welt.wesen
                     if isinstance(w, KampfGegner) and w.lebt)
        zeilen = [
            ("TESTMODUS", K.C_AMBER),
            ("ZEIT %s x%g" % ("STEHT" if self.zeit_stopp else "LÄUFT", self.zeitfaktor),
             K.C_RED if self.zeit_stopp else K.C_CREAM),
            ("KI %s" % ("STOP" if self.ki_stopp else "AN"),
             K.C_RED if self.ki_stopp else K.C_CREAM),
            ("GOTT %s" % self.gott_name(), K.C_TEAL if self.gott else K.C_MUTED),
            (("BEOBACHTER E%d" % self._geist.ebene) if self.beobachter
             else ("STEUERE %s" % self.ich.name), K.C_CREAM),
            ("BOTS %d  GEGNER %d  WESEN %d" % (bots, gegner, len(self.welt.wesen)),
             K.C_MUTED),
        ]
        # Als Beobachter oben rechts, wo sonst nichts steht; mit Figur
        # links unter der Minikarte (rechts oben steht dann die Rangliste).
        if self.beobachter:
            x, y = K.GAME_W - 186, 30
        elif self.spawner_offen:
            return
        else:
            x, y = 6, 100
        for text, farbe in zeilen:
            SCHRIFT.zeichnen(ziel, text, x, y, farbe, 1)
            y += 10

    def _numpad_zeichnen(self, ziel) -> None:
        for name, r in self.tasten_flaechen():
            text, an = self._tastentext(name)
            glyph = next(a for n, *_x, a in TASTEN if n == name)
            pygame.draw.rect(ziel, (24, 30, 26) if an else (12, 10, 9), r)
            pygame.draw.rect(ziel, K.C_TEAL if an else K.C_MUTED_DK, r, 1)
            SCHRIFT.zeichnen(ziel, glyph, r.x + 3, r.y + 2,
                             K.C_AMBER if an else K.C_MUTED, 1)
            SCHRIFT.zeichnen(ziel, ui.kuerzen(text, r.width - 4), r.centerx,
                             r.bottom - 10, K.C_CREAM if an else K.C_MUTED, 1,
                             ausrichtung="mitte")

    @staticmethod
    def _klassisch_zustand(h) -> str:
        """Was ein Bot mit der klassischen KI gerade tut, in einem Wort."""
        zustand = "UNTERWEGS"
        if h.ziel is not None:
            zustand = "KAMPF"
        if h.druck_rest > 0:
            zustand = "DRUCK"
        if h.taktik is not None:
            zustand = "FLANKE"
        if h.deckung_ort is not None:
            zustand = "DECKUNG"
        if h.sturm is not None:
            zustand = "STURM:%s" % h.sturm["phase"].upper()
        return zustand

    def aktion_text(self, w) -> str:
        """Was ein Wesen gerade tut, fuer die saubere Ansicht: bei GOAP die
        Aktion, bei einem klassischen Bot sein Zustand, sonst nichts."""
        h = getattr(w, "hirn", None)
        if h is None or self.ki_stopp or getattr(w, "ki_aus", False):
            return ""
        if getattr(w, "am_boden", False):
            return "VERWUNDET"            # er denkt nicht mehr (seit 0.34.46)
        gehirn = getattr(h, "gehirn", None)
        if gehirn is not None:
            return gehirn.aktion.name.replace("_", " ").upper() if gehirn.aktion else ""
        if getattr(w, "ist_bot", False):
            return self._klassisch_zustand(h)
        return ""

    def _aktionen_zeichnen(self, ziel) -> list:
        """Ueber jedem Kopf, was er gerade tut - in einem dunklen Feld, damit
        es auf Sand und Fels gleich gut lesbar ist. Liegen zwei Felder
        aufeinander (ein Rudel), rueckt das spaetere hoch; findet es keinen
        Platz, faellt es weg - lieber eines weniger als ein Knaeuel."""
        kam = self.kamera
        belegt = []
        # Bots zuerst: wird es eng, faellt eher ein Zombie aus einem Rudel weg.
        for w in sorted(self.welt.wesen,
                        key=lambda w: (not getattr(w, "ist_bot", False), -w.pos.y)):
            if not w.lebt or w.ebene != self.blick:
                continue
            text = self.aktion_text(w)
            if not text:
                continue
            p = kam.zu_bild(w.pos)
            # Ueber dem Namensschild der Bots, bei Gegnern ueber dem Balken.
            hoch = 30 if getattr(w, "ist_bot", False) else 22
            x, y = int(p.x), int(p.y - getattr(w, "radius", 8) / kam.zoom) - hoch
            b = SCHRIFT.breite(text) + 6
            feld = pygame.Rect(x - b // 2, y - 2, b, 10)
            for _ in range(K.TESTMODUS["aktion_ausweichen"]):
                if feld.collidelist(belegt) < 0:
                    break
                feld.y -= 11
            if feld.collidelist(belegt) >= 0:
                continue
            belegt.append(feld)
            y = feld.y + 2
            pygame.draw.rect(ziel, (10, 8, 7), feld)
            team = getattr(w, "team", -1)
            farbe = ((255, 196, 150) if team == 0 else (170, 210, 255) if team == 1
                     else (230, 150, 140))
            SCHRIFT.zeichnen(ziel, text, x, y, farbe, 1, ausrichtung="mitte")
        return belegt

    def _info_zeichnen(self, ziel) -> None:
        """Was die KI gerade denkt: Linien zu Ziel, Flanke, Deckung und
        Sammelpunkt, darueber der Zustand."""
        kam = self.kamera
        for k in self._bots():
            if k.ebene != self.blick or not k.lebt or k.hirn is None:
                continue
            h = k.hirn
            p = kam.zu_bild(k.pos)
            zustand = self._klassisch_zustand(h)
            if h.ziel is not None:
                pygame.draw.line(ziel, K.C_RED, p, kam.zu_bild(h.ziel.pos), 1)
            if h.taktik is not None:
                pygame.draw.line(ziel, K.C_AMBER, p, kam.zu_bild(h.taktik["ort"]), 1)
            if h.deckung_ort is not None:
                pygame.draw.line(ziel, K.C_TEAL, p, kam.zu_bild(h.deckung_ort), 1)
            if h.sturm is not None:
                pygame.draw.line(ziel, (120, 170, 255), p, kam.zu_bild(h.sturm["sammel"]), 1)
            gehirn = getattr(h, "gehirn", None)
            if gehirn is not None:
                # GOAP: was er will und was er dafuer gerade tut.
                zustand = "%s > %s" % (
                    gehirn.ziel.name.upper() if gehirn.ziel else "-",
                    gehirn.aktion.name.upper() if gehirn.aktion else "-")
            if h.unterdrueckt > 0:
                zustand += " (NIEDERGEH.)"
            SCHRIFT.zeichnen(ziel, zustand, int(p.x), int(p.y) + 14, K.C_AMBER, 1,
                             ausrichtung="mitte")
            innen = getattr(h, "innen", None)
            if innen is not None:
                self._innen_zeichnen(ziel, h, innen, p)
        for w in self.welt.wesen:
            if isinstance(w, KampfGegner) and w.lebt and w.ebene == self.blick:
                ziel_w = getattr(w, "_ziel", None)
                if ziel_w is not None and ziel_w.lebt:
                    pygame.draw.line(ziel, (150, 40, 40), kam.zu_bild(w.pos),
                                     kam.zu_bild(ziel_w.pos), 1)
                q = kam.zu_bild(w.pos)
                if w.ki_aus or self.ki_stopp:
                    SCHRIFT.zeichnen(ziel, "KI AUS", int(q.x), int(q.y) + 12,
                                     K.C_MUTED, 1, ausrichtung="mitte")
                elif w.hirn is not None and w.hirn.gehirn is not None:
                    gh = w.hirn.gehirn
                    SCHRIFT.zeichnen(ziel, "%s > %s" % (
                        gh.ziel.name.upper() if gh.ziel else "-",
                        gh.aktion.name.upper() if gh.aktion else "-"),
                        int(q.x), int(q.y) + 12, (200, 120, 110), 1, ausrichtung="mitte")

    def _innen_zeichnen(self, ziel, h, innen, p) -> None:
        """Seit 0.34.38: unter dem Zustand ein Balken fuer den Stress, die
        Stufe der Zuversicht als Buchstabe, PANIK oder SCHRECK - und graue
        Punkte, wo er etwas gehoert hat."""
        kam = self.kamera
        x, y = int(p.x) - 12, int(p.y) + 24
        pygame.draw.rect(ziel, (30, 26, 22), (x, y, 24, 3))
        breite = int(round(24 * innen.stress))
        if breite > 0:
            farbe = (K.C_TEAL if innen.stress < 0.4 else K.C_AMBER if innen.stress < 0.75
                     else K.C_RED)
            pygame.draw.rect(ziel, farbe, (x, y, breite, 3))
        zeichen = innen.stufen_name()[0]
        text = zeichen
        if innen.panik:
            text = "PANIK"
        elif innen.erschrocken:
            text = "SCHRECK"
        SCHRIFT.zeichnen(ziel, text, x + 28, y - 3,
                         K.C_RED if innen.panik or innen.erschrocken else K.C_MUTED, 1)
        for ort, ebene, _zeit, _art in getattr(h, "lagebild", ()):
            if ebene != self.blick:
                continue
            q = kam.zu_bild(ort)
            pygame.draw.circle(ziel, (130, 130, 120), (int(q.x), int(q.y)), 3, 1)
            pygame.draw.line(ziel, (70, 70, 64), p, q, 1)

    # ── Trupps und Funk (seit 0.34.39) ──────────────────────────────
    def _trupps_zeichnen(self, ziel) -> None:
        """Je Trupp: die Frontlinie, fuer jeden seine Stellung (ein
        kleines Kaestchen mit Linie), ueber dem Anfuehrer Name und Zustand."""
        from .trupp import trupps
        kam = self.kamera
        for t in trupps(self):
            leute = [m for m in t.lebende() if m.ebene == self.blick]
            if not leute:
                continue
            farbe = (255, 196, 150) if t.team == 0 else (170, 210, 255)
            f = t.front
            if f is not None and f["ebene"] == self.blick:
                a = kam.zu_bild(f["linie"] + f["quer"] * (f["breite"] / 2))
                b = kam.zu_bild(f["linie"] - f["quer"] * (f["breite"] / 2))
                pygame.draw.line(ziel, farbe, a, b, 1)
                m_ = kam.zu_bild(f["linie"])
                pygame.draw.line(ziel, farbe, m_, kam.zu_bild(f["linie"] + f["richtung"] * 20), 1)
            for m in leute:
                q = t.stellung(m)
                if q is None:
                    continue
                pq = kam.zu_bild(q)
                pygame.draw.rect(ziel, farbe, (int(pq.x) - 2, int(pq.y) - 2, 4, 4), 1)
                pygame.draw.line(ziel, (90, 80, 70), kam.zu_bild(m.pos), pq, 1)
            if t.zustand == "igel" and t.igel is not None and t.igel["ebene"] == self.blick:
                # Der Platz, an dem er sich einigelt (seit 0.34.41).
                q = kam.zu_bild(t.igel["ort"])
                pygame.draw.circle(ziel, farbe, (int(q.x), int(q.y)), 8, 1)
                SCHRIFT.zeichnen(ziel, "IGEL", int(q.x), int(q.y) - 4, farbe, 1, ausrichtung="mitte")
            if t.zustand == "engstelle" and t.enge is not None and t.enge["ebene"] == self.blick:
                e_ = t.enge
                q = kam.zu_bild(e_["ort"])
                quer = pygame.Vector2(-e_["achse"].y, e_["achse"].x) * (e_["breite"] / 2)
                pygame.draw.line(ziel, K.C_RED, kam.zu_bild(e_["ort"] + quer),
                                 kam.zu_bild(e_["ort"] - quer), 2)
                SCHRIFT.zeichnen(ziel, "ENGSTELLE %d PX" % e_["breite"], int(q.x), int(q.y) + 6,
                                 K.C_RED, 1, ausrichtung="mitte")
            for m in leute:
                bl = t.blick_fuer(m)
                if bl is not None:
                    a_ = kam.zu_bild(m.pos)
                    r_ = (bl - m.pos)
                    if r_.length_squared() > 1.0:
                        pygame.draw.line(ziel, (120, 110, 70), a_,
                                         kam.zu_bild(m.pos + r_.normalize() * 28), 1)
            b = t.bergung
            if b is not None and b["opfer"].ebene == self.blick:
                # Wer liegt, und ob der Trupp es fuer sicher genug haelt, ihn
                # zu holen (seit 0.34.40); Linien von den Rettern zu ihm.
                q = kam.zu_bild(b["opfer"].pos)
                farbe_b = K.C_TEAL if b["sicher"] else K.C_RED
                pygame.draw.circle(ziel, farbe_b, (int(q.x), int(q.y)), 14, 1)
                for m in leute:
                    if m.nummer in b["retter"]:
                        pygame.draw.line(ziel, farbe_b, kam.zu_bild(m.pos), q, 1)
                SCHRIFT.zeichnen(ziel, "BERGEN: %s (%d)" % ("SICHER" if b["sicher"] else "ZU GEFÄHRLICH",
                                                            b["bedrohung"]),
                                 int(q.x), int(q.y) + 16, farbe_b, 1, ausrichtung="mitte")
            fuehrer = t.fuehrer if t.fuehrer in leute else leute[0]
            p = kam.zu_bild(fuehrer.pos)
            text = "%s %s%s" % (t.name, t.zustand.upper(),
                                " (FUNK)" if getattr(fuehrer, "funkgeraet", False) else "")
            if t.hilfe is not None:
                text += " > %s" % t.hilfe["fuer"].name
            SCHRIFT.zeichnen(ziel, text, int(p.x), int(p.y) + 34, farbe, 1, ausrichtung="mitte")

    def _kreis_zeichnen(self, flaeche, ebene: int, ecke) -> None:
        """Auf den Boden jeder Ebene, noch unter die Figuren: dazu die
        Funkwellen (seit 0.34.46)."""
        super()._kreis_zeichnen(flaeche, ebene, ecke)
        self._funkwellen_zeichnen(flaeche, ebene, ecke)

    def _funkwellen_zeichnen(self, flaeche, ebene: int, ecke) -> None:
        """Wer funkt, sendet Wellen (seit 0.34.43). Seit 0.34.46 klein, rot
        und am Boden unter ihm, wie ein Teil der Figur. Gemeldet: "auf rot
        und deutlich kleiner ... als Teil des Bots selber erkennbar ... ein
        bisschen mehr zum Design passend". Solange er spricht, laufen Ringe
        von ihm weg; beim Anfuehrer, der den Spruch bekommt, laeuft ein Ring
        nach innen. Was gesagt wurde, steht in INFO unten links."""
        from .trupp import trupps
        jetzt = self.welt.zeit
        t = K.TESTMODUS
        weg = t["welle_weite"] - t["welle_start"]
        for k in self._bots():
            laeuft = getattr(k.hirn, "funk_laeuft", None)
            if laeuft is None or not k.lebt or k.ebene != ebene or laeuft.get("phase") == "weg":
                continue                      # erst, wenn er spricht (nicht auf dem Weg dorthin)
            seit = jetzt - laeuft["anfang"]
            for i in range(int(seit / t["welle_takt"]) + 1):
                r = t["welle_start"] + (seit - i * t["welle_takt"]) * t["welle_tempo"]
                self._welle_ring(flaeche, k.pos - ecke, r)
        for tr in trupps(self):
            alter = jetzt - getattr(tr, "empfangen_zeit", -1e9)
            f = tr.fuehrer
            if 0.0 <= alter < t["empfang_zeigen"] and f is not None and f.lebt and f.ebene == ebene:
                r = t["welle_weite"] - weg * alter / t["empfang_zeigen"]
                self._welle_ring(flaeche, f.pos - ecke, r)

    def _welle_ring(self, flaeche, p, radius: float) -> bool:
        """Ein Ring der Funkwelle in Weltpixeln, scharf wie die Figuren, mit
        einer dunklen Kante. Seit 0.34.48 nur in Rot (hell, dann tiefer) und
        gestrichelt, die Striche drehen sich - etwas abstrakt, damit man ihn
        nicht fuer etwas in der Welt haelt (gemeldet: "eher rot ... etwas
        abstrakt und von der Welt unterschiedlich"). False, wenn er schon
        (oder noch) unsichtbar ist."""
        t = K.TESTMODUS
        if not (t["welle_start"] <= radius <= t["welle_weite"]):
            return False
        anteil = (radius - t["welle_start"]) / max(1.0, t["welle_weite"] - t["welle_start"])
        farbe = t["welle_farben"][min(len(t["welle_farben"]) - 1, int(anteil * len(t["welle_farben"])))]
        r = int(radius)
        n = t["welle_striche"]
        dreh = self.welt.zeit * t["welle_dreh"]
        for mitte, f, breite in (((int(p.x), int(p.y) + 1), K.C_VOID, 1), ((int(p.x), int(p.y)), farbe, 1)):
            feld = pygame.Rect(mitte[0] - r, mitte[1] - r, 2 * r, 2 * r)
            for i in range(n):
                a = dreh + i * 2.0 * math.pi / n
                pygame.draw.arc(flaeche, f, feld, a, a + math.pi / n, breite)
        return True

    def _funk_liste_zeichnen(self, ziel) -> None:
        """Unten links die letzten Funksprueche, der neueste unten."""
        netz = getattr(self, "_funknetz", None) or []
        if not netz or self.info == 2:
            return
        jetzt = self.welt.zeit
        y = K.GAME_H - 14 - 10 * min(5, len(netz))
        for spruch in netz[-5:]:
            alt = jetzt - spruch.zeit
            SCHRIFT.zeichnen(ziel, "%5.0fs  %s" % (-alt, spruch.text), 6, y,
                             K.C_TEAL if alt < 4.0 else K.C_MUTED, 1)
            y += 10

    # Was INNENLEBEN im Testmenue mit der gezeigten Figur tut (seit 0.34.38).
    INNEN_WAHL = (("panik", "PANIK"), ("stress", "STRESS +0,3"), ("kamerad", "KAMERAD FÄLLT"),
                  ("granate", "GRANATE NEBEN IHM"), ("ruhe", "RUHE"))

    def innen_wirken(self, art: str | None = None) -> bool:
        """Das Innenleben der gezeigten GOAP-Figur verstellen: Panik, Stress,
        ein Ereignis - oder alles zur Ruhe. False ohne Bot mit Innenleben."""
        d = self.denker()
        innen = getattr(getattr(d, "hirn", None), "innen", None)
        if innen is None:
            self.melde("KEIN GOAP-BOT AM ZEIGER")
            return False
        art = art or self.INNEN_WAHL[self._innen_nr % len(self.INNEN_WAHL)][0]
        if art == "panik":
            innen.panik_setzen()
        elif art == "stress":
            innen.stress = min(1.0, innen.stress + 0.3)
        elif art == "ruhe":
            innen.beruhigen()
        else:
            innen.ereignis(art)
        self.melde("%s: %s (STRESS %.2f)" % (d.name, art.upper(), innen.stress))
        return True

    # ── Gedanken (GOAP, seit 0.34.29) ─────────────────────────────────
    def _denkende(self) -> list:
        """Alles mit einem GOAP-Gehirn: Bots und (seit 0.34.30) Gegner."""
        return [w for w in self.welt.wesen
                if w.lebt and getattr(getattr(w, "hirn", None), "gehirn", None) is not None]

    def denker(self):
        """Wessen Gedanken die INFO zeigt: die GOAP-Figur am Zeiger, sonst
        die zuletzt gezeigte, sonst die erste, die es gibt."""
        w = self.am_zeiger()
        if w is not None and getattr(getattr(w, "hirn", None), "gehirn", None) is not None:
            self._denker = w
        denkende = self._denkende()
        if self._denker in denkende:
            return self._denker
        self._denker = denkende[0] if denkende else None
        return self._denker

    def _erzwungen_text(self) -> str:
        d = self._denker
        gehirn = getattr(getattr(d, "hirn", None), "gehirn", None)
        if gehirn is None:
            return "KEINE GOAP-FIGUR"
        return (gehirn.erzwungen or "-").upper()

    def ziel_erzwingen(self, schritt: int = 1) -> None:
        """Der gezeigten Figur ein Ziel aufzwingen, egal wie dringlich -
        oder wieder frei denken lassen ("-")."""
        d = self.denker()
        if d is None:
            self.melde("KEINE GOAP-FIGUR (BOT ODER GEGNER MIT HIRN GOAP)")
            return
        gehirn = d.hirn.gehirn
        namen = [None] + [z.name for z in gehirn.ziele]
        i = namen.index(gehirn.erzwungen) if gehirn.erzwungen in namen else 0
        gehirn.erzwungen = namen[(i + schritt) % len(namen)]
        gehirn.plan = []
        self.melde("%s: ZIEL %s" % (getattr(d, "name", None) or d.art.upper(),
                                     (gehirn.erzwungen or "FREI").upper()))

    def ki_daten_laden(self) -> None:
        """wesen/*.txt neu lesen und jeder GOAP-Figur ein neues Gehirn
        geben - aendern und ausprobieren, ohne neu zu starten."""
        from . import wesen_daten
        d = wesen_daten.neu_laden()
        n = 0
        for w in self._denkende():
            w.hirn.gehirn_neu()
            n += 1
        fehler = wesen_daten.pruefen(d)
        self.melde("KI-DATEN: %d FEHLER" % len(fehler) if fehler
                   else "KI-DATEN NEU GELADEN (%d FIGUREN)" % n)

    def _gedanken_zeichnen(self, ziel) -> None:
        """Links: Merkmale, Ziele mit Dringlichkeit, Plan, Fakten und das
        Protokoll der GOAP-Figur, die gerade gezeigt wird."""
        d = self.denker()
        r = pygame.Rect(4, 28, 252, K.GAME_H - 56)
        if d is None:
            SCHRIFT.zeichnen(ziel, "GEDANKEN: KEINE GOAP-FIGUR - HIRN GOAP SPAWNEN",
                             r.x + 2, r.y, K.C_MUTED, 1)
            return
        h = d.hirn
        gehirn = h.gehirn
        bild = pygame.Surface(r.size, pygame.SRCALPHA)
        bild.fill((8, 6, 5, 200))
        ziel.blit(bild, r.topleft)
        pygame.draw.rect(ziel, K.C_MUTED_DK, r, 1)
        x, y = r.x + 4, r.y + 4
        breit = r.width - 8

        def zeile(text, farbe=K.C_CREAM, einzug=0):
            nonlocal y
            if y > r.bottom - 10:
                return
            SCHRIFT.zeichnen(ziel, ui.kuerzen(text.replace("_", " "), breit - einzug),
                             x + einzug, y, farbe, 1)
            y += 9

        name = getattr(d, "name", None) or d.daten.get("name", d.art.upper())
        zeile("%s - %s" % (name, h.spezies.upper()), K.C_AMBER)
        zeile("  ".join("%s %.2f" % (n, v) for n, v in sorted(gehirn.merkmale.items())),
              K.C_MUTED)
        if gehirn.erzwungen:
            zeile("ERZWUNGEN: %s" % gehirn.erzwungen, K.C_RED)
        innen = getattr(h, "innen", None)
        if innen is not None:
            v = innen.verhaeltnis
            zeile("STRESS %.2f  ZUVERSICHT %s%s" % (
                innen.stress, innen.stufen_name(), "" if v is None else " (%.2f)" % v),
                K.C_RED if innen.panik else K.C_CREAM)
            zeile("PANIK %.1f  SCHRECK %.1f  EINGESCH. %.1f  ZULETZT %s" % (
                innen.panik_rest, innen.schreck_rest, innen.eingeschossen,
                innen.zuletzt or "-"), K.C_MUTED)
            zeile("GEBUNDEN %.1f  BEDENKT %.1f  GEHOERT %d%s" % (
                gehirn.gebunden, getattr(h, "_bedenk_rest", 0.0),
                len(getattr(h, "lagebild", ())),
                "  GESCHWÄCHT" if getattr(h, "geschwaecht", False) else ""), K.C_MUTED)
        t = getattr(h, "trupp", None)
        if t is not None:
            rolle = ("ANFÜHRER" if t.fuehrer is d else
                     "FLANKE" if d.nummer in t.flanker else
                     "WELLE" if d.nummer in t.welle else "MANN")
            zeile("TRUPP %s: %s, %s, ZUV %d, LAGE %d%s" % (
                t.name, rolle, t.zustand.upper(), t.zuversicht, len(t.lage),
                ", HILFE > %s" % t.hilfe["fuer"].name if t.hilfe else ""), K.C_TEAL)
        zeile("PLAN: %s" % (" > ".join(a.name for a in gehirn.plan) or "-"), K.C_TEAL)
        y += 3
        zeile("ZIELE", K.C_MUTED_DK)
        for z in sorted(gehirn.ziele, key=lambda z: -gehirn.dringlichkeiten.get(z.name, 0.0)):
            wert = gehirn.dringlichkeiten.get(z.name, 0.0)
            erledigt = goap_erfuellt(gehirn.fakten, z.will)
            farbe = (K.C_AMBER if z is gehirn.ziel else
                     K.C_MUTED_DK if wert <= 0 or erledigt else K.C_CREAM)
            zeile("%s %3d %s%s" % (">" if z is gehirn.ziel else " ", round(wert), z.name,
                                   "  (ERFÜLLT)" if erledigt and wert > 0 else ""), farbe, 4)
        y += 3
        zeile("FAKTEN", K.C_MUTED_DK)
        wahr = [n for n, v in sorted(gehirn.fakten.items()) if v]
        stueck = ""
        for n in wahr:
            probe = (stueck + "  " + n) if stueck else n
            if SCHRIFT.breite(probe.replace("_", " ")) > breit - 4:
                zeile(stueck, K.C_CREAM, 4)
                stueck = n
            else:
                stueck = probe
        zeile(stueck or "-", K.C_CREAM, 4)
        zeile("  ".join("%s %.2f" % (n, v) if v < 100 else "%s %d" % (n, v)
                        for n, v in sorted(gehirn.werte.items())), K.C_MUTED, 4)
        y += 3
        zeile("PROTOKOLL", K.C_MUTED_DK)
        platz = max(0, (r.bottom - 10 - y) // 9)
        for zeit, text in list(gehirn.protokoll)[-platz:] if platz else ():
            zeile("%6.1f %s" % (zeit, text), K.C_MUTED, 4)

    def _spawner_zeichnen(self, ziel) -> None:
        r = self.SPAWNER
        ui.kasten(ziel, r, K.C_AMBER, (10, 8, 7), 4)
        SCHRIFT.zeichnen(ziel, "SPAWNER", r.x + 6, r.y + 6, K.C_AMBER, 1)
        SCHRIFT.zeichnen(ziel, "ZEIT STEHT - SPAWNEN GEHT TROTZDEM" if self.zeit_stopp else "",
                         r.x + 60, r.y + 6, K.C_MUTED, 1)
        liste, optionen = self._spawner_flaechen()
        for z, rr in liste:
            if z[0] == "kopf":
                SCHRIFT.zeichnen(ziel, z[1], rr.x, rr.y + 1, K.C_MUTED_DK, 1)
                continue
            e = self.eintraege[z[1]]
            aktiv = z[1] == self._sp_nr
            if aktiv:
                pygame.draw.rect(ziel, (34, 24, 16), rr)
                if self._sp_fokus == "liste":
                    pygame.draw.rect(ziel, K.C_AMBER, (rr.x, rr.y, 2, rr.h))
            SCHRIFT.zeichnen(ziel, ui.kuerzen(e.name, rr.width - 12), rr.x + 6, rr.y + 1,
                             K.C_CREAM if aktiv else K.C_MUTED, 1)
        e = self.eintraege[self._sp_nr]
        SCHRIFT.zeichnen(ziel, ui.kuerzen(e.name, 136), r.x + 158, r.y + 22, K.C_AMBER, 1)
        w = self.werte(e)
        for i, (o, rr) in enumerate(optionen):
            aktiv = self._sp_fokus == "optionen" and i == self._sp_opt
            if aktiv:
                pygame.draw.rect(ziel, (34, 24, 16), rr)
            name, _werte, text = OPTIONEN[o]
            SCHRIFT.zeichnen(ziel, name, rr.x + 2, rr.y + 2,
                             K.C_CREAM if aktiv else K.C_MUTED, 1)
            SCHRIFT.zeichnen(ziel, ui.kuerzen(text(w[o]), 70), rr.right - 2, rr.y + 2,
                             K.C_AMBER if aktiv else K.C_CREAM, 1, ausrichtung="rechts")
        if not e.optionen:
            SCHRIFT.zeichnen(ziel, "KEINE EINSTELLUNGEN", r.x + 158, r.y + 36, K.C_MUTED_DK, 1)
        for i, text in enumerate(("ENTER / KLICK IN DIE WELT: SPAWNEN",
                                  "PFEILE: WAHL  TAB: EINSTELLUNGEN  4/ESC: ZU")):
            SCHRIFT.zeichnen(ziel, text, r.x + 6, r.bottom - 22 + i * 10, K.C_MUTED, 1)

    def _testmenue_zeichnen(self, ziel) -> None:
        r = self.MENUE
        ui.kasten(ziel, r, K.C_AMBER, (10, 8, 7), 4)
        SCHRIFT.zeichnen(ziel, "TESTMENÜ", r.x + 8, r.y + 8, K.C_AMBER, 1)
        SCHRIFT.zeichnen(ziel, "PFEILE/KLICK, ENTER LÖST AUS", r.right - 8, r.y + 8,
                         K.C_MUTED_DK, 1, ausrichtung="rechts")
        zeilen = self._menue_zeilen()
        for i, ((schluessel, name, wert), rr) in enumerate(zip(zeilen, self._menue_flaechen())):
            aktiv = i == self._tm_zeile
            if aktiv:
                pygame.draw.rect(ziel, (34, 24, 16), rr)
                pygame.draw.rect(ziel, K.C_AMBER, (rr.x, rr.y, 2, rr.h))
            SCHRIFT.zeichnen(ziel, name, rr.x + 6, rr.y + 2,
                             K.C_CREAM if aktiv else K.C_MUTED, 1)
            SCHRIFT.zeichnen(ziel, wert, rr.right - 4, rr.y + 2,
                             K.C_AMBER if aktiv else K.C_CREAM, 1, ausrichtung="rechts")
        hilfe = ""
        schluessel = zeilen[max(0, min(len(zeilen) - 1, self._tm_zeile))][0]
        for art, _n, text in GOTT_ARTEN:
            if schluessel == "gott:" + art:
                hilfe = text
        if hilfe:
            SCHRIFT.zeichnen(ziel, hilfe, r.centerx, r.bottom - 12, K.C_TEAL, 1,
                             ausrichtung="mitte")
