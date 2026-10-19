"""
DUSTFRONT - Touch-Steuerung
===========================

Seit 0.34.20, fuer iOS (plattform.py). Auf dem Rechner laesst sie sich mit
DUSTFRONT_TOUCH=1 ausprobieren - eine Maus zaehlt dann nicht als Finger,
aber ein Touchpad oder Touchscreen schon.

**Zwei Arten, wie Finger zaehlen.** Ob gespielt wird oder ein Menue offen
ist, sagt die oberste Szene mit `touch_spielt` (False, wenn es fehlt).

* Im Menue bleibt alles, wie es ist: SDL macht aus dem ersten Finger eine
  Maus, und jedes Menue ist mit der Maus bedienbar. Dazu kommt nur das
  Blaettern mit zwei Fingern - es wird zu Rad-Rasten.
* Im Spiel gehoeren die Finger der Steuerung, und die Maus, die SDL aus
  ihnen macht, faellt weg (core.App.ereignisse). Sonst schoesse jeder
  Fingertipp dorthin, wo der Finger liegt.

**Die Steuerung.** Links ein Stick, der dort entsteht, wo der Finger
aufsetzt: laufen, analog. Rechts genauso einer zum Zielen; ab
`K.TOUCH["feuer_ab"]` schiesst er auch - wie bei jedem Spiel mit zwei
Sticks. Wie weit er gedrueckt ist, sagt, wie weit weg gezielt wird; das
ist bei einer Granate die Wurfweite. Dazu Knoepfe am rechten Rand
(K.TOUCH["knoepfe"]).

**Wie es ins Spiel kommt.** Ueber dieselben Wege wie Tastatur und Maus,
nichts daneben:

* Knoepfe werden zu Tastendruecken (KEYDOWN/KEYUP mit der ersten Taste
  der Belegung). So erreichen sie jede Szene, die auf Tasten hoert - auch
  den Gast, der seine Druecke ueber das Netz schickt (mehrspieler.py,
  `_knopf_merken`).
* Die Sticks setzen in `core.Eingabe` den Bewegungswunsch (`analog`), den
  Mauspunkt und die gehaltenen Maustasten.

Dadurch braucht der Gastgeber nichts davon zu wissen: was ankommt, sieht
aus wie von einem Spieler mit Tastatur. Das ist der Kern von Crossplay.
"""

from __future__ import annotations

import math

import pygame

from . import config as K
from .font import SCHRIFT

T = K.TOUCH


