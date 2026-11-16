"""
DUSTFRONT - Kern
================

Fenster, Zeit, Eingabe, Bilder. Alles, was nichts mit dem Spiel selbst zu tun
hat, aber unter allem liegt.

Vier Entscheidungen, die hier festgezurrt sind und spaeter nicht mehr
angefasst werden muessen:

1. **Fester Zeitschritt.** Die Simulation laeuft immer in Schritten von
   1/120 s, unabhaengig von der Bildrate. Gezeichnet wird dazwischen
   interpoliert. Ohne das haengt spaeter jede Physik an der Bildrate, und das
   nachtraeglich einzubauen heisst, jede Bewegung neu zu schreiben.

2. **Alles rendert auf eine feste Flaeche.** 640x360, danach einmal
   hochskaliert. Pixel bleiben Pixel, jedes Fensterverhaeltnis geht.

3. **Eingabe laeuft ueber Aktionen, nicht ueber Tasten.** Der Spielcode fragt
   "wird VOR gedrueckt", nicht "ist W unten". Tastenbelegung aendern heisst
   dann ein Eintrag in TASTEN.

4. **Bilder kommen aus der Registratur.** Gibt es assets/<name>.png, wird die
   Datei benutzt, sonst ein im Code erzeugter Platzhalter. Beim Austausch
   gegen echte Pixel-Art aendert sich am Spielcode nichts. Fuer Klaenge gilt
   dasselbe, siehe audio.py.
"""

from __future__ import annotations

import math
import os
import warnings
from pathlib import Path

import pygame

from . import config as K
from . import plattform
from .audio import Klaenge
from .einstellungen import Einstellungen

# ══════════════════════════════════════════════════════════════════
# Eingabe
# ══════════════════════════════════════════════════════════════════

# Rueckfallebene, falls keine Einstellungen geladen werden konnten. Im
# Normalfall kommt die Tabelle aus einstellungen.py und ist umlegbar.
TASTEN = {
    "vor":      [pygame.K_w, pygame.K_UP],
    "zurueck":  [pygame.K_s, pygame.K_DOWN],
    "links":    [pygame.K_a, pygame.K_LEFT],
    "rechts":   [pygame.K_d, pygame.K_RIGHT],
    "dash":     [pygame.K_LSHIFT, pygame.K_RSHIFT],
    "ziehen":   [pygame.K_g],
    "ebenen":   [pygame.K_q],
    "planen":   [pygame.K_p],
    "nutzen":   [pygame.K_e],
    "nachladen": [pygame.K_r],
    "tracer":   [pygame.K_t],
    "tracer_weit": [pygame.K_z],
    "waffe1":   [pygame.K_1],
    "waffe2":   [pygame.K_2],
    "waffe3":   [pygame.K_3],
    "waffe4":   [pygame.K_4],
    "waffe5":   [pygame.K_5],
    "waffe6":   [pygame.K_6],
    "waffe7":   [pygame.K_7],
    "waffe8":   [pygame.K_8],
    "waffe9":   [pygame.K_9],
    "waffe10":  [pygame.K_0],
    "feuermodus": [pygame.K_v],
    # Die Ebene anschauen. Im Gefecht gehoert das Mausrad seit 0.30 dem
    # Zoom; die Ebenen gehen dort mit Strg + Mausrad oder diesen Tasten.
    "ansicht_hoch": [pygame.K_PAGEUP],
    "ansicht_runter": [pygame.K_PAGEDOWN],
    "heilen":   [pygame.K_h],
    "nahkampf": [pygame.K_f],
    # Granate sofort werfen (seit 0.34.96) - auf G wie das Ziehen: wer
    # neben einem Gefallenen steht, zieht ihn, sonst fliegt die Granate.
    "granate":  [pygame.K_g],
    "faehigkeit": [pygame.K_c],     # Faehigkeit der Klasse (seit 0.34.73)
    "inventar": [pygame.K_TAB],
    "pause":    [pygame.K_ESCAPE],
    "debug":    [pygame.K_F3],
    "vollbild": [pygame.K_F11],
}
MAUSTASTEN = {"feuer": 1, "zweit": 3}




def _gpu_hinweise_weg() -> None:
    """Die Umgebungsvariablen fuer SCALED wieder weg (siehe App._gpu_setzen)."""
    os.environ.pop("SDL_HINT_RENDER_SCALE_QUALITY", None)
    os.environ.pop("SDL_RENDER_SCALE_QUALITY", None)


def _fenster_objekt():
    """Das Fenster als pygame.Window (pygame-ce ab 2.4), sonst None."""
    fenster = getattr(pygame, "Window", None)
    if fenster is None or not hasattr(fenster, "from_display_module"):
        return None
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            return fenster.from_display_module()
    except (pygame.error, AttributeError):
        return None

