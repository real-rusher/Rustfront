"""
DUSTFRONT - Von Lobby zu Lobby
==============================

Bis 0.31 gab es zwei Starter, LAN-GASTGEBER und LAN-GAST, und beide fragten
im Terminal nach Name, Adresse und Kennwort. Wer eine Runde verliess, war
draussen - das Fenster ging zu.

Seit 0.32 gibt es nur noch einen Weg hinein: **jeder startet in seiner
eigenen Lobby.** Von dort tritt man den Lobbys der anderen im selben Netz
bei (lan.py findet sie), und wer eine fremde Runde verlaesst - von selbst,
weil der Gastgeber aufhoert oder weil er abgewiesen wurde -, landet wieder
in seiner eigenen Lobby statt vor dem Desktop.

Hier steht nur das Umsteigen. Die Lobby selbst ist das Gefecht mit
`lobby=True` (lobby.py), die Suche ist `LobbySuche` weiter unten.

GRUND fuer "erst verbinden, dann umsteigen": Ein Beitritt, der scheitert
(falsche Adresse, Gastgeber weg), darf einen nicht aus der eigenen Lobby
werfen. Darum wird die neue Verbindung aufgebaut, **bevor** die alte
Szene verlassen wird, und nur wenn sie steht, wird umgestiegen.
"""

from __future__ import annotations

import pygame

from . import config as K
from . import lan
from . import netz
from . import ui
from .font import SCHRIFT
from .menues import Menue, _mitte


def spielername(app) -> str:
    """Wie man in Lobbys heisst.

    Angemeldet der Kontoname - unter dem stehen auch die Zahlen. Sonst der
    Name aus der Lobbysuche, und ganz ohne alles SPIELER.
    """
    try:
        konto = getattr(app, "konto", None)
    except Exception:                           # noqa: BLE001
        konto = None
    if konto is not None and getattr(konto, "angemeldet", False):
        return netz.name_saeubern(konto.name)
    eigen = ""
    try:
        eigen = str(app.opt["spielername"] or "")
    except (KeyError, TypeError, AttributeError):
        pass
    sauber = netz.name_saeubern(eigen) if eigen.strip() else ""
    if sauber:
        return sauber
    # GRUND fuer die Zahl: Ohne sie hiesse jede Lobby im Netz SPIELER, und
    # in der Liste stuende fuenfmal dasselbe. Das Ende der eigenen Adresse
    # ist im Heimnetz eindeutig und bleibt meist ueber Tage gleich.
    ende = netz.eigene_adresse().rsplit(".", 1)[-1]
    return netz.name_saeubern("SPIELER" + (ende if ende.isdigit() else ""))


def eigene_lobby(app, hinweis: str = "", headless_port: int | None = None):
    """Eine eigene Lobby aufmachen und in sie wechseln.

    Gibt das neue Gefecht zurueck, oder None, wenn kein Port frei war.
    Der Port wandert: ist 50505 belegt (ein zweites Fenster auf demselben
    Rechner), wird der naechste genommen. `headless_port` legt ihn fest -
    nur fuer die Pruefungen, die ihre Ports selbst verteilen.
    """
    from .mehrspieler import Gefecht

    erster = int(headless_port or K.NETZ["port"])
    wirt = None
    for versuch in range(1 if headless_port else K.NETZ["port_versuche"]):
        try:
            wirt = netz.Gastgeber(erster + versuch)
            break
        except OSError:
            continue
    if wirt is None:
        return None
    g = Gefecht(app, spielername(app), gastgeber=wirt, lobby=True,
                ansagen=True, heimkehr=True)
    app.ersetzen(g)
    if hinweis:
        g.melden(hinweis, 6.0)
    return g


def beitreten(app, adresse: str, passwort: str = "") -> str:
    """Einer fremden Lobby beitreten. Gibt "" zurueck oder den Grund.

    Scheitert schon die Verbindung, bleibt alles, wie es war. Was danach
    noch schiefgehen kann - falsches Kennwort, falsche Version, die Lobby
    ist voll -, sagt der Gastgeber; dann geht es von selbst zurueck in die
    eigene Lobby (Gefecht.heim).
    """
    from .mehrspieler import Gefecht

    gast = netz.Gast(adresse)
    if not gast.offen:
        return gast.fehler or "KEINE VERBINDUNG"
    g = Gefecht(app, spielername(app), gast=gast, passwort=passwort,
                heimkehr=True)
    g.wohin = adresse
    app.ersetzen(g)
    return ""