class Touchsteuerung:
    def __init__(self, app) -> None:
        self.app = app
        # finger_id -> {"rolle": "links"/"rechts"/"knopf"/"menue",
        #               "start": Vector2, "jetzt": Vector2, "knopf": Index}
        self.finger: dict = {}
        self.analog = pygame.Vector2(0, 0)
        self.zielrichtung = pygame.Vector2(1, 0)
        self.zielanteil = 0.0
        self._weite = T["ziel_nah"]
        self.feuert = False
        self._feuerte = False
        self.zielen_an = False
        self._zielte = False
        self._gehaltene: set = set()      # Knoepfe der Art "halten", die unten sind
        self._spielte = False
        self._zwei_y = None               # Blaettern mit zwei Fingern im Menue
        self._zoom_abstand = None         # Zoomen mit zwei Fingern im Spiel
        self._overlay = None

    # ---- Wo und was ---------------------------------------------------
    def spielt(self) -> bool:
        szene = self.app.oben
        return bool(szene is not None and getattr(szene, "touch_spielt", False))

    def schluckt(self, ev) -> bool:
        """Soll die App diese Maus, die SDL aus einem Finger gemacht hat,
        verwerfen? Im Spiel immer; im Menue nur auf dem ESC-Knopf - sonst
        klickte derselbe Finger auch auf das, was darunter liegt."""
        if self.spielt():
            return True
        pos = getattr(ev, "pos", None)
        return pos is not None and self._auf_esc(self.app.zu_spiel(pos))

    @staticmethod
    def _auf_esc(p) -> bool:
        mx, my = T["esc_mitte"]
        r = T["esc_radius"] * 1.3
        return (p[0] - mx) ** 2 + (p[1] - my) ** 2 <= r * r

    def _punkt(self, ev) -> pygame.Vector2:
        """Ein Finger auf der Spielflaeche. SDL meldet ihn als Anteil des
        Fensters (0 bis 1), auch ausserhalb des Bildes in den schwarzen
        Raendern links und rechts - dort liegt beim iPhone oft der Daumen."""
        fw, fh = self.app.fenster.get_size()
        return self.app.zu_spiel((float(ev.x) * fw, float(ev.y) * fh))

    def _knopf_an(self, p) -> int | None:
        r = T["knopf_radius"] * 1.25          # etwas Spiel fuer den Daumen
        beste, beste_d = None, r * r
        for i, (_a, _t, mitte, _art) in enumerate(T["knoepfe"]):
            d = (p[0] - mitte[0]) ** 2 + (p[1] - mitte[1]) ** 2
            if d <= beste_d:
                beste, beste_d = i, d
        return beste

    def _taste(self, aktion: str):
        tasten = self.app.eingabe.tabelle.get(aktion) or ()
        return tasten[0] if tasten else None

    def _druck(self, aktion: str, unten: bool) -> list:
        taste = self._taste(aktion)
        if taste is None:
            return []
        return [pygame.event.Event(pygame.KEYDOWN if unten else pygame.KEYUP,
                                   key=taste, mod=0, scancode=0, unicode="")]

    # ---- Ereignisse -----------------------------------------------------
    def ereignis(self, ev) -> list:
        """Ein Fingerereignis verarbeiten. Gibt Ereignisse zurueck, die die
        App weiterreicht wie echte (Tastendruecke, Rad)."""
        raus = self._modus_pruefen()
        if not self._spielte:
            return raus + self._menue_finger(ev)
        return raus + self._spiel_finger(ev)

    def _modus_pruefen(self) -> list:
        """Ins Menue oder heraus: was gehalten war, loslassen. Sonst liefe
        die Figur hinter dem Pausenmenue weiter, oder ein Dash bliebe als
        Handbremse stehen. Gefragt wird vor jedem Finger und in jedem
        Bild - wer erst im Bild fragte, verloere den Finger, der das Spiel
        im selben Bild wieder aufnimmt."""
        spielt = self.spielt()
        if spielt == self._spielte:
            return []
        self._spielte = spielt
        return self.alles_los()

    def _spiel_finger(self, ev) -> list:
        fid = ev.finger_id
        p = self._punkt(ev)
        if ev.type == pygame.FINGERDOWN:
            knopf = self._knopf_an(p)
            if knopf is not None:
                self.finger[fid] = {"rolle": "knopf", "knopf": knopf,
                                    "start": p, "jetzt": p}
                return self._knopf_runter(knopf)
            platz = self._hotbar_an(p)
            if platz is not None:
                # Ein Platz der Hotbar: diese Waffe, sofort (seit 0.34.22).
                self.finger[fid] = {"rolle": "hotbar", "start": p, "jetzt": p}
                aktion = "waffe%d" % (platz + 1)
                return self._druck(aktion, True) + self._druck(aktion, False)
            links = p.x < K.GAME_W * T["links_bis"]
            rolle = "links" if links else "rechts"
            schon = [g for g in self.finger.values() if g["rolle"] == rolle]
            if schon:
                # Ein zweiter Finger auf derselben Seite: zoomen wie auf
                # einer Karte (seit 0.34.22). Der Stick dieser Seite
                # wird dafuer losgelassen - mit zwei Fingern zielt und
                # laeuft niemand.
                schon[0]["rolle"] = "zoom"
                self.finger[fid] = {"rolle": "zoom", "start": p, "jetzt": p}
                self._zoom_abstand = schon[0]["jetzt"].distance_to(p)
                self._sticks_rechnen()
                return []
            self.finger[fid] = {"rolle": rolle, "start": p, "jetzt": p}
            return []
        f = self.finger.get(fid)
        if f is None:
            return []
        if ev.type == pygame.FINGERMOTION:
            f["jetzt"] = p
            if f["rolle"] == "zoom":
                return self._zoomen()
            self._sticks_rechnen()
            return []
        # FINGERUP
        del self.finger[fid]
        if f["rolle"] == "knopf":
            return self._knopf_hoch(f["knopf"])
        if f["rolle"] == "zoom":
            # Der andere Finger zoomt nicht mehr und wird auch kein Stick:
            # er laege sonst irgendwo mitten im Zug.
            for g in self.finger.values():
                if g["rolle"] == "zoom":
                    g["rolle"] = "ruht"
            self._zoom_abstand = None
        self._sticks_rechnen()
        return []

    def _zoomen(self) -> list:
        """Zwei Finger auseinander: naeher heran, zusammen: weiter weg - als
        Rad-Rasten, wie das Mausrad am Rechner (Gefecht.zoom_stufe)."""
        zwei = [g["jetzt"] for g in self.finger.values() if g["rolle"] == "zoom"]
        if len(zwei) != 2 or self._zoom_abstand is None:
            return []
        abstand = zwei[0].distance_to(zwei[1])
        raus = []
        while abs(abstand - self._zoom_abstand) >= T["zoom_schritt"]:
            schritt = 1 if abstand > self._zoom_abstand else -1
            self._zoom_abstand += schritt * T["zoom_schritt"]
            raus.append(pygame.event.Event(
                pygame.MOUSEWHEEL, x=0, y=schritt, flipped=False,
                precise_x=0.0, precise_y=float(schritt), touch=False, which=0))
        return raus

    def _hotbar_an(self, p):
        """Welcher Platz der Hotbar unter dem Finger liegt, oder None. Die
        Szene sagt, wo die Plaetze stehen (`touch_hotbar`)."""
        frage = getattr(self.app.oben, "touch_hotbar", None)
        if frage is None:
            return None
        try:
            plaetze = frage() or []
        except Exception:                          # noqa: BLE001
            return None
        for i, r in enumerate(plaetze):
            # Etwas groesser als gezeichnet: die Felder sind nur 20 hoch.
            if pygame.Rect(r).inflate(2, T["hotbar_zugabe"]).collidepoint(p):
                return i
        return None

    def _knopf_runter(self, i: int) -> list:
        aktion, _t, _m, art = T["knoepfe"][i]
        if art == "umschalten":
            self.zielen_an = not self.zielen_an
            return []
        if art == "waffe":
            return self._naechste_waffe()
        if art == "halten":
            self._gehaltene.add(aktion)
        return self._druck(aktion, True)

    def _knopf_hoch(self, i: int) -> list:
        aktion, _t, _m, art = T["knoepfe"][i]
        if art in ("umschalten", "waffe"):
            return []
        self._gehaltene.discard(aktion)
        return self._druck(aktion, False)

    def _naechste_waffe(self) -> list:
        """Zur naechsten Waffe der Hotbar - als Druck auf ihre Zahl.

        Die Szene sagt, welche Waffe gerade dran ist und wie viele es gibt
        (`touch_waffen`). Weiss sie es nicht, bleibt es bei der ersten.
        """
        szene = self.app.oben
        jetzt, anzahl = 0, 1
        frage = getattr(szene, "touch_waffen", None)
        if frage is not None:
            try:
                jetzt, anzahl = frage()
            except Exception:                      # noqa: BLE001
                jetzt, anzahl = 0, 1
        nr = (int(jetzt) + 1) % max(1, int(anzahl)) + 1
        aktion = "waffe%d" % nr
        return self._druck(aktion, True) + self._druck(aktion, False)

    def _sticks_rechnen(self) -> None:
        r = T["stick_radius"]
        self.analog.update(0, 0)
        self.feuert = False
        self.zielanteil = 0.0
        for f in self.finger.values():
            if f["rolle"] not in ("links", "rechts"):
                continue
            v = f["jetzt"] - f["start"]
            laenge = v.length()
            if laenge > r:
                # Der Stick wandert mit, statt am Rand haengen zu bleiben:
                # wer weiter zieht, kehrt sonst erst nach demselben Weg um.
                f["start"] = f["jetzt"] - v * (r / laenge)
                v.scale_to_length(r)
                laenge = r
            anteil = laenge / r
            if anteil < T["tot"]:
                continue
            richtung = v / laenge
            if f["rolle"] == "links":
                kraft = min(1.0, (anteil - T["tot"]) / max(0.01, T["voll_ab"] - T["tot"]))
                self.analog = richtung * kraft
            else:
                self.zielrichtung = pygame.Vector2(richtung)
                self.zielanteil = anteil
                self.feuert = anteil >= T["feuer_ab"]

    def _menue_finger(self, ev) -> list:
        """Im Menue: zwei Finger blaettern, der ESC-Knopf. Sonst nichts -
        den einzelnen Finger macht SDL selbst zur Maus."""
        if ev.type == pygame.FINGERDOWN and self._auf_esc(self._punkt(ev)):
            return self._druck("pause", True) + self._druck("pause", False)
        if ev.type == pygame.FINGERDOWN:
            self.finger[ev.finger_id] = {"rolle": "menue", "start": None,
                                         "jetzt": pygame.Vector2(ev.x, ev.y)}
        elif ev.type == pygame.FINGERUP:
            self.finger.pop(ev.finger_id, None)
        elif ev.finger_id in self.finger:
            self.finger[ev.finger_id]["jetzt"] = pygame.Vector2(ev.x, ev.y)
        menue = [f for f in self.finger.values() if f["rolle"] == "menue"]
        if len(menue) != 2:
            self._zwei_y = None
            return []
        fh = self.app.fenster.get_size()[1]
        y = (menue[0]["jetzt"].y + menue[1]["jetzt"].y) / 2.0 * fh / max(0.01, self.app.skala)
        if self._zwei_y is None:
            self._zwei_y = y
            return []
        raus = []
        while abs(y - self._zwei_y) >= T["zwei_finger_rad"]:
            schritt = 1 if y > self._zwei_y else -1
            self._zwei_y += schritt * T["zwei_finger_rad"]
            raus.append(pygame.event.Event(
                pygame.MOUSEWHEEL, x=0, y=schritt, flipped=False,
                precise_x=0.0, precise_y=float(schritt), touch=False, which=0))
        return raus

    # ---- Je Bild --------------------------------------------------------
    def bild(self) -> list:
        """Einmal je Bild nach den Ereignissen: die Sticks in die Eingabe
        legen. Gibt Ereignisse zurueck, wenn beim Wechsel zwischen Spiel
        und Menue noch etwas losgelassen werden muss."""
        e = self.app.eingabe
        raus = self._modus_pruefen()
        if not self._spielte:
            e.analog = None
            e.ziel_versatz = None
            return raus
        e.analog = pygame.Vector2(self.analog)
        if self.zielanteil > 0.0:
            weite = T["ziel_nah"] + (T["ziel_weit"] - T["ziel_nah"]) * min(1.0, self.zielanteil)
            self._weite = weite
        elif self.zielen_an:
            # Mit ZIEL bleibt der Blick, wo er war, auch ohne Daumen auf dem
            # Stick: sonst sprang die Kamera zurueck, sobald man ihn hob.
            weite = self._weite
        else:
            weite = T["ziel_nah"]
        # Gezielt wird von der Figur aus (Eingabe.ziel_welt). Der Mauspunkt
        # bleibt fuer das Trefferzeichen, das dort erscheint, wo man zielt.
        e.ziel_versatz = self.zielrichtung * weite
        e.maus = self._mitte() + e.ziel_versatz
        self._halten(e, "feuer", self.feuert, self._feuerte)
        self._feuerte = self.feuert
        self._halten(e, "zweit", self.zielen_an, self._zielte)
        self._zielte = self.zielen_an
        return raus

    @staticmethod
    def _halten(e, name: str, jetzt: bool, vorher: bool) -> None:
        """Eine Maustaste der Eingabe halten oder loslassen - losgelassen
        wird nur, was der Finger selbst gehalten hatte. GRUND: am iPad
        kann zugleich eine echte Maus haengen, und deren Taste soll der
        Stick nicht in jedem Bild wieder wegnehmen."""
        if jetzt:
            e._gehalten.add(name)
            if not vorher:
                e._gedrueckt.add(name)
        elif vorher:
            e._gehalten.discard(name)
            e._losgelassen.add(name)

    def _mitte(self) -> pygame.Vector2:
        """Wo die eigene Figur auf der Spielflaeche steht."""
        frage = getattr(self.app.oben, "touch_mitte", None)
        if frage is not None:
            try:
                p = frage()
                if p is not None:
                    return pygame.Vector2(p)
            except Exception:                      # noqa: BLE001
                pass
        return pygame.Vector2(K.GAME_W / 2, K.GAME_H / 2)

    def alles_los(self) -> list:
        raus = []
        for aktion in sorted(self._gehaltene):
            raus += self._druck(aktion, False)
        self._gehaltene.clear()
        self.finger.clear()
        self._zoom_abstand = None
        self.analog.update(0, 0)
        self.feuert = False
        self.zielanteil = 0.0
        self.zielen_an = False
        e = self.app.eingabe
        self._halten(e, "feuer", False, self._feuerte)
        self._feuerte = False
        self._halten(e, "zweit", False, self._zielte)
        self._zielte = False
        return raus

    # ---- Zeichnen -------------------------------------------------------
    def zeichnen(self, ziel) -> None:
        if not self.spielt():
            if self.app.oben is not None:
                mitte, r = T["esc_mitte"], int(T["esc_radius"])
                pygame.draw.circle(ziel, K.C_VOID, mitte, r)
                pygame.draw.circle(ziel, K.C_MUTED, mitte, r, 1)
                SCHRIFT.zeichnen(ziel, "ESC", mitte[0], mitte[1] - 3, K.C_CREAM, 1,
                                 ausrichtung="mitte")
            return
        if self._overlay is None or self._overlay.get_size() != ziel.get_size():
            self._overlay = pygame.Surface(ziel.get_size(), pygame.SRCALPHA)
        o = self._overlay
        o.fill((0, 0, 0, 0))
        # Die Deckkraft steckt in jeder Farbe selbst, nicht in set_alpha der
        # ganzen Flaeche. GRUND: pygame-ce 2.5.6 auf dem iPhone rechnet eine
        # Flaeche mit eigenem Alpha je Pixel UND set_alpha falsch - alles
        # Dunkle darunter wurde schwarz, Boden, Figuren und Schrift waren
        # weg, solange die Sticks zu sehen waren (gemeldet nach 0.34.20).
        # Alpha je Pixel allein benutzt jede Figur im Spiel; das geht dort.
        a = int(T["deckkraft"])
        hell = (*K.C_CREAM, a)
        dunkel = (*K.C_MUTED_DK, a)
        r = int(T["stick_radius"])
        for f in self.finger.values():
            if f["rolle"] not in ("links", "rechts"):
                continue
            s, j = f["start"], f["jetzt"]
            pygame.draw.circle(o, (*K.C_VOID, a * 150 // 255), (round(s.x), round(s.y)), r)
            pygame.draw.circle(o, hell, (round(s.x), round(s.y)), r, 2)
            v = j - s
            if v.length() > r:
                v.scale_to_length(r)
            farbe = (*K.C_ORANGE, a) if (f["rolle"] == "rechts" and self.feuert) else hell
            pygame.draw.circle(o, farbe, (round(s.x + v.x), round(s.y + v.y)), r // 2)
        unten = {f["knopf"] for f in self.finger.values() if f["rolle"] == "knopf"}
        kr = int(T["knopf_radius"])
        for i, (aktion, text, mitte, art) in enumerate(T["knoepfe"]):
            an = i in unten or (art == "umschalten" and self.zielen_an)
            pygame.draw.circle(o, (*(K.C_AMBER if an else K.C_VOID), a), mitte, kr)
            pygame.draw.circle(o, hell if an else dunkel, mitte, kr, 2)
            SCHRIFT.zeichnen(o, text, mitte[0], mitte[1] - 3,
                             K.C_VOID if an else K.C_CREAM, 1, ausrichtung="mitte")
        ziel.blit(o, (0, 0))