class Eingabe:
    """Uebersetzt Tasten und Maus in benannte Aktionen."""

    def __init__(self, tabelle: dict | None = None) -> None:
        self.tabelle = dict(tabelle) if tabelle else dict(TASTEN)
        self._gehalten: set[str] = set()
        self._gedrueckt: set[str] = set()
        self._losgelassen: set[str] = set()
        # Zaehlt die Bilder (seit 0.34.95). GRUND: ein Druck gilt ein ganzes
        # Bild, in einem Bild laufen aber oft zwei oder drei Rechenschritte.
        # Wer Druecke je Schritt liest, merkt so, ob er dieses Bild schon
        # gelesen hat - sonst zaehlt ein Druck doppelt.
        self.bild = 0
        self.maus = pygame.Vector2(0, 0)      # in Spielkoordinaten der Flaeche
        self.rad = 0
        # Ein Stick statt WASD (touch.py, seit 0.34.20): der Bewegungswunsch
        # mit seiner Laenge, 0 bis 1. None heisst Tastatur.
        self.analog: pygame.Vector2 | None = None
        # Der rechte Stick (seit 0.34.22): wohin gezielt wird, als Versatz
        # von der eigenen Figur in Pixeln des Bildes. None heisst Maus.
        # GRUND: Aus dem Mauspunkt gerechnet hing das Ziel an der Kamera,
        # und die folgt selbst dem Ziel - beim Laufen wackelte es, mit dem
        # Scharfschuetzengewehr deutlich (gemeldet).
        self.ziel_versatz: pygame.Vector2 | None = None

    def neues_bild(self) -> None:
        self.bild += 1
        self._gedrueckt.clear()
        self._losgelassen.clear()
        self.rad = 0

    def ereignis(self, ev) -> None:
        if ev.type == pygame.KEYDOWN:
            for name, tasten in self.tabelle.items():
                if ev.key in tasten:
                    self._gehalten.add(name)
                    self._gedrueckt.add(name)
        elif ev.type == pygame.KEYUP:
            for name, tasten in self.tabelle.items():
                if ev.key in tasten:
                    self._gehalten.discard(name)
                    self._losgelassen.add(name)
        elif ev.type == pygame.MOUSEBUTTONDOWN:
            for name, knopf in MAUSTASTEN.items():
                if ev.button == knopf:
                    self._gehalten.add(name)
                    self._gedrueckt.add(name)
        elif ev.type == pygame.MOUSEBUTTONUP:
            for name, knopf in MAUSTASTEN.items():
                if ev.button == knopf:
                    self._gehalten.discard(name)
                    self._losgelassen.add(name)
        elif ev.type == pygame.MOUSEWHEEL:
            self.rad += ev.y

    def gehalten(self, name: str) -> bool:
        return name in self._gehalten

    def gedrueckt(self, name: str) -> bool:
        return name in self._gedrueckt

    def losgelassen(self, name: str) -> bool:
        return name in self._losgelassen

    def richtung(self) -> pygame.Vector2:
        """Bewegungswunsch als Vektor der Laenge 0 oder 1 - mit einem Stick
        auch dazwischen: halb gedrueckt heisst langsamer gehen."""
        if self.analog is not None and self.analog.length_squared() > 1e-6:
            v = pygame.Vector2(self.analog)
            if v.length_squared() > 1.0:
                v.normalize_ip()
            return v
        v = pygame.Vector2(
            (1 if self.gehalten("rechts") else 0) - (1 if self.gehalten("links") else 0),
            (1 if self.gehalten("zurueck") else 0) - (1 if self.gehalten("vor") else 0))
        if v.length_squared() > 1e-6:
            v.normalize_ip()
        return v

    def ziel_welt(self, kamera, figur) -> pygame.Vector2:
        """Der Zielpunkt in der Welt: unter der Maus, oder mit dem Stick
        von der Figur aus."""
        if self.ziel_versatz is not None:
            return pygame.Vector2(figur) + self.ziel_versatz * kamera.zoom
        return kamera.zu_welt(self.maus)

    def blick_versatz(self, kamera) -> pygame.Vector2:
        """Wie weit die Kamera in Blickrichtung vorausschaut (Welt-Pixel)."""
        if self.ziel_versatz is not None:
            return self.ziel_versatz * kamera.zoom
        return (self.maus - pygame.Vector2(K.GAME_W / 2, K.GAME_H / 2)) * kamera.zoom

    def tabelle_setzen(self, tabelle: dict) -> None:
        """Nach einer Aenderung im Menue neu uebernehmen."""
        self.tabelle = {k: list(v) for k, v in tabelle.items() if v}
        self.alles_loslassen()

    def alles_loslassen(self) -> None:
        self._gehalten.clear()
        self._gedrueckt.clear()
        self._losgelassen.clear()


# ══════════════════════════════════════════════════════════════════
# Bilder
# ══════════════════════════════════════════════════════════════════

_PLATZHALTER = {}
# Zeichner fuer ganze Familien von Namen (seit 0.34.60): (Anfang, Zeichner).
# Der Zeichner bekommt den vollen Namen und gibt eine Flaeche zurueck oder
# None, wenn er ihn nicht kennt. GRUND: 31 Aussehen mal Mannschaft mal Waffe
# waeren ueber tausend einzelne Eintraege - die meisten nie gebraucht.
_MUSTER: list = []
# Und ihr Sollmass: (Anfang, Funktion Name -> (b, h) oder None).
_MUSTER_MASS: list = []


def platzhalter(name):
    """Registriert einen Zeichner fuer ein Bild, das es noch nicht gibt."""
    def deko(fn):
        _PLATZHALTER[name] = fn
        return fn
    return deko


# Name -> (Zahl der Muster beim Rechnen, Sollmass), siehe Bilder.mass.
_MASS_MERK: dict = {}


def platzhalter_muster(anfang: str, zeichner, mass=None) -> None:
    """Registriert einen Zeichner fuer alle Namen, die mit `anfang`
    beginnen (siehe art_figuren.py). `mass(name)` sagt das Sollmass, damit
    eine hingelegte Datei auch hier auf die richtige Groesse kommt."""
    _MUSTER.append((anfang, zeichner))
    if mass is not None:
        _MUSTER_MASS.append((anfang, mass))


def drehen_mittig(bild: pygame.Surface, grad: float) -> pygame.Surface:
    """Wie pygame.transform.rotate(bild, grad), aber die Mitte des Bildes
    liegt bei jedem Winkel genau auf dem mittleren Pixel, und Breite und Hoehe
    sind immer ungerade (seit 0.34.141, K.DREHEN). Sonst sprang ein Bild, das
    sich dreht, um einen halben Pixel hin und her - je nachdem, ob rotate eine
    gerade oder ungerade Breite lieferte.

    Wie: das Bild `fein`-fach vergroessern (harte Pixel), drehen und dann je
    Pixel genau einmal abtasten, im Raster um die Mitte herum. Das ist eine
    Drehung mit naechstem Nachbarn, nur mit fester Mitte - es bleibt Pixel-Art."""
    d = K.DREHEN
    if not d["an"]:
        return pygame.transform.rotate(bild, grad)
    # Auch ungedreht (0 Grad) auf ungerade Masse: dieselbe Mitte wie gedreht.
    k = grad % 360
    f = max(1, int(d["fein"]))
    w, h = bild.get_size()
    gross = pygame.transform.scale(bild, (w * f, h * f))
    gedreht = pygame.transform.rotate(gross, k) if k else gross
    gw, gh = gedreht.get_size()
    # Bei gerader Breite liegt die Mitte zwischen zwei Pixeln. Abgetastet wird
    # dann einen halben Pixel links (oben) davon: so liegt das Bild ungedreht
    # genau wie vorher, wenn es an seiner Mitte aufgelegt wird (p - Breite/2),
    # und gedreht ebenso fest.
    cx = gw / 2.0 - (f / 2.0 if w % 2 == 0 else 0.0)
    cy = gh / 2.0 - (f / 2.0 if h % 2 == 0 else 0.0)
    rahmen = gedreht.get_bounding_rect()
    if rahmen.width == 0 or rahmen.height == 0:
        return pygame.transform.rotate(bild, grad)
    hx = int(math.ceil(max(cx - rahmen.left, rahmen.right - cx) / f))
    hy = int(math.ceil(max(cy - rahmen.top, rahmen.bottom - cy) / f))
    bw, bh = 2 * hx + 1, 2 * hy + 1
    # Abgetastet wird je Pixel die Stelle seiner Mitte: der mittlere Pixel
    # (hx, hy) bei (cx, cy), die anderen im Abstand von `f`.
    # transform.scale nimmt beim Verkleinern um `f` je Block den Pixel bei
    # f // 2 (gemessen) - darum so viel frueher anfangen.
    x0 = int(math.floor(cx - hx * f)) - f // 2
    y0 = int(math.floor(cy - hy * f)) - f // 2
    flaeche = pygame.Surface((bw * f, bh * f), pygame.SRCALPHA, gedreht)
    flaeche.fill((0, 0, 0, 0))
    flaeche.blit(gedreht, (-x0, -y0))
    return pygame.transform.scale(flaeche, (bw, bh))