def fehler_kurz(text: str) -> str:
    """Eine Socket-Meldung so kurz, dass sie in eine Zeile passt."""
    t = (text or "").upper()
    if "REFUSED" in t or "10061" in t or "111" in t:
        return "DORT IST KEINE LOBBY OFFEN"
    if "TIMED OUT" in t or "10060" in t or "TIMEOUT" in t:
        return "KEINE ANTWORT - FALSCHE ADRESSE?"
    if "UNREACHABLE" in t or "10065" in t or "10051" in t:
        return "ADRESSE NICHT ERREICHBAR"
    if "NAME" in t or "11001" in t or "GETADDRINFO" in t:
        return "ADRESSE UNBEKANNT"
    return t[:40] or "KEINE VERBINDUNG"


# ══════════════════════════════════════════════════════════════════
# Die Liste der Lobbys im Netz
# ══════════════════════════════════════════════════════════════════

ZEILEN = 6          # so viele Lobbys stehen auf einmal da


class LobbyZeile(ui.Knopf):
    """Eine gefundene Lobby: Name links, dann Spieler, Spielart, Kennwort.

    In Spalten statt als ein zentrierter Satz - sonst springen die Zahlen
    von Zeile zu Zeile hin und her, und man liest schlecht ab, wo Platz ist.
    """

    def __init__(self, rect, eintrag: dict, grund: str = "") -> None:
        super().__init__(rect, eintrag["name"], "lobby:%s" % eintrag["adresse"],
                         gesperrt=bool(grund))
        self.eintrag = eintrag
        self.grund = grund

    def zeichnen(self, ziel) -> None:
        z = self.zustand()
        rahmen, fuellung, schrift = ui.ZUSTAND_FARBEN[z]
        r = self.rect
        ui.kasten(ziel, r, rahmen, fuellung, 4)
        if z == ui.UEBER:
            pygame.draw.rect(ziel, K.C_ORANGE, (r.x, r.y + 3, 2, r.height - 6))
        e = self.eintrag
        y = r.centery - 3
        SCHRIFT.zeichnen(ziel, e["name"], r.x + 10, y, schrift, 1)
        if self.grund:
            SCHRIFT.zeichnen(ziel, self.grund, r.x + 110, y, K.C_RED, 1)
            return
        SCHRIFT.zeichnen(ziel, "%d/%d" % (e["spieler"], e["hoechstens"]),
                         r.x + 110, y, schrift, 1)
        art = "IN DER LOBBY" if e["lobby"] else (e["modus"] or "RUNDE")
        if not e["lobby"] and e["karte"]:
            art += " - " + e["karte"]
        SCHRIFT.zeichnen(ziel, ui.kuerzen(art, 190), r.x + 150, y,
                         K.C_TEAL if e["lobby"] else K.C_AMBER, 1)
        if e["passwort"]:
            SCHRIFT.zeichnen(ziel, "KENNWORT", r.right - 10, y, K.C_MUTED, 1,
                             1, "rechts")