def _zusammenfassen(stuecke: list, abstand: int = 6) -> list:
    """Nahe beieinander liegende Rechtecke zu einem (Buchstaben eines Worts,
    Felder einer Leiste): weniger, groessere Stuecke sind schneller
    hochzuziehen als viele kleine."""
    rest = sorted(stuecke, key=lambda r: (r.y, r.x))
    fertig = []
    while rest:
        r = rest.pop(0)
        wachsen = True
        while wachsen:
            wachsen = False
            gross = r.inflate(abstand * 2, abstand * 2)
            for i in range(len(rest) - 1, -1, -1):
                if gross.colliderect(rest[i]):
                    r = r.union(rest.pop(i))
                    wachsen = True
        fertig.append(r)
    return fertig


class Bilder:
    """Registratur fuer Sprites.

    `bild("wand")` liefert `assets/wand.png`, falls vorhanden, sonst den im
    Code erzeugten Platzhalter. Gedrehte Fassungen werden zwischengespeichert,
    damit pro Bild nicht neu rotiert wird.

    Drei Dinge nimmt die Registratur dem Zeichner ab, damit eine hingelegte
    Datei wirklich ohne Codeaenderung passt:

    1. **Endung egal.** Gesucht wird in der Reihenfolge aus
       `K.ASSETS["bild_endungen"]`, also erst .png, dann .webp, dann .bmp.
    2. **Groesse egal.** Passt die Datei nicht auf das Sollmass aus
       `K.BILD_MASS`, wird sie hart darauf gebracht, Pixel fuer Pixel und
       ohne Weichzeichnen. Wer in doppelter Groesse malt, bekommt sauberes
       Herunterrechnen; wer danebenliegt, reisst trotzdem kein Loch in die
       Karte.
    3. **Kaputte Datei kostet nichts.** Laesst sie sich nicht lesen, kommt
       der Platzhalter, und der Grund landet in `fehler`.
    """

    DREH_SCHRITT = 3        # Grad

    def __init__(self, ordner: Path | None = None) -> None:
        self.ordner = ordner
        self._cache: dict[str, pygame.Surface] = {}
        self._dreh: dict[tuple, pygame.Surface] = {}
        self.aus_datei: set[str] = set()
        self.fehler: list[str] = []

    # ---- Suchen -----------------------------------------------------
    def datei(self, name: str) -> Path | None:
        """Die erste Datei, die zu diesem Namen passt, oder None."""
        if self.ordner is None:
            return None
        for endung in K.ASSETS["bild_endungen"]:
            pfad = self.ordner / (name + endung)
            if pfad.is_file():
                return pfad
        return None

    @staticmethod
    def mass(name: str) -> tuple[int, int] | None:
        """Das Sollmass des Bildes, oder None, wenn keines festgelegt ist.

        Gemerkt je Name (seit 0.34.75): jede Figur fragt jedes Bild danach,
        und fuer Skins hiess das, den Namen jedesmal neu zu zerlegen.
        BILD_MASS aendert sich nach dem Laden nicht; kommt ein Muster spaeter
        dazu (Import-Reihenfolge), gilt der Merkzettel nicht mehr."""
        merk = _MASS_MERK.get(name)
        if merk is not None and merk[0] == len(_MUSTER_MASS):
            return merk[1]
        m = K.BILD_MASS.get(name)
        if not m:
            for anfang, mass in _MUSTER_MASS:
                if name.startswith(anfang):
                    m = mass(name)
                    if m:
                        break
        raus = (int(m[0]), int(m[1])) if m else None
        if len(_MASS_MERK) > 20000:
            _MASS_MERK.clear()
        _MASS_MERK[name] = (len(_MUSTER_MASS), raus)
        return raus

    def _laden(self, name: str) -> pygame.Surface | None:
        pfad = self.datei(name)
        if pfad is None:
            return None
        try:
            surf = pygame.image.load(str(pfad)).convert_alpha()
        except (pygame.error, OSError) as grund:
            self.fehler.append("%s: %s" % (pfad.name, grund))
            return None
        soll = self.mass(name)
        if soll is not None and surf.get_size() != soll:
            # Hart skalieren, nicht weichzeichnen: sonst verschmieren die
            # Kanten und die Pixel-Art sieht aus wie ein Foto.
            surf = pygame.transform.scale(surf, soll)
        self.aus_datei.add(name)
        return surf

    def bild(self, name: str) -> pygame.Surface:
        hit = self._cache.get(name)
        if hit is not None:
            return hit
        surf = self._laden(name)
        if surf is None:
            surf = self.platzhalter(name)
        self._cache[name] = surf
        return surf

    def platzhalter(self, name: str) -> pygame.Surface:
        """Die im Code gezeichnete Fassung, unabhaengig von jeder Datei.

        Wird auch von `--vorlagen` gebraucht: dort soll die Vorlage aus dem
        Code kommen, selbst wenn schon eine Datei danebenliegt.
        """
        zeichner = _PLATZHALTER.get(name)
        if zeichner is None:
            for anfang, muster in _MUSTER:
                if name.startswith(anfang):
                    surf = muster(name)
                    if surf is not None:
                        return surf
            soll = self.mass(name) or (K.TILE, K.TILE)
            surf = pygame.Surface(soll, pygame.SRCALPHA)
            surf.fill(K.C_FEHLT)                       # auffaellig fehlend
            self.fehler.append("%s: weder Datei noch Platzhalter" % name)
            return surf
        return zeichner()

    def gedreht(self, name: str, winkel: float) -> pygame.Surface:
        k = int(round(winkel / self.DREH_SCHRITT)) * self.DREH_SCHRITT % 360
        key = (name, k)
        hit = self._dreh.get(key)
        if hit is None:
            hit = drehen_mittig(self.bild(name), -k)
            self._dreh[key] = hit
        return hit

    def vergessen(self) -> None:
        """Alles neu laden. Fuer den Fall, dass jemand im laufenden Spiel
        eine Datei dazulegt oder austauscht."""
        self._cache.clear()
        self._dreh.clear()
        self.aus_datei.clear()
        self.fehler.clear()


# ══════════════════════════════════════════════════════════════════
# Szenen
# ══════════════════════════════════════════════════════════════════

class Szene:
    """Ein Zustand des Spiels. Die App haelt einen Stapel davon."""

    deckt_zu = True          # False = darunterliegende Szene wird mitgezeichnet
    # True = diese Szene rechnet weiter, auch wenn eine andere ueber ihr
    # liegt. Genau eine Art von Szene braucht das: eine, die an einer
    # Leitung haengt. Ein LAN-Gefecht, das stillsteht, waehrend jemand
    # sein Loadout aendert, hoert auf zu antworten - und der Gastgeber
    # wirft ihn nach acht Sekunden als stumm hinaus. Eingaben bekommt sie
    # trotzdem nicht: die gehen immer nur an die oberste Szene.
    weiterlaufen = False

    def __init__(self, app: "App") -> None:
        self.app = app

    def betreten(self) -> None:
        pass

    def verlassen(self) -> None:
        pass

    def ereignis(self, ev) -> None:
        pass

    def schritt(self, dt: float) -> None:
        """Fester Simulationsschritt. dt ist immer K.FIXED_DT."""

    def zeichnen(self, ziel: pygame.Surface, alpha: float) -> None:
        """alpha = 0..1 zwischen vorletztem und letztem Schritt."""


# ══════════════════════════════════════════════════════════════════
# Anwendung
# ══════════════════════════════════════════════════════════════════