class LobbySuche(Menue):
    """Lobbys im eigenen Netz, zum Anklicken. Darunter die Adresse von Hand.

    Liegt als Szene ueber der eigenen Lobby wie die Ausruestung: die Lobby
    laeuft darunter weiter (Gefecht.weiterlaufen), Gaeste, die schon da
    sind, fliegen also nicht hinaus, nur weil man sich umsieht.
    """

    titel = "LOBBYS IM NETZ"

    def __init__(self, app, gefecht=None) -> None:
        self.gefecht = gefecht
        self.tafel = _mitte(440, 300)
        eigen = getattr(gefecht, "ansager", None)
        self.sucher = lan.Sucher(ohne=eigen.kennung if eigen is not None else "")
        self._stand = None          # woran die Liste zuletzt gebaut wurde
        self.tippt = -1             # welches Textfeld dran ist, -1 = keines
        self._verbinde: tuple[str, str] | None = None
        self._verbinde_bild = 0
        self.blatt = 0
        super().__init__(app)

    # ---- Aufbau -------------------------------------------------------
    def _liste(self) -> list[dict]:
        return self.sucher.liste()

    def aufbauen(self) -> None:
        r = self.tafel
        alt = {f.name: f.wert for f in getattr(self, "elemente", [])
               if isinstance(f, ui.Textfeld)}
        bx, bw = r.x + 18, r.width - 36
        y = r.y + 44
        liste = self._liste()
        self.blatt = max(0, min(self.blatt, max(0, (len(liste) - 1) // ZEILEN)))
        neu: list[ui.Element] = []
        for i, e in enumerate(liste[self.blatt * ZEILEN:(self.blatt + 1) * ZEILEN]):
            grund = ""
            if e["version"] != K.VERSION:
                grund = "VERSION %s" % (e["version"] or "ALT")
            elif e["spieler"] >= e["hoechstens"]:
                grund = "VOLL"
            neu.append(LobbyZeile((bx, y + i * 22, bw, 19), e, grund))
        y = r.y + 44 + ZEILEN * 22 + 4
        konto = self.app._konto
        angemeldet = konto is not None and konto.angemeldet
        neu.append(ui.Textfeld((bx, y, bw - 96, 17), "ADRESSE", "adresse",
                               wert=alt.get("adresse", ""), laenge=40,
                               label_breite=70,
                               erlaubt=lambda c: c.isalnum() or c in ".:-"))
        neu.append(ui.Knopf((bx + bw - 90, y, 90, 17), "BEITRETEN", "hand"))
        neu.append(ui.Textfeld((bx, y + 21, bw - 96, 17), "KENNWORT", "wort",
                               wert=alt.get("wort", ""), verdeckt=True,
                               laenge=K.NETZ["passwortlaenge"], label_breite=70))
        if not angemeldet:
            neu.append(ui.Textfeld(
                (bx, y + 42, bw - 96, 17), "DEIN NAME", "name",
                wert=alt.get("name", str(self.app.opt["spielername"] or "")),
                laenge=K.NETZ["namenslaenge"], label_breite=70,
                erlaubt=lambda c: c.isalnum() or c in "-_"))
        neu.append(ui.Knopf((bx + bw - 90, y + 42, 90, 17), "ZURÜCK", "zurueck"))
        self.elemente = neu
        felder = self.felder
        for j, f in enumerate(felder):
            f.aktiv = (j == self.tippt)
        self.wahl = min(self.wahl, len(self.elemente) - 1)

    @property
    def felder(self) -> list:
        return [e for e in self.elemente if isinstance(e, ui.Textfeld)]

    def _wert(self, name: str) -> str:
        for f in self.felder:
            if f.name == name:
                return f.wert
        return ""

    def _feld_setzen(self, i: int) -> None:
        felder = self.felder
        self.tippt = (i % len(felder)) if (felder and i >= 0) else -1
        for j, f in enumerate(felder):
            f.aktiv = (j == self.tippt)

    # ---- Ablauf -------------------------------------------------------
    def schritt(self, dt: float) -> None:
        super().schritt(dt)
        for f in self.felder:
            f.schritt(dt)
        self.sucher.schritt(dt)
        stand = tuple((e["adresse"], e["spieler"], e["lobby"], e["modus"],
                       e["version"], e["passwort"]) for e in self._liste())
        if stand != self._stand:
            self._stand = stand
            self.aufbauen()
        if self._verbinde is not None:
            # Erst ein Bild "VERBINDE ..." zeigen, dann verbinden: der
            # Versuch kann bis zu K.NETZ["wartezeit"] Sekunden dauern, und
            # ein stehendes Bild ohne Erklaerung sieht wie ein Absturz aus.
            self._verbinde_bild += 1
            if self._verbinde_bild >= 2:
                adresse, wort = self._verbinde
                self._verbinde = None
                self._name_merken()
                grund = beitreten(self.app, adresse, wort)
                if grund:
                    self.sagen("KEINE VERBINDUNG: %s" % fehler_kurz(grund), 4.0)

    def _name_merken(self) -> None:
        if not any(f.name == "name" for f in self.felder):
            return
        name = netz.name_saeubern(self._wert("name")) if self._wert("name") else ""
        if name != str(self.app.opt["spielername"] or ""):
            self.app.opt["spielername"] = name
            self.app.opt.speichern()

    def verbinden(self, adresse: str, passwort: str = "") -> None:
        if not adresse.strip():
            self.sagen("ERST EINE ADRESSE EINGEBEN")
            return
        self._verbinde = (adresse.strip(), passwort)
        self._verbinde_bild = 0

    def verlassen(self) -> None:
        super().verlassen()
        self._name_merken()
        self.sucher.schliessen()

    def ausloesen(self, el) -> None:
        if el.name == "zurueck":
            self.zurueck()
        elif el.name == "hand":
            self.verbinden(self._wert("adresse"), self._wert("wort"))
        elif el.name.startswith("lobby:"):
            e = getattr(el, "eintrag", {})
            if e.get("passwort") and not self._wert("wort"):
                self._feld_setzen([f.name for f in self.felder].index("wort"))
                self.sagen("DIESE LOBBY HAT EIN KENNWORT - ERST EINGEBEN")
                return
            self.verbinden(e.get("adresse", ""), self._wert("wort"))

    def taste(self, ev) -> None:
        """Erst ans Textfeld, dann ans Menue - wie in der Anmeldung."""
        felder = self.felder
        if 0 <= self.tippt < len(felder):
            if ev.key == pygame.K_ESCAPE:
                self._feld_setzen(-1)
                return
            if felder[self.tippt].tippen(ev):
                return
            if ev.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                if felder[self.tippt].name in ("adresse", "wort") \
                        and self._wert("adresse"):
                    self.verbinden(self._wert("adresse"), self._wert("wort"))
                else:
                    self._feld_setzen(-1)
                return
        if ev.key == pygame.K_TAB:
            self._feld_setzen(self.tippt + 1)
            return
        if ev.key in (pygame.K_PAGEDOWN, pygame.K_PAGEUP):
            self.blatt += 1 if ev.key == pygame.K_PAGEDOWN else -1
            self.blatt = max(0, self.blatt)
            self.aufbauen()
            return
        if ev.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
            el = self.gewaehlt()
            if isinstance(el, ui.Textfeld):
                self._feld_setzen(self.felder.index(el))
                return
        super().taste(ev)

    def maus_druck(self, pos) -> None:
        for i, f in enumerate(self.felder):
            if f.rect.collidepoint(pos):
                self._feld_setzen(i)
                return
        self._feld_setzen(-1)
        super().maus_druck(pos)

    # ---- Bild ---------------------------------------------------------
    def inhalt_zeichnen(self, ziel) -> None:
        r = self.tafel
        g = self.gefecht
        if g is not None and g.ist_gastgeber:
            eigen = "DEINE LOBBY: %s" % g.gastgeber.adresse
        else:
            eigen = "DEINE ADRESSE: %s" % netz.eigene_adresse()
        SCHRIFT.zeichnen(ziel, eigen, r.centerx, r.y + 30, K.C_MUTED, 1, 1,
                         "mitte")
        if not self._liste():
            y = r.y + 44 + 2 * 22
            SCHRIFT.zeichnen(ziel, "SUCHE ..." if self.sucher.sock is not None
                             else "SUCHE GEHT HIER NICHT: %s"
                             % self.sucher.fehler.upper()[:30],
                             r.centerx, y, K.C_MUTED, 1, 1, "mitte")
            SCHRIFT.zeichnen(ziel, "WER IM SELBEN NETZ DUSTFRONT OFFEN HAT,",
                             r.centerx, y + 16, K.C_MUTED_DK, 1, 1, "mitte")
            SCHRIFT.zeichnen(ziel, "ERSCHEINT HIER VON SELBST.",
                             r.centerx, y + 26, K.C_MUTED_DK, 1, 1, "mitte")
        anzahl = len(self._liste())
        if anzahl > ZEILEN:
            SCHRIFT.zeichnen(ziel, "SEITE %d/%d  [BILD HOCH/RUNTER]"
                             % (self.blatt + 1, (anzahl - 1) // ZEILEN + 1),
                             r.right - 20, r.y + 30, K.C_MUTED_DK, 1, 1,
                             "rechts")
        if self._verbinde is not None:
            ui.schleier(ziel, 150)
            SCHRIFT.zeichnen(ziel, "VERBINDE MIT %s ..." % self._verbinde[0],
                             K.GAME_W // 2, K.GAME_H // 2 - 4, K.C_AMBER, 1, 1,
                             "mitte")

    def fusstext(self) -> str:
        return "[KLICK] BEITRETEN   [TAB] FELD   [ESC] ZURÜCK"