class App:
    def __init__(self, titel="DUSTFRONT", asset_ordner: Path | None = None,
                 headless=False) -> None:
        self.headless = headless
        pygame.init()
        # Keine Tastenwiederholung im Spiel. Das Hauptmenue schaltet sie
        # fuer sich ein; im Spiel waere jede Wiederholung ein neuer Druck -
        # E gehalten hiesse dann: Treppe hoch, runter, hoch.
        pygame.key.set_repeat()
        self.opt = Einstellungen()
        self.flaeche = pygame.Surface((K.GAME_W, K.GAME_H))
        self.fenster_groesse = self.opt.aufloesung_paar()
        self.vollbild = self.opt["fenstermodus"] != "fenster"
        self.anzeige_setzen()
        pygame.display.set_caption(titel)
        self.flaeche = self.flaeche.convert()
        # Finger statt Maus und Tastatur (seit 0.34.20): auf iOS immer, auf
        # dem Rechner mit DUSTFRONT_TOUCH=1.
        self.touch = None
        if plattform.touch_an():
            from .touch import Touchsteuerung
            self.touch = Touchsteuerung(self)
        plattform.zu_fenster = self.zu_fenster

        self.bilder = Bilder(asset_ordner)
        # Mit Fenster die geteilte Werkstatt, die alle Klaenge im Hintergrund
        # baut (seit 0.34.58) - vorher hielt der erste Schuss jeder Waffe
        # das Spiel bis zu 380 ms an. Ohne Fenster (Tests, Werkzeuge) eine
        # eigene, die erst baut, wonach gefragt wird.
        if headless:
            self.klaenge = Klaenge(asset_ordner)
        else:
            self.klaenge = Klaenge.geteilt(asset_ordner)
            self.klaenge.vorbauen()
        self.klaenge.lautstaerke_setzen(self.opt["ton_gesamt"] / 100.0,
                                        self.opt["ton_effekte"] / 100.0)
        self.eingabe = Eingabe(self.opt.tastentabelle())
        self.uhr = pygame.time.Clock()
        self.stapel: list[Szene] = []
        self.laeuft = True
        self.fps_grenze = int(self.opt["bildrate"] or 0)
        self.debug = False
        self.zeitlupe = 0.0            # Restsekunden kurzer Verlangsamung
        self._rest = 0.0
        self.fps = 0.0
        # Das Konto. Es haengt an der App und nicht an einer Szene: eine
        # Anmeldung soll einen Szenenwechsel ueberleben, und das Journal
        # soll auch dann weiterlaufen, wenn man gerade im Menue steht.
        # Angelegt wird es traege - wer nur die Testkarte startet, soll
        # deswegen keine Datei anlegen und keinen Faden starten.
        self._konto = None

    @property
    def konto(self):
        """Das Konto des Spielers. Wird beim ersten Zugriff angelegt."""
        if self._konto is None:
            from .konto import Konto
            self._konto = Konto()
            # Was im Konto steht, gilt fuer die Einstellungen: wer sich
            # an einem anderen Rechner anmeldet, bringt sein Bildwackeln
            # und seine Lautstaerken mit.
            if self._konto.angemeldet and self._konto.werte:
                self.opt.konto_uebernehmen(self._konto.werte)
        return self._konto

    def konto_sichern(self) -> None:
        """Die eigenen Einstellungen ins Konto uebernehmen und ablegen.

        Aufgerufen, wenn im Menue etwas geaendert wurde. Ohne Anmeldung
        bleibt es bei der Datei auf diesem Rechner - das ist kein
        Sonderfall, sondern der Normalfall vor der ersten Anmeldung.
        """
        jetzt = self.opt.konto_werte()
        if self._konto is None:
            # Noch nicht geladen (seit 0.34.143): erst laden - das Laden
            # uebernimmt den alten Stand des Kontos in die Einstellungen -,
            # dann gilt wieder, was gerade gewaehlt wurde. Vorher ging die
            # Aenderung hier verloren, und beim ersten Zugriff aufs Konto
            # (Rundenstart) setzte der alte Stand das Aussehen zurueck
            # (gemeldet: "ich spawne oft mit dem Standard-Skin").
            self.konto
            self.opt.konto_uebernehmen(jetzt)
        self._konto.werte.update(jetzt)
        self._konto.profil_sichern()

    # ---- Anzeige ----------------------------------------------------
    def anzeige_setzen(self) -> None:
        self.gpu = False
        if self.headless:
            self.fenster = pygame.display.set_mode(K.START_FENSTER)
            self.viewport_rechnen()
            return
        modus = self.opt["fenstermodus"] if self.vollbild else "fenster"
        if self._gpu_gewuenscht() and self._gpu_setzen(modus):
            self.viewport_rechnen()
            return
        _gpu_hinweise_weg()
        if plattform.nur_vollbild():
            # iOS: der ganze Bildschirm, in der Groesse, die er hat.
            versuche = [((0, 0), pygame.FULLSCREEN)]
        elif modus == "randlos":
            versuche = [(self.desktop_groesse(), pygame.NOFRAME),
                        (self.desktop_groesse(), pygame.FULLSCREEN)]
        elif modus == "vollbild":
            versuche = [(self.desktop_groesse(), pygame.FULLSCREEN),
                        ((0, 0), pygame.FULLSCREEN)]
        else:
            versuche = [(self.fenster_groesse, pygame.RESIZABLE)]
        for groesse, flags in versuche:
            try:
                self.fenster = pygame.display.set_mode(groesse, flags)
                self.viewport_rechnen()
                return
            except pygame.error:
                continue
        self.vollbild = False
        self.fenster = pygame.display.set_mode(self.fenster_groesse, pygame.RESIZABLE)
        self.viewport_rechnen()

    # ---- Hochskalieren auf der Grafikkarte (seit 0.34.90) -------------
    def _gpu_gewuenscht(self) -> bool:
        """Soll die Grafikkarte das Bild aufs Fenster vergroessern? Nur auf
        Wunsch (GRAFIKKARTE SKALIERT) und nicht mit Touch-Steuerung: die
        rechnet Finger selbst ins Fenster um (touch.py), und auf iOS bleibt
        alles, wie es erprobt ist."""
        # BESTE QUALITAET BEIM ZOOM geht vor (seit 0.34.141): sie legt die Welt
        # selbst in Fensteraufloesung auf - mit SCALED ging das nicht, und der
        # Schalter wirkte stillschweigend gar nicht.
        return (bool(self.opt["grafikkarte"]) and not self.headless
                and not self.opt["zoom_hochaufloesend"]
                and not plattform.touch_an() and not plattform.nur_vollbild()
                and hasattr(pygame, "SCALED"))

    def _gpu_setzen(self, modus: str) -> bool:
        """Das Fenster mit pygame.SCALED: gezeichnet wird weiter in 640 x 360,
        die Grafikkarte vergroessert es beim flip() aufs Fenster - samt
        schwarzem Rand und Mauskoordinaten, die pygame zurueckrechnet. Das
        spart das Vergroessern auf dem Prozessor (transform.scale), bei
        1920 x 1080 rund 2 Millionen Pixel je Bild.

        False, wenn es nicht geht oder nur ein langsamer Ersatz ohne
        Grafikkarte da ist ("no fast renderer") - dann der alte Weg."""
        raster = self.opt["pixelraster"]
        # GRUND fuer die zwei Umgebungsvariablen: pygame fragt beim Anlegen
        # "SDL_HINT_RENDER_SCALE_QUALITY" als Schalter fuer krumme Faktoren
        # (sonst nur 2x, 3x ... im Fenster), SDL die Glaettung beim
        # Vergroessern. GANZE PIXEL: nur ganze Faktoren; OHNE FLIMMERN:
        # geglaettet; sonst scharf und fuellend.
        os.environ["SDL_HINT_RENDER_SCALE_QUALITY"] = "0" if raster == "ganzzahlig" else "1"
        os.environ["SDL_RENDER_SCALE_QUALITY"] = "linear" if raster == "ruhig" else "nearest"
        if modus == "vollbild":
            flags, groesse = pygame.SCALED | pygame.FULLSCREEN, None
        elif modus == "randlos":
            flags, groesse = pygame.SCALED | pygame.NOFRAME, self.desktop_groesse()
        else:
            flags, groesse = pygame.SCALED | pygame.RESIZABLE, self.fenster_groesse
        try:
            with warnings.catch_warnings(record=True) as meldungen:
                warnings.simplefilter("always")
                fenster = pygame.display.set_mode((K.GAME_W, K.GAME_H), flags)
        except pygame.error:
            return False
        langsam = any("no fast renderer" in str(m.message) for m in meldungen)
        if langsam and not K.ANZEIGE["gpu_ohne_grafikkarte"]:
            return False
        self.fenster = fenster
        self.gpu = True
        if groesse is not None:
            fenster_obj = _fenster_objekt()
            if fenster_obj is not None:
                try:
                    fenster_obj.size = tuple(groesse)
                    if modus == "randlos":
                        fenster_obj.position = (0, 0)
                except (pygame.error, ValueError, TypeError):
                    pass
        return True

    def _fenster_masse(self) -> tuple:
        """Wie gross das Fenster wirklich ist - mit SCALED meldet die
        Anzeigeflaeche nur 640 x 360."""
        if getattr(self, "gpu", False):
            fenster_obj = _fenster_objekt()
            if fenster_obj is not None:
                return tuple(fenster_obj.size)
            return tuple(self.fenster_groesse)
        return self.fenster.get_size()

    @staticmethod
    def desktop_groesse() -> tuple[int, int]:
        try:
            return pygame.display.get_desktop_sizes()[0]
        except (pygame.error, AttributeError, IndexError):
            info = pygame.display.Info()
            if info.current_w > 0:
                return (info.current_w, info.current_h)
            return tuple(K.START_FENSTER)

    def anzeige_uebernehmen(self) -> None:
        """Nach einer Aenderung in den Einstellungen neu aufsetzen."""
        self.fenster_groesse = self.opt.aufloesung_paar()
        self.vollbild = self.opt["fenstermodus"] != "fenster"
        self.fps_grenze = int(self.opt["bildrate"] or 0)
        self.anzeige_setzen()
        self.klaenge.lautstaerke_setzen(self.opt["ton_gesamt"] / 100.0,
                                        self.opt["ton_effekte"] / 100.0)

    def viewport_rechnen(self) -> None:
        fw, fh = self.fenster.get_size()
        roh = min(fw / K.GAME_W, fh / K.GAME_H)
        ganz = round(roh)
        if self.opt["pixelraster"] == "ganzzahlig":
            self.skala = max(1.0, float(int(roh)))
        elif ganz >= 1 and abs(roh - ganz) <= K.FENSTER_EINRASTEN * ganz:
            # Fast ein ganzes Vielfaches: genau das (K.FENSTER_EINRASTEN).
            self.skala = float(ganz)
        else:
            self.skala = max(0.25, roh)
        w, h = int(K.GAME_W * self.skala), int(K.GAME_H * self.skala)
        self.viewport = pygame.Rect((fw - w) // 2, (fh - h) // 2, w, h)

    def vollbild_wechseln(self) -> None:
        if plattform.nur_vollbild():
            return
        self.opt["fenstermodus"] = ("fenster" if self.opt["fenstermodus"] != "fenster"
                                    else "vollbild")
        self.opt.speichern()
        self.anzeige_uebernehmen()

    def zu_spiel(self, pos) -> pygame.Vector2:
        """Fensterkoordinate in Koordinate der Spielflaeche."""
        return pygame.Vector2((pos[0] - self.viewport.x) / self.skala,
                              (pos[1] - self.viewport.y) / self.skala)

    def hoch_auflegen(self, rect, maler) -> bool:
        """Etwas in Fensteraufloesung ueber das Bild legen (seit 0.34.100).

        Die Spielflaeche ist 640 x 360 gross und wird aufs Fenster
        vergroessert - eine Karte darin hat nie mehr Pixel als das. Gewuenscht
        war "deutlich hoehere Resolution fuer die Minimap": wer hier
        anmeldet, malt sein Rechteck (`rect`, Koordinaten der Spielflaeche)
        nach dem Vergroessern noch einmal in voller Fenstergroesse.
        `maler(flaeche, mass)` bekommt eine Flaeche in Fenstergroesse und den
        Faktor Fenster/Spielflaeche. Was gleichzeitig auf der Spielflaeche
        steht, bleibt der Ersatz, wenn es nichts zu vergroessern gibt (die
        Grafikkarte skaliert, Touch-Steuerung, ohne Fenster)."""
        if (getattr(self, "gpu", False) or getattr(self, "touch", None) is not None
                or getattr(self, "skala", 1.0) <= 1.0 or getattr(self, "fenster", None) is None):
            return False
        self.__dict__.setdefault("hochaufgeloest", []).append((pygame.Rect(rect), maler))
        return True

    def _hoch_zeichnen(self, f) -> None:
        liste = self.__dict__.get("hochaufgeloest") or []
        if not liste:
            return
        rand = f.get_rect()
        for rect, maler in liste:
            ziel = self.zu_fenster(rect).clip(rand)
            if ziel.width <= 0 or ziel.height <= 0:
                continue
            try:
                maler(f.subsurface(ziel), self.skala)
            except (pygame.error, ValueError):
                continue
        self.hochaufgeloest = []

    def zu_fenster(self, rect) -> pygame.Rect:
        """Ein Rechteck der Spielflaeche im Fenster (fuer die Tastatur)."""
        r = pygame.Rect(rect)
        return pygame.Rect(round(self.viewport.x + r.x * self.skala),
                           round(self.viewport.y + r.y * self.skala),
                           max(1, round(r.width * self.skala)),
                           max(1, round(r.height * self.skala)))

    # ---- Szenenstapel -----------------------------------------------
    def schieben(self, szene: Szene) -> None:
        self.stapel.append(szene)
        szene.betreten()

    def werfen(self) -> None:
        if self.stapel:
            self.stapel.pop().verlassen()

    def ersetzen(self, szene: Szene) -> None:
        while self.stapel:
            self.werfen()
        self.schieben(szene)

    @property
    def oben(self) -> Szene | None:
        return self.stapel[-1] if self.stapel else None

    # ---- Schleife ---------------------------------------------------
    def ereignisse(self) -> None:
        self.eingabe.neues_bild()
        touch = self.touch
        for ev in plattform.text_umsetzen(pygame.event.get()):
            if touch is not None:
                if ev.type in (pygame.FINGERDOWN, pygame.FINGERUP, pygame.FINGERMOTION):
                    for neu in touch.ereignis(ev):
                        self._weiterreichen(neu)
                    continue
                if getattr(ev, "touch", False) and ev.type in (
                        pygame.MOUSEMOTION, pygame.MOUSEBUTTONDOWN,
                        pygame.MOUSEBUTTONUP, pygame.MOUSEWHEEL) \
                        and touch.schluckt(ev):
                    # Die Maus, die SDL aus einem Finger macht: im Spiel
                    # gehoert der Finger der Steuerung (touch.py).
                    continue
            if ev.type == pygame.QUIT:
                self.laeuft = False
                return
            if ev.type == pygame.WINDOWFOCUSLOST:
                # Wer das Fenster wechselt, waehrend er eine Taste haelt,
                # laesst sie im anderen Fenster los - dieses hier erfaehrt
                # davon nie. Ohne das blieb die Taste als gehalten stehen:
                # die Figur lief weiter, schoss weiter, und beim Gast nahm
                # ein festhaengendes E immer wieder die Treppe.
                self.eingabe.alles_loslassen()
                if touch is not None:
                    # Auf iOS: die App geht in den Hintergrund. Finger, die
                    # dabei lagen, melden sich nie mehr ab.
                    for neu in touch.alles_los():
                        self._weiterreichen(neu)
                continue
            if ev.type in (pygame.WINDOWSIZECHANGED, pygame.VIDEORESIZE):
                surf = pygame.display.get_surface()
                if surf is not None:
                    self.fenster = surf
                    if not self.vollbild and not self.headless:
                        self.fenster_groesse = self._fenster_masse()
                self.viewport_rechnen()
                continue
            if ev.type == pygame.KEYDOWN:
                if ev.key in self.eingabe.tabelle.get("vollbild", ()):
                    self.vollbild_wechseln()
                    continue
                if ev.key in self.eingabe.tabelle.get("debug", ()):
                    self.debug = not self.debug
                    continue
            self._weiterreichen(ev)
        self.eingabe.maus = self.zu_spiel(pygame.mouse.get_pos())
        if touch is not None:
            # Die Sticks nach allem, was in diesem Bild kam: Zielpunkt,
            # Laufen und Feuer stehen jetzt fest. Beim Wechsel zwischen
            # Spiel und Menue kommt hier zurueck, was loszulassen ist.
            for neu in touch.bild():
                self._weiterreichen(neu)

    def _weiterreichen(self, ev) -> None:
        self.eingabe.ereignis(ev)
        if self.oben is not None:
            self.oben.ereignis(ev)

    def laufen(self, beenden: bool = True) -> None:
        """Die Spielschleife.

        beenden=False laesst pygame am Leben, wenn die Schleife endet. Das
        braucht das Hauptmenue: es hat pygame selbst hochgefahren und will
        danach weiterlaufen, statt mit dem Spiel zusammen abgeraeumt zu
        werden.
        """
        while self.laeuft and self.stapel:
            echt = self.uhr.tick(self.fps_grenze) / 1000.0
            self.fps = self.uhr.get_fps()
            echt = min(echt, 0.25)
            bild_dauer = echt              # wirklich vergangen, ohne Zeitlupe
            if self.zeitlupe > 0.0:
                self.zeitlupe -= echt
                echt *= 0.25

            self.ereignisse()
            if not self.laeuft or not self.stapel:
                break

            # Das Konto laeuft mit der echten Zeit, nicht mit dem festen
            # Schritt: es simuliert nichts, es holt nur Antworten ab.
            if self._konto is not None:
                self._konto.schritt(echt)

            self._rechnen(echt, bild_dauer)

            alpha = self._rest / K.FIXED_DT
            self.hochaufgeloest = []
            self.flaeche.fill(K.C_VOID)
            for szene in self._sichtbar():
                szene.zeichnen(self.flaeche, alpha)
            if self.touch is not None:
                self.touch.zeichnen(self.flaeche)
            self.ausgeben()
            plattform.tastatur_abgleichen()
        if not self.laeuft:
            self._fenster_zu()
        self.klaenge.stille()
        if beenden:
            self.klaenge.werkstatt_anhalten()
            pygame.quit()

    def takt_neu(self) -> None:
        """Die Uhr neu stellen, nach einem langen Aufbau (seit 0.34.143):
        die Zeit, die er gedauert hat, wird nicht nachgerechnet - sonst
        liefen danach Bild fuer Bild die meisten Schritte, die erlaubt sind,
        und die ersten Sekunden ruckelten."""
        self._rest = 0.0
        uhr = getattr(self, "uhr", None)
        if uhr is not None:
            uhr.tick()

    def _rechnen(self, echt: float, bild_dauer: float) -> int:
        """Die Rechenschritte eines Bildes: so viele feste Schritte, wie in
        `echt` Spielzeit passen (hoechstens MAX_SCHRITTE). Gibt ihre Zahl
        zurueck.

        Die Schritte laufen im Block, das Bild zeigt erst ihr Ende. Ihre
        Klaenge dagegen werden ueber die echte Dauer des Bildes verteilt
        (`Klaenge.versatz`, seit 0.34.58): der k-te von n Schritten klingt
        um k/n der Bilddauer spaeter. Vorher erklangen alle zugleich, und
        bei 10 Bildern je Sekunde wurde aus einem Feuerstoss ein Knall je
        Bild. Geteilt wird die echte Dauer, nicht die Spielzeit: laeuft das
        Spiel unter MAX_SCHRITTE in Zeitlupe, klingt es im selben Takt, in
        dem man es sieht."""
        self._rest += echt
        n, rest = 0, self._rest
        while rest >= K.FIXED_DT and n < K.MAX_SCHRITTE:
            rest -= K.FIXED_DT
            n += 1
        abstand = bild_dauer / n if n else 0.0
        schritte = 0
        try:
            while self._rest >= K.FIXED_DT and schritte < K.MAX_SCHRITTE:
                self.klaenge.versatz = schritte * abstand
                for szene in self._aktive():
                    szene.schritt(K.FIXED_DT)
                self._rest -= K.FIXED_DT
                schritte += 1
        finally:
            # Was zwischen den Bildern klingt (Menue, Tasten), sofort.
            self.klaenge.versatz = 0.0
        if schritte == K.MAX_SCHRITTE:
            self._rest = 0.0          # aufgelaufene Zeit verwerfen
        return schritte

    def _fenster_zu(self) -> None:
        """Das Fenster wurde geschlossen: aufraeumen, bevor alles weg ist.

        Erst jede Szene verlassen, oberste zuerst - genau wie mit ESC. Das
        ist der Weg, auf dem ein laufendes Gefecht seine Runde als
        abgebrochen bucht und die Gaeste es erfahren (seit 0.31; vorher
        endete die Schleife einfach, und die Runde war fuer alle weg).
        Dann das Konto: was im Journal offen ist, noch hochladen.

        Jeder Schritt fuer sich gefangen. Ein Fehler beim Aufraeumen darf
        das Schliessen nicht verhindern - wer auf X klickt, will, dass
        das Fenster zugeht.
        """
        while self.stapel:
            try:
                self.werfen()
            except Exception:                      # noqa: BLE001
                pass
        if self._konto is not None:
            try:
                # Laeuft im Faden gerade derselbe Abgleich, schadet das
                # nicht: dieselbe Partie zweimal ist dieselbe Zeile (3.2).
                self._konto.hochladen_vor_ende()
            except Exception:                      # noqa: BLE001
                pass

    def _aktive(self) -> list[Szene]:
        """Die oberste Szene rechnet - und alles darunter, was muss.

        "Muss" heisst: `weiterlaufen`. Das hat nur, wer an einer Leitung
        haengt und nicht einfach anhalten kann, ohne dass die Gegenseite
        ihn fuer weg haelt. Alles andere steht still, solange ein Menue
        darueber liegt - so war es immer, und so soll es bleiben.
        """
        if len(self.stapel) < 2:
            return self.stapel[-1:]
        raus = [self.stapel[-1]]
        for szene in reversed(self.stapel[:-1]):
            if not szene.weiterlaufen:
                break
            raus.insert(0, szene)
        return raus

    def _sichtbar(self) -> list[Szene]:
        i = len(self.stapel) - 1
        while i > 0 and not self.stapel[i].deckt_zu:
            i -= 1
        return self.stapel[i:]

    def ausgeben(self) -> None:
        # Direkt in den Ausschnitt des Fensters skalieren und nur den Rand
        # darum fuellen (seit 0.34.57). Vorher entstand jedes Bild eine neue
        # Flaeche in voller Fenstergroesse, die dann noch einmal kopiert
        # wurde - gemessen 6 ms je Bild bei 1920x1080, mehr als das Zeichnen
        # der Welt. Der Ausschnitt wird jedes Bild neu genommen (kostet
        # nichts) und nicht gemerkt: legt set_mode das Fenster neu an, zeigte
        # ein gemerkter Ausschnitt auf Speicher, den es nicht mehr gibt.
        f = self.fenster
        if getattr(self, "gpu", False):
            # Die Grafikkarte vergroessert (GRAFIKKARTE SKALIERT): nur die
            # 640 x 360 hineinkopieren, den Rest macht flip().
            f.blit(self.flaeche, (0, 0))
            pygame.display.flip()
            return
        vp = self.viewport
        fb, fh = f.get_size()
        innen = vp.left >= 0 and vp.top >= 0 and vp.right <= fb and vp.bottom <= fh
        if innen and self.__dict__.get("welt_hoch"):
            # BESTE QUALITAET (seit 0.34.141): die Welt deckt den ganzen
            # Ausschnitt - das 640 x 360-Bild vorher aufs Fenster zu ziehen war
            # umsonst (gemessen der groesste Posten je Bild).
            self._rand_fuellen(f, vp, fb, fh)
            if self._welt_hoch_auflegen(f, vp):
                self._hoch_zeichnen(f)
                pygame.display.flip()
                return
        if (self.opt["pixelraster"] == "ruhig" and abs(self.skala - round(self.skala)) > 1e-6
                and self.skala > 1.0):
            self._ruhig_ausgeben(f, vp, fb, fh)
        elif innen:
            self._rand_fuellen(f, vp, fb, fh)
            pygame.transform.scale(self.flaeche, vp.size, f.subsurface(vp))
        else:
            # Groesser als das Fenster (eingerastet, K.FENSTER_EINRASTEN):
            # in eine gemerkte Flaeche, der Rand faellt beim Auflegen weg.
            f.fill(K.C_VOID)
            puffer = getattr(self, "_gross_puffer", None)
            if puffer is None or puffer.get_size() != vp.size:
                puffer = self._gross_puffer = pygame.Surface(vp.size, 0, self.flaeche)
            pygame.transform.scale(self.flaeche, vp.size, puffer)
            f.blit(puffer, vp.topleft)
        self._welt_hoch_auflegen(f, vp)
        self._hoch_zeichnen(f)
        pygame.display.flip()

    @staticmethod
    def _rand_fuellen(f, vp, fb, fh) -> None:
        for rand in ((0, 0, fb, vp.top), (0, vp.bottom, fb, fh - vp.bottom),
                     (0, vp.top, vp.left, vp.height),
                     (vp.right, vp.top, fb - vp.right, vp.height)):
            if rand[2] > 0 and rand[3] > 0:
                f.fill(K.C_VOID, rand)

    # Die Farbe, die in der Anzeige-Schicht "hier nichts" heisst.
    _LEER = (255, 0, 254)

    def _welt_hoch_auflegen(self, f, vp) -> bool:
        """BESTE QUALITAET BEIM ZOOM (seit 0.34.138, gewuenscht: "dass das
        Spiel immer am bestmoeglichsten aussieht, egal wie weit man
        rausgezoomt hat"): die gezoomte Welt kommt in Fensteraufloesung ins
        Fenster, an ihre ungerundete Stelle - nicht erst auf 640 x 360
        verkleinert. Damit faellt auch das Zittern der eigenen Figur weg: auf
        dem groben Raster lagen Kamera und Figur je Bild bis zu 0,4 Pixel
        gegeneinander verschoben. Darueber kommt, was die Anzeige gemalt hat:
        jedes Bildpixel, das sich vom reinen Weltbild unterscheidet."""
        hoch = self.__dict__.pop("welt_hoch", None)
        if not hoch or vp.width <= 0 or vp.height <= 0:
            return False
        try:
            lw, z = hoch["leinwand"], hoch["zoom"]
            sk = vp.width / float(K.GAME_W)
            ox, oy = hoch["ecke"]
            b = max(1, int(round(lw.get_width() * sk / z)))
            h = max(1, int(round(lw.get_height() * sk / z)))
            # Groesser: hart, solange es mindestens doppelt ist (scharfe
            # Pixel); sonst weich (kein Flimmern bei krummen Faktoren).
            if b >= 2 * lw.get_width():
                gross = pygame.transform.scale(lw, (b, h))
            else:
                gross = pygame.transform.smoothscale(lw, (b, h))
            alt = f.get_clip()
            f.set_clip(vp)
            f.blit(gross, (vp.x + int(round(ox * sk)), vp.y + int(round(oy * sk))))
            # Die Anzeige: was sich vom reinen Weltbild unterscheidet.
            flach, jetzt = hoch["flach"], self.flaeche
            # Pixel fuer Pixel gegen das Weltbild (seit 0.34.141 in einem Schritt).
            gleich = pygame.mask.from_threshold(jetzt, (0, 0, 0, 0), (3, 3, 3, 255), flach)
            schicht = jetzt.copy()
            gleich.to_surface(schicht, setcolor=self._LEER, unsetcolor=None)
            schicht.set_colorkey(self._LEER)
            # Nur wo Anzeige liegt (seit 0.34.141): je Stueck vergroessern statt
            # das ganze Bild - die Anzeige deckt meist wenig.
            gleich.invert()
            stuecke = _zusammenfassen(gleich.get_bounding_rects() if gleich.count() else [])
            if len(stuecke) > K.ANZEIGE_STUECKE:
                stuecke = [schicht.get_rect()]
            sy = vp.height / float(K.GAME_H)
            for r in stuecke:
                x0, x1 = int(round(r.left * sk)), int(round(r.right * sk))
                y0, y1 = int(round(r.top * sy)), int(round(r.bottom * sy))
                if x1 <= x0 or y1 <= y0:
                    continue
                teil = pygame.transform.scale(schicht.subsurface(r), (x1 - x0, y1 - y0))
                teil.set_colorkey(self._LEER)
                f.blit(teil, (vp.x + x0, vp.y + y0))
            f.set_clip(alt)
            return True
        except (pygame.error, ValueError, KeyError, TypeError):
            return False

    def _ruhig_ausgeben(self, f, vp, fb, fh) -> None:
        """PIXELRASTER OHNE FLIMMERN (seit 0.34.77): erst um den naechsten
        ganzen Faktor vergroessern - jedes Spielpixel gleich gross -, dann
        weich auf die Fenstergroesse. Ein krummer Faktor zeigt so keine
        Reihe doppelt und die naechste dreifach; die Kanten werden dafuer
        etwas weicher, und es kostet einige Millisekunden je Bild."""
        n = int(self.skala) + 1
        gross = (K.GAME_W * n, K.GAME_H * n)
        puffer = getattr(self, "_ruhig_puffer", None)
        if puffer is None or puffer.get_size() != gross:
            puffer = self._ruhig_puffer = pygame.Surface(gross, 0, self.flaeche)
        pygame.transform.scale(self.flaeche, gross, puffer)
        f.fill(K.C_VOID)
        klein = pygame.transform.smoothscale(puffer, vp.size)
        f.blit(klein, vp.topleft)


# ══════════════════════════════════════════════════════════════════
# Kleine Helfer
# ══════════════════════════════════════════════════════════════════

def mische(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def naehern(wert: float, ziel: float, schritt: float) -> float:
    """Bewegt wert um hoechstens schritt in Richtung ziel."""
    if wert < ziel:
        return min(ziel, wert + schritt)
    return max(ziel, wert - schritt)


def winkel_zu(von: pygame.Vector2, nach: pygame.Vector2) -> float:
    return math.degrees(math.atan2(nach.y - von.y, nach.x - von.x))
