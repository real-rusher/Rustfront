"""
DUSTFRONT - Darstellung
=======================

Kamera und Renderer. Zwei Regeln stecken hier drin, die spaeter nicht mehr
angefasst werden muessen:

**Sichtbarkeitsregel der Hoehenebenen.** Gezeichnet wird zuerst die Ebene
unter dir, abgedunkelt, danach deine eigene. Wo deine Ebene ein Loch hat
(Kachel "leer"), scheint die darunter durch. Genau so steht es im GDD: unter
dem Rumpf eines Walkers sieht man den Boden, und wer auf Hoehe 0 steht, sieht
die Beine als Saeulen. Mehr Etagen aendern an diesem Code nichts.

**Kamera.** Sie folgt weich, laeuft ein Stueck in Blickrichtung vor und hat
ein Ruckeln mit abklingender Staerke. Der Spieler bleibt trotzdem nah an der
Mitte, wie in den Mockups vorgesehen.
"""

from __future__ import annotations

import math
import random

import pygame

from . import art  # noqa: F401  registriert die Platzhalter-Bilder
from . import config as K
from . import plattform
from .font import SCHRIFT
from .world import DEKAL_PIXEL

RND = random.Random(4711)
# Kacheln je Seite eines vorgezeichneten Bodenblocks (seit 0.34.57). 8 mal 32
# Pixel: ein Blit deckt 64 Kacheln, und ein Block, der nur an einer Ecke ins
# Bild ragt, kostet wenig. Gemerkt werden hoechstens BODEN_MERKEN Bloecke
# (je 256 KB) - genug fuer alle Ebenen ganz herausgezoomt.
BODEN_STUECK = 8


def _erstes(eintrag):
    return eintrag[0]


def _viele_blits(ziel, auftraege) -> None:
    """Viele Bilder nacheinander auf `ziel` - wie einzelne blit-Aufrufe, nur
    mit einem einzigen Aufruf (pygame-ce fblits, seit 0.34.75). Ohne fblits
    (aelteres pygame) einzeln."""
    fb = getattr(ziel, "fblits", None)
    if fb is not None:
        fb(auftraege)
    else:
        for bild, ort in auftraege:
            ziel.blit(bild, ort)


def _deckend_wenn_moeglich(flaeche):
    """Eine Flaeche, deren Pixel alle Alpha 255 haben, ohne Alphakanal
    (seit 0.34.75). Beim Blit wird ein ganz deckendes Pixel genau kopiert -
    das Bild bleibt dasselbe, nur ohne Mischen je Pixel. Sonst (oder ohne
    Fenster) die Flaeche wie sie ist."""
    try:
        if not flaeche.get_flags() & pygame.SRCALPHA:
            return flaeche
        breite, hoehe = flaeche.get_size()
        if pygame.mask.from_surface(flaeche, 254).count() == breite * hoehe:
            return flaeche.convert()
    except pygame.error:
        pass
    return flaeche


_SCHLUESSEL = ((255, 0, 255), (1, 254, 3), (254, 1, 253), (3, 2, 251))


def _mit_farbschluessel(flaeche):
    """Eine Flaeche, deren Pixel nur ganz deckend oder ganz durchsichtig
    sind, als deckende Flaeche mit Farbschluessel und RLE (seit 0.34.75).
    Auf ein deckendes Ziel geblittet ergibt sie genau dasselbe Bild:
    deckende Pixel werden kopiert, die Loecher bleiben, wie sie sind - nur
    rund dreimal so schnell wie Mischen je Pixel. Gibt (Flaeche, True)
    zurueck, oder (flaeche, False), wenn es nicht genau ginge."""
    breite, hoehe = flaeche.get_size()
    ganz = pygame.mask.from_surface(flaeche, 254).count()
    if pygame.mask.from_surface(flaeche, 0).count() != ganz:
        return flaeche, False                 # halb durchsichtige Pixel
    loecher = breite * hoehe - ganz
    for farbe in _SCHLUESSEL:
        neu = pygame.Surface((breite, hoehe)).convert()
        neu.fill(farbe)
        neu.blit(flaeche, (0, 0))
        # Nur die Loecher duerfen die Schluesselfarbe haben.
        gleich = pygame.mask.from_threshold(neu, farbe, (1, 1, 1, 255)).count()
        if gleich == loecher:
            neu.set_colorkey(farbe, pygame.RLEACCEL)
            return neu, True
    return flaeche, False


_STREIFEN: dict = {}


def _rand_blit(ziel, bild) -> None:
    """`bild` bei (0, 0) auf `ziel` - nur seine Randstreifen, wenn innen ein
    Rechteck ganz durchsichtig ist (die Vignette, seit 0.34.75). Ein Pixel
    mit Alpha 0 laesst ein deckendes Ziel genau, wie es war; auf ein Ziel
    mit Alphakanal darum immer ganz."""
    if ziel.get_flags() & pygame.SRCALPHA:
        ziel.blit(bild, (0, 0))
        return
    hit = _STREIFEN.get(id(bild))
    if hit is None or hit[0] is not bild:
        hit = (bild, _rand_streifen(bild))
        if len(_STREIFEN) > 16:
            _STREIFEN.clear()
        _STREIFEN[id(bild)] = hit
    streifen = hit[1]
    if streifen is None:
        ziel.blit(bild, (0, 0))
        return
    for r in streifen:
        ziel.blit(bild, r.topleft, r)


def _rand_streifen(bild):
    """Die vier Streifen um das groesste durchsichtige Rechteck in der
    Mitte, oder None, wenn es keines gibt (oder es nicht sicher ist)."""
    try:
        w, h = bild.get_size()
        m = pygame.mask.from_surface(bild, 0)        # gesetzt: Alpha > 0
    except (pygame.error, ValueError):
        return None
    mx, my = w // 2, h // 2
    if m.get_at((mx, my)):
        return None
    x0 = mx
    while x0 > 0 and not m.get_at((x0 - 1, my)):
        x0 -= 1
    x1 = mx
    while x1 < w - 1 and not m.get_at((x1 + 1, my)):
        x1 += 1
    y0 = my
    while y0 > 0 and not m.get_at((mx, y0 - 1)):
        y0 -= 1
    y1 = my
    while y1 < h - 1 and not m.get_at((mx, y1 + 1)):
        y1 += 1
    innen = pygame.Rect(x0, y0, x1 - x0 + 1, y1 - y0 + 1)
    voll = pygame.mask.Mask(innen.size, fill=True)
    if m.overlap_area(voll, innen.topleft) != 0:
        return None
    raus = [pygame.Rect(0, 0, w, innen.top), pygame.Rect(0, innen.bottom, w, h - innen.bottom),
            pygame.Rect(0, innen.top, innen.left, innen.height),
            pygame.Rect(innen.right, innen.top, w - innen.right, innen.height)]
    return [r for r in raus if r.width > 0 and r.height > 0]


_NULLEN: dict = {}


def _ganz_leer(flaeche) -> bool:
    """Sind alle Bytes der Flaeche null - nach fill((0, 0, 0, 0)) nichts
    mehr darauf gezeichnet? Ein Vergleich der rohen Bytes, schneller als
    eine Maske. Im Zweifel (Rand im Speicher, Fehler) False."""
    try:
        roh = flaeche.get_buffer().raw
    except (pygame.error, ValueError, AttributeError):
        return False
    null = _NULLEN.get(len(roh))
    if null is None:
        if len(_NULLEN) > 8:
            _NULLEN.clear()
        null = _NULLEN[len(roh)] = bytes(len(roh))
    return roh == null


def _raster_waehlen(bild: int, breite: int):
    """Eine Flaechenbreite nahe `breite`, nach der `bild`/Breite ein kleines
    Raster hat: (Breite, q) - q Weltpixel ergeben genau ganze Bildpixel.
    Ohne passende Breite (breite, None): dann wie vor 0.34.77."""
    g = K.TIEFENRASTER
    for d in g["versuche"]:
        b = breite + d
        if b <= 0:
            continue
        q = b // math.gcd(b, bild)
        if q <= g["groesstes"]:
            return b, q
    return breite, None


def _zeile_spalte(eintrag):
    """Sortierschluessel fuer feste Kacheln: Zeile, dann Spalte."""
    return eintrag[0], eintrag[1]


BODEN_MERKEN = 320


def _gezeigter_winkel(w) -> float:
    """Der Winkel, mit dem ein Wesen gezeichnet wird - mit etwas Ruhe
    (seit 0.34.96, K.FIGUR_DREH_RUHE). GRUND: beim langsamen Gehen wandert
    der Mauspunkt in der Welt in ganzen Pixeln mit der Kamera, der Blick
    schwankte um eine Drehstufe des Bildes, und die Figur sprang von Bild
    zu Bild zwischen zwei gedrehten Fassungen - andere Pixel, die Mitte
    einen Pixel versetzt (gemeldet: "Mikroschritte vor und zurueck").
    Erst wer sich weiter dreht, bekommt das neue Bild."""
    alt = w.__dict__.get("_winkel_gezeigt")
    jetzt = w.winkel
    if alt is not None and abs((jetzt - alt + 180.0) % 360.0 - 180.0) < K.FIGUR_DREH_RUHE:
        return alt
    w._winkel_gezeigt = jetzt
    return jetzt


class Kamera:
    """Der Bildausschnitt. Folgt dem Spieler, laeuft ein Stueck in seine
    Blickrichtung vor und bekommt gelegentlich einen Schlag ab.

    Das Ruckeln haelt zwei Dinge auseinander, die frueher eines waren:

    ``anteil``  wie stark geruckelt werden **darf**. Das ist die
                Einstellung des Spielers (Menue und, spaeter, das Konto),
                0.0 bis 1.0. Auf 0 steht das Bild vollkommen still - auch
                dann, wenn die Welt gerade explodiert.
    ``ruckeln`` wie stark es gerade **wirklich** ruckelt.

    Und es hat eine Sperre. Ohne sie ergibt Dauerfeuer ein Dauerzittern:
    jeder Schuss legt nach, bevor der vorige verklungen ist, und das Bild
    kommt nie zur Ruhe. Genau so sah es beim Gastgeber aus.
    """

    def __init__(self, ziel=(0, 0)) -> None:
        self.pos = pygame.Vector2(ziel)
        self.ruckeln = 0.0
        self.versatz = pygame.Vector2(0, 0)
        self.anteil = 1.0
        self._sperre = 0.0
        # Wie viel Welt ins Bild passt: 1 ist das normale Bild, 2 die
        # doppelte Breite und Hoehe (Mausrad im Gefecht, mehrspieler.py).
        # Das Bild selbst bleibt 640 x 360 - die Welt wird dafuer auf eine
        # groessere Flaeche gezeichnet und verkleinert.
        self.zoom = 1.0
        # Blick voraus (Barrierefreiheit, experimentell): so viele
        # Weltpixel vor der Figur, in Blickrichtung, liegt die Bildmitte.
        # 0 = aus, dann wie immer ein kleines Stueck zur Maus hin.
        self.vorausschau = 0.0
        # Weich zwischen zwei Rechenschritten (seit 0.34.95): wo die Kamera
        # beim vorigen Schritt stand, und wo das Bild gerade zwischen beiden
        # liegt (alpha, wie bei den Figuren - zeichnen() setzt es). GRUND:
        # die Figuren werden zwischen zwei Schritten gezeichnet, die Kamera
        # stand auf dem letzten. Je nach Bildrate lag die Figur so jedes
        # Bild ein, zwei Pixel woanders und zuckte (gemeldet: "der
        # Charakter scheint beim Rumlaufen komisch umherzuhacken").
        self.vorher = pygame.Vector2(self.pos)
        self.alpha = 1.0
        self._nach_schritt = pygame.Vector2(self.pos)

    @property
    def mitte(self) -> pygame.Vector2:
        """Die Bildmitte, wie sie gezeichnet wird. Hat jemand die Kamera
        seit dem Schritt von Hand versetzt (Sprung, Tests), gilt die neue
        Stelle ohne Zwischenstand."""
        if self.alpha >= 1.0 or self.pos != self._nach_schritt:
            return pygame.Vector2(self.pos)
        return self.vorher.lerp(self.pos, max(0.0, self.alpha))

    @property
    def breite(self) -> float:
        """Wie viele Weltpixel das Bild breit ist."""
        return K.GAME_W * self.zoom

    @property
    def hoehe(self) -> float:
        return K.GAME_H * self.zoom

    def stossen(self, kraft: float) -> None:
        """Ein Schlag auf die Kamera. Kleines und zu Dichtes faellt weg."""
        r = K.RUCKELN
        kraft = float(kraft) * r["staerke"] * self.anteil
        if kraft < r["schwelle"] or self._sperre > 0.0:
            return
        self._sperre = r["sperre"]
        self.ruckeln = min(r["max"], self.ruckeln + kraft)

    def schritt(self, dt: float, ziel: pygame.Vector2, blick: pygame.Vector2,
                grenze: tuple[int, int], versatz=None, scope: bool = False) -> None:
        """`versatz`: wo die Maus vom Bildmittelpunkt weg steht, in
        Weltpixeln (seit 0.32.6). Ist er da, folgt der kleine Vorlauf zur
        Maus ihm statt `blick`.

        GRUND: `blick` ist der Weltpunkt unter der Maus - und der haengt
        selbst an der Kamera. Bewegte sich die Kamera, wanderte der Punkt
        mit, und die Kamera lief ihm ein Stueck hinterher; beim Zoomen
        verschob sich der Punkt ausserdem mit dem Massstab. Das Bild zog
        dann sichtbar zur Seite und fand sich erst nach einem Moment ein
        (gemeldet). Der Abstand zur Bildmitte haengt an keinem von beiden.
        """
        k = K.KAMERA
        self.vorher.update(self.pos)
        vor = (blick - ziel)
        if self.vorausschau > 0.0:
            # Der unsichtbare Punkt vor der Waffe. Nur die Richtung zaehlt,
            # nicht wie weit die Maus weg ist: sonst liefe das Bild der Maus
            # hinterher, und die Maus mit dem Bild - es schaukelte sich auf.
            wunsch = pygame.Vector2(ziel)
            if vor.length_squared() > 1.0:
                wunsch += vor.normalize() * self.vorausschau
            nachlauf = k["blick_nachlauf"]
        else:
            zug = K.SCOPE["zug"] if scope else k["maus_zug"]
            grenze_vor = K.SCOPE["weite"] / zug if scope else k["maus_max"]
            if versatz is not None:
                # Dieselbe Ruhelage wie frueher: dort galt
                # vorlauf = zug * (versatz + vorlauf), also
                # vorlauf = versatz * zug / (1 - zug).
                vor = pygame.Vector2(versatz) / (1.0 - zug)
            if vor.length() > grenze_vor:
                vor.scale_to_length(grenze_vor)
            wunsch = ziel + vor * zug
            nachlauf = k["nachlauf"]
        self.pos += (wunsch - self.pos) * min(1.0, nachlauf * dt)
        if (wunsch - self.pos).length_squared() < 0.36:
            # Den letzten halben Pixel nicht ausschleichen: die gerundete
            # Ecke sprang sonst noch einmal, wenn man laengst stand.
            self.pos.update(wunsch)

        self._sperre = max(0.0, self._sperre - dt)
        self.ruckeln = max(0.0, self.ruckeln
                           - K.RUCKELN["abbau"] * dt * max(1.0, self.ruckeln))
        r = self.ruckeln
        self.versatz.update(RND.uniform(-r, r), RND.uniform(-r, r))

        # An den Kartenrand anlegen, damit man nicht ins Nichts schaut
        halb_w, halb_h = self.breite / 2, self.hoehe / 2
        bw, bh = grenze
        if bw > self.breite:
            self.pos.x = max(halb_w, min(bw - halb_w, self.pos.x))
        else:
            self.pos.x = bw / 2
        if bh > self.hoehe:
            self.pos.y = max(halb_h, min(bh - halb_h, self.pos.y))
        else:
            self.pos.y = bh / 2
        self._nach_schritt.update(self.pos)

    @property
    def ecke(self) -> pygame.Vector2:
        """Die Ecke zum **Zeichnen**. Das Ruckeln steckt hier drin."""
        return self._ecke_bei(self.versatz.x, self.versatz.y)

    def _ecke_bei(self, vx: float, vy: float) -> pygame.Vector2:
        """Die Ecke mit dem Versatz (vx, vy), auf ganze Pixel gerundet."""
        m = self.mitte
        return pygame.Vector2(round(m.x - self.breite / 2 + vx),
                              round(m.y - self.hoehe / 2 + vy))

    def fest_im_bild(self, weltpunkt) -> pygame.Vector2:
        """Wo die Figur, der die Kamera folgt, gezeichnet wird (seit 0.34.95):
        auf ganzen Pixeln relativ zur ungerundeten Kamera, nicht zur
        gerundeten Ecke. Ihr Abstand zur Kamera aendert sich beim Folgen nur
        langsam, so steht sie still im Bild. GRUND: Figur und Ecke rundeten
        jede fuer sich, und beim Laufen sprang die Figur staendig einen
        Pixel vor und zurueck (gemeldet: "umherhacken")."""
        e = self.ecke
        m = self.mitte
        fx = m.x - self.breite / 2 + self.versatz.x
        fy = m.y - self.hoehe / 2 + self.versatz.y
        return pygame.Vector2(e.x + round(weltpunkt[0] - fx), e.y + round(weltpunkt[1] - fy))

    @property
    def ecke_ruhig(self) -> pygame.Vector2:
        """Dieselbe Ecke **ohne** Ruckeln, zum Umrechnen von Eingaben.

        Der Unterschied ist keine Feinheit. `zu_welt` liefert den Punkt,
        auf den gezielt wird, und daraus folgt der Winkel jedes Schusses
        und - bei der Granate - die Wurfweite. Rechnete man das ueber die
        wackelnde Ecke, veraenderte sich das Ziel mit jedem Zittern des
        Bildes: man haelt still, und der Wurf geht trotzdem woandershin.
        Das Ruckeln gehoert ins Bild, nicht in die Hand.
        """
        return self._ecke_bei(0.0, 0.0)

    def zu_welt(self, bildpunkt) -> pygame.Vector2:
        """Bildpunkt (im 640 x 360-Bild) -> Weltpunkt, auch mit Zoom.
        Seit 0.34.96 von der ungerundeten Kamera aus: von der gerundeten Ecke
        sprang der Mauspunkt beim langsamen Gehen pixelweise, und mit ihm der
        Blick der Figur."""
        m = self.mitte
        z = self.zoom
        return pygame.Vector2(bildpunkt[0] * z + m.x - self.breite / 2,
                              bildpunkt[1] * z + m.y - self.hoehe / 2)

    def zu_bild(self, weltpunkt) -> pygame.Vector2:
        """Weltpunkt -> Bildpunkt im 640 x 360-Bild, mit Ruckeln und Zoom."""
        # Dieselbe Rechnung wie (Vector2(weltpunkt) - self.ecke) / zoom, nur
        # ohne die drei Zwischenvektoren (seit 0.34.89) - die Anzeige des
        # Testmodus fragt das tausendfach je Bild.
        e, z = self.ecke, self.zoom
        return pygame.Vector2((weltpunkt[0] - e.x) / z, (weltpunkt[1] - e.y) / z)


class Ueberblendung:
    """Das letzte Weltbild, das nach einem Ebenenwechsel ausblendet.

    Die Ansicht springt beim Wechsel ueber Treppe oder Aufzug sofort auf
    die neue Hoehe (siehe K.EBENENWECHSEL). Ein harter Schnitt waere
    aber genauso unruhig wie das Nachziehen vorher - also liegt fuer
    einen Augenblick das alte Bild darueber und wird durchsichtig.

    Gemerkt wird jedes Bild, aber nur die Welt, nicht die Anzeige: sonst
    stuende die Lebensleiste kurz doppelt. Waehrend des Ausblendens
    bleibt das alte Bild stehen - wuerde es weiter gemerkt, blendete es
    sich selbst immer wieder ein und verschwaende viel spaeter.
    """

    def __init__(self) -> None:
        self.bild: pygame.Surface | None = None
        self.rest = 0.0

    def merken(self, ziel: pygame.Surface) -> None:
        if self.rest > 0:
            return
        if (self.bild is None or self.bild.get_size() != ziel.get_size()
                or self.bild.get_masks() != ziel.get_masks()):
            # Im Format des Ziels (seit 0.34.75): dann ist das Merken ein
            # reines Kopieren, ohne jedes Pixel umzurechnen.
            self.bild = pygame.Surface(ziel.get_size(), 0, ziel)
        self.bild.blit(ziel, (0, 0))

    def starten(self) -> None:
        if self.bild is not None:
            self.rest = K.EBENENWECHSEL["ueberblenden"]

    def schritt(self, dt: float) -> None:
        self.rest = max(0.0, self.rest - dt)

    def zeichnen(self, ziel: pygame.Surface) -> None:
        if self.rest <= 0 or self.bild is None:
            return
        t = self.rest / K.EBENENWECHSEL["ueberblenden"]
        self.bild.set_alpha(int(255 * t * t * (3 - 2 * t)))
        ziel.blit(self.bild, (0, 0))


class Renderer:
    def __init__(self, bilder) -> None:
        self.bilder = bilder
        self._dunkel: dict[tuple, tuple] = {}     # (Quelle, dunkle Fassung), siehe dunkel
        self._schatten_cache: dict[tuple, pygame.Surface] = {}
        self._tiefen: dict[int, pygame.Surface] = {}
        # Wie gross die Flaeche ist, auf die die Welt gezeichnet wird. Fast
        # immer das Bild selbst; mit Zoom (mehrspieler.py) eine groessere,
        # die danach verkleinert wird. Alles, was die Welt zeichnet, fragt
        # hier und nicht bei K.GAME_W.
        self.groesse = (K.GAME_W, K.GAME_H)
        self.vignette_an = True
        # Nur Boden und Waende, keine Wesen, kein Rauch, keine Funken:
        # das Gelaende im Nebel (mehrspieler.py, Zoom).
        self.nur_gelaende = False
        self._puffer_je: dict[str, pygame.Surface] = {}
        self._brand: dict[int, pygame.Surface] = {}
        self._fleck_cache: dict[tuple, pygame.Surface] = {}
        self._fleck_art: dict[tuple, pygame.Surface] = {}   # gefaerbt, gedreht
        self._rauch_puffer: dict[tuple, tuple] = {}
        self._feuer_puffer: dict[int, tuple] = {}
        self._klippen_farbe: dict[str, tuple] = {}
        self._stehend_offen = None      # siehe stehende_nachholen
        # Je Ebene: wo das Auge steht (Weltpunkt darunter und Hoehe ueber
        # der Ebene), gemerkt beim Zeichnen der Ebene - fuer `verdeckt`.
        self._augen: dict[int, tuple] = {}
        self._seiten_farbe: dict[str, tuple] = {}
        self._toene: dict[tuple, tuple] = {}     # siehe _stehende_zeichnen
        self._hoechste_stehende = max(d["hoehe"] for d in K.STEHEN.values())
        self._oberseiten: dict[tuple, pygame.Surface] = {}
        # Weiche Raender (seit 0.34.6, _weicher_rand). Was als Sand zaehlt:
        # der Boden selbst, Gestruepp (liegt auf Sand) und alles, was auf
        # Sand steht, ohne die ganze Kachel zu fuellen - Fass, Brocken,
        # Kaktus.
        self._weich: dict[tuple, pygame.Surface] = {}
        # Der Boden in Bloecken von BODEN_STUECK Kacheln, je Ebene und
        # Helligkeit vorgezeichnet (seit 0.34.57, siehe _bodenstueck).
        self._boden_stuecke: dict[tuple, tuple] = {}
        voll = (0, 0, K.TILE, K.TILE)
        self._grundartig = frozenset(
            k for k, d in K.KACHELN.items()
            if k in (K.BODEN, K.GESTRUEPP)
            or (d["fest"] and K.STEHEN.get(d["name"]) is not None
                and K.STEHEN[d["name"]]["rahmen"] != voll))
        # Auch Schatten, Vignette und die Dekale kommen aus der Registratur:
        # eine Datei assets/vignette.png ersetzt sie genauso wie eine Kachel.
        # Gehalten werden sie hier, damit die Zeichenschleife nicht bei jedem
        # Bild nachschlaegt.
        self._vignette = bilder.bild("vignette")
        self._blut = bilder.bild("blut")
        self._wandschatten = bilder.bild("wandschatten")
        self._boden_namen = ("boden", "boden_2", "boden_3", "boden_4")
        self._schneespur = pygame.Surface((10, 6), pygame.SRCALPHA)
        pygame.draw.ellipse(self._schneespur, (67, 105, 128, 255),
                            self._schneespur.get_rect())

    # ---- Vorgefertigtes -------------------------------------------
    def _passend(self, cache: dict, name: str, groesse, deckkraft: float = 1.0):
        """Ein Bild aus der Registratur auf eine Groesse gebracht, gemerkt.

        Schatten, Blut und Brandfleck haben keine feste Groesse: sie richten
        sich nach dem, was sie wirft. Gemalt sind sie einmal in ihrem
        Basismass, hier werden sie darauf umgerechnet. Das gilt fuer den
        Platzhalter wie fuer eine hingelegte Datei - beide sind an dieser
        Stelle nur noch eine Form.
        """
        w = max(1, int(groesse[0]))
        h = max(1, int(groesse[1]))
        deckung = max(0, min(255, int(round(255 * deckkraft))))
        key = (w, h, deckung)
        hit = cache.get(key)
        if hit is not None:
            return hit
        # Hart skalieren, genau wie die Registratur es mit einer Datei macht.
        # Weichzeichnen wuerde aus einem Blutfleck einen Farbnebel machen.
        hit = pygame.transform.scale(self.bilder.bild(name), (w, h))
        if deckung < 255:
            hit = hit.copy()
            hit.fill((255, 255, 255, deckung), special_flags=pygame.BLEND_RGBA_MULT)
        if len(cache) > 200:
            cache.clear()
        cache[key] = hit
        return hit

    def schatten(self, radius: float, f: float = 1.0) -> pygame.Surface:
        """Schatten passend zum Koerperkreis des Wesens.

        Frueher war das ein festes Oval fuer alle, das weder zur Groesse noch
        zur Fusslinie passte. Jetzt richtet sich das Oval nach dem Radius,
        und f schrumpft und lichtet es, wenn das Wesen in der Luft haengt.
        """
        d = K.DEKAL
        r = max(3.0, float(radius))
        return self._passend(self._schatten_cache, "schatten",
                             (r * d["schatten_breite"] * f + 4,
                              r * d["schatten_hoehe"] * f + 4), f)

    def blutfleck(self, radius: float, art: str = "mensch",
                  variante: int = 0) -> pygame.Surface:
        """Was liegen bleibt, wo ein Wesen gestorben ist. Ein Brecher
        hinterlaesst mehr als ein Laeufer, darum haengt es am Radius.

        Seit 0.34.33 je Blut eine Farbe (K.BLUT): die Form kommt aus dem
        Bild "blut", die Farbe von hier - so behaelt ein ersetztes Bild
        seine Form. `variante` (0 bis 7) dreht und spiegelt die Form: vorher
        lag jeder Fleck gleich da, Tropfen fuer Tropfen."""
        basis = K.BILD_MASS["blut"]
        k = max(0.4, float(radius) / K.DEKAL["blut_radius"])
        roh = self._passend(self._fleck_cache, "blut",
                            (basis[0] * k, basis[1] * k))
        farbe = K.BLUT.get(art, K.BLUT["mensch"])["farbe"]
        variante = int(variante) % 8
        if farbe is None and variante == 0:
            return roh
        key = (roh.get_size(), art, variante)
        hit = self._fleck_art.get(key)
        if hit is None:
            hit = roh
            if farbe is not None:
                # Die Farbe ersetzen, das Alpha (die Form) behalten.
                hit = roh.copy()
                hit.fill((0, 0, 0), special_flags=pygame.BLEND_RGB_MULT)
                hit.fill(farbe, special_flags=pygame.BLEND_RGB_ADD)
            if variante % 4:
                hit = pygame.transform.rotate(hit, 90 * (variante % 4))
            if variante >= 4:
                hit = pygame.transform.flip(hit, True, False)
            if len(self._fleck_art) > 300:
                self._fleck_art.clear()
            self._fleck_art[key] = hit
        return hit

    def brandfleck(self, radius: float) -> pygame.Surface:
        """Russfleck, den eine Granate hinterlaesst."""
        k = max(0.2, float(radius) / K.DEKAL["brand_radius"])
        basis = K.BILD_MASS["brandfleck"]
        return self._passend(self._brand, "brandfleck",
                             (basis[0] * k, basis[1] * k))

    def dunkel(self, surf: pygame.Surface, staerke: int) -> pygame.Surface:
        # Der Eintrag haelt das Quellbild fest (seit 0.34.57): sonst bekam
        # ein neues Bild die id eines weggeworfenen - etwa einer skalierten
        # Oberseite - und erhielt dessen dunkle Fassung. Gefunden beim
        # pixelgenauen Vergleich: ein Ring um ein Fass auf der Ebene darunter.
        key = (id(surf), staerke)
        hit = self._dunkel.get(key)
        if hit is None or hit[0] is not surf:
            bild = surf.copy()
            bild.fill((staerke, staerke, staerke), special_flags=pygame.BLEND_RGB_MULT)
            if len(self._dunkel) > 400:
                self._dunkel.clear()
            hit = (surf, bild)
            self._dunkel[key] = hit
        return hit[1]

    # ---- Welt ------------------------------------------------------
    # Kachelsaetze. Der Name einer Karte sagt, welcher gilt - `satz` im
    # Kopf der Kartendatei. Was hier nicht steht, bleibt beim Standard;
    # eine Karte mit unbekanntem Satz sieht also aus wie immer und faellt
    # nicht aus.
    # Die Kartensaetze stehen seit 0.34.19 in config (K.KARTENSAETZE), weil
    # auch die Kollision sie braucht.
    SAETZE = K.KARTENSAETZE

    def ebene_zeichnen(self, ziel, welt, index: int, ecke, dunkel: int | None,
                       auge: float | None = None,
                       aufschieben: bool = False) -> None:
        """`auge`: wie hoch das Auge ueber dieser Ebene steht, in Welt-
        Pixeln - fuer die Perspektive der stehenden Kacheln (K.STEHEN).
        Ohne Angabe die Brennweite: die angeschaute Ebene.

        `aufschieben`: Waende und Barrikaden noch nicht zeichnen, sondern
        merken - `stehende_nachholen` zeichnet sie nach den Figuren, damit
        eine Mauer verdeckt, wer hinter ihr steht (seit 0.34.4).

        Ist `ziel` eben ganz durchsichtig geleert worden (die Tiefenflaeche,
        `_ziel_frisch`, seit 0.34.75), kommen die Bodenstuecke zuerst und
        nebeneinander, also jedes auf leeren Grund - dann duerfen sie als
        Flaeche mit Farbschluessel kommen wie auf das Bild selbst."""
        e = welt.ebene(index)
        satz = self.SAETZE.get(getattr(welt, "satz", ""), {})
        boden_namen = satz.get("boden", self._boden_namen)
        # Der Ausschnitt richtet sich nach der Zielflaeche, nicht nach der
        # Bildgroesse: die Tiefenflaeche fuer untere Ebenen ist groesser.
        zw, zh = ziel.get_size()
        t0x = max(0, int(ecke.x // K.TILE))
        t0y = max(0, int(ecke.y // K.TILE))
        t1x = min(e.breite - 1, int((ecke.x + zw) // K.TILE))
        t1y = min(e.hoehe - 1, int((ecke.y + zh) // K.TILE))
        # Erster Durchgang: alles Begehbare - aus vorgezeichneten Bloecken
        # (seit 0.34.57). Vorher je Kachel ein Blit und ein paar
        # Nachschlagungen, gemessen ein Viertel des ganzen Zeichnens.
        C = BODEN_STUECK
        fest = []
        self._boden_da = False
        # Auf ein deckendes Ziel (das Bild selbst, nicht eine Tiefenflaeche)
        # darf ein Bodenstueck mit Loechern als Flaeche mit Farbschluessel
        # kommen (_mit_farbschluessel).
        deckend = (getattr(self, "_ziel_frisch", None) is ziel
                   or not ziel.get_flags() & pygame.SRCALPHA)
        for cy in range(t0y // C, t1y // C + 1):
            for cx in range(t0x // C, t1x // C + 1):
                stueck, stueck_fest = self._bodenstueck(welt, e, satz, boden_namen,
                                                        cx, cy, dunkel, deckend)
                if stueck is not None:
                    self._boden_da = True
                    ziel.blit(stueck, (cx * C * K.TILE - ecke.x, cy * C * K.TILE - ecke.y))
                for (tx, ty, name_f, info) in stueck_fest:
                    if t0x <= tx <= t1x and t0y <= ty <= t1y:
                        fest.append((ty, tx, name_f, info))
        # In der Reihenfolge wie vorher Kachel fuer Kachel: Zeile um Zeile.
        # Sortiert nur nach Zeile und Spalte - die Angaben (Tupel mit dicts)
        # lassen sich nicht vergleichen, und zwei Eintraege mit derselben
        # Kachel gibt es nicht.
        fest.sort(key=_zeile_spalte)
        fest = [(tx, ty, name_f, ty * K.TILE - ecke.y, info)
                for (ty, tx, name_f, info) in fest]

        # Fussspuren liegen auf der Schneeschicht und altern mit der Welt.
        # Ein fester Weltzeitstempel sorgt dafuer, dass Kamerawechsel und
        # Ebene-Ansicht die Abdruecke nicht neu erzeugen oder auffrischen.
        if getattr(welt, "satz", "") == "schnee":
            for sx, sy, sebene, zeit in welt.schneespuren:
                alter = welt.zeit - zeit
                if sebene != index or alter >= 24.0:
                    continue
                alpha = max(0, int(115 * (1.0 - alter / 24.0)))
                spur = plattform.deckkraft(self._schneespur, alpha)
                ziel.blit(spur, (int(sx - ecke.x - 5), int(sy - ecke.y - 3)))

        # Dekale liegen auf dem Boden - also vor den Waenden. Bis 0.34.2
        # kamen sie danach; bei flachen Waenden fiel das nicht auf, bei
        # stehenden laege ein Blutfleck sonst auf der Mauerseite.
        self._dekale_zeichnen(ziel, e, ecke, dunkel)

        # Zweiter Durchgang: Schlagschatten, dann die festen Kacheln darueber
        sch = self._wandschatten
        if dunkel is not None:
            sch = self.dunkel(sch, dunkel)
        # Alle Schatten in einem Aufruf (seit 0.34.75), in derselben Folge.
        T, ex = K.TILE, ecke.x
        schatten = []
        for (tx, ty, name, sy, info) in fest:
            st = info[0]
            if st is not None and not info[1]:            # nicht voll (_stehend_fest)
                # Ein Kaktus, ein Fass, eine Kiste: der Schatten hat ihre Form.
                # Bis 0.34.18 warf jedes Hindernis den Schatten der ganzen
                # Kachel - ein dunkles Quadrat um den Kaktus, das aussah, als
                # stuende ein Block darunter (gemeldet).
                schatten.append((self._kleinschatten(st, dunkel), (tx * T - ex, sy)))
                continue
            schatten.append((sch, (tx * T - ex, sy)))
        _viele_blits(ziel, schatten)
        auge_h = K.PERSPEKTIVE["brennweite"] if auge is None else auge
        self._augen[index] = (ecke.x + zw / 2.0, ecke.y + zh / 2.0, auge_h)
        auftrag = (ziel, e, satz, fest, ecke, dunkel, auge_h)
        if aufschieben:
            self._stehend_offen = auftrag
        else:
            self._stehende_zeichnen(*auftrag)

    def _bodenstueck(self, welt, e, satz, boden_namen, cx: int, cy: int, dunkel,
                     deckend: bool = False):
        """Ein Block Boden (BODEN_STUECK mal BODEN_STUECK Kacheln), fertig
        gezeichnet: (Flaeche oder None, [(tx, ty, Bildname) fester Kacheln]).

        Gemerkt, solange sich die Kacheln darin und rundherum nicht aendern -
        geprueft an einem Abdruck der Kachelnummern bei jedem Aufruf, damit
        auch eine Kachel auffaellt, die jemand direkt in `kacheln` schreibt
        (die Tests tun das). Der Rand gehoert dazu: weiche Bodenarten franst
        der Nachbar aus. Der Eintrag haelt seine Ebene fest, wie bei
        `dunkel`: eine neue Ebene mit der id einer alten bekaeme sonst deren
        Block."""
        C = BODEN_STUECK
        b, h = e.breite, e.hoehe
        x0, y0 = cx * C, cy * C
        x1, y1 = min(b, x0 + C), min(h, y0 + C)
        kacheln = e.kacheln
        ax0, ax1 = max(0, x0 - 1), min(b, x1 + 1)
        # Der Abdruck als Liste der Zeilenstuecke (seit 0.34.75): dieselbe
        # Gleichheit wie vorher mit bytes, aber ohne jede Kachelnummer erst
        # umzuwandeln - das kostete je Bild mehr als der Vergleich.
        abdruck = [kacheln[ty * b + ax0: ty * b + ax1]
                   for ty in range(max(0, y0 - 1), min(h, y1 + 1))]
        schluessel = (id(e), cx, cy, dunkel, getattr(welt, "satz", ""))
        hit = self._boden_stuecke.get(schluessel)
        if (hit is not None and hit[3] is e and hit[0] == abdruck
                and (deckend or not hit[4])):
            return hit[1], hit[2]
        T = K.TILE
        bild = self.bilder.bild
        flaeche = None
        mit_schluessel = False
        fest = []
        for ty in range(y0, y1):
            zeile = ty * b
            for tx in range(x0, x1):
                kachel = kacheln[zeile + tx]
                if kachel == K.LEER:
                    continue
                daten = K.KACHELN[kachel]
                s = None
                if daten["fest"]:
                    # Mit Abwechslung, auch aus dem Satz (seit 0.34.131).
                    name_f = K.satz_bild(satz, daten, e.variante[zeile + tx])
                    st = self._stehend(name_f, daten)
                    fest.append((tx, ty, name_f,
                                 self._stehend_fest(e, satz, tx, ty, name_f, st)))
                    if st is None or st["rahmen"] == (0, 0, T, T):
                        continue
                    # Ein Fass oder eine Kiste steht auf Boden: der ist
                    # rundherum zu sehen, also zuerst der Boden.
                    s = bild(boden_namen[e.variante[zeile + tx]])
                else:
                    if kachel == K.BODEN:
                        name = boden_namen[e.variante[zeile + tx]]
                    else:
                        name = K.satz_bild(satz, daten, e.variante[zeile + tx])
                    if daten.get("weich"):
                        s = self._weicher_rand(name, e, tx, ty, boden_namen[0])
                    else:
                        s = bild(name)
                if flaeche is None:
                    flaeche = pygame.Surface((C * T, C * T), pygame.SRCALPHA)
                flaeche.blit(s, ((tx - x0) * T, (ty - y0) * T))
        if flaeche is not None:
            if dunkel is not None:
                flaeche.fill((dunkel, dunkel, dunkel), special_flags=pygame.BLEND_RGB_MULT)
            try:
                flaeche = flaeche.convert_alpha()
                # Ganz deckend (seit 0.34.75): dann ohne Alphakanal. Ein
                # Pixel mit Alpha 255 wird beim Blit genau kopiert - dasselbe
                # Bild, aber ohne Mischen je Pixel, rund dreimal so schnell.
                flaeche = _deckend_wenn_moeglich(flaeche)
                if deckend and flaeche.get_flags() & pygame.SRCALPHA:
                    flaeche, mit_schluessel = _mit_farbschluessel(flaeche)
            except pygame.error:
                pass                          # ohne Fenster (Tests): so lassen
        if len(self._boden_stuecke) > BODEN_MERKEN:
            self._boden_stuecke.clear()
        # Der letzte Eintrag: ob das Stueck einen Farbschluessel traegt - dann
        # taugt es nur fuer ein deckendes Ziel und wird sonst neu gebaut.
        self._boden_stuecke[schluessel] = (abdruck, flaeche, fest, e, mit_schluessel)
        return flaeche, fest

    def _stehend_fest(self, e, satz, tx: int, ty: int, name: str, st):
        """Was an einer stehenden Kachel nicht von der Kamera abhaengt (seit
        0.34.75): ihre Masse, ob sie die Kachel ganz fuellt, welche Seiten
        ein gleich hoher Nachbar verdeckt, und ihre Seitenfarbe. Gerechnet
        einmal je Bodenstueck - das wird neu gebaut, sobald sich eine Kachel
        darin oder am Rand aendert, und der Rand enthaelt alle Nachbarn.
        Vorher je Bild und Kachel vier Nachbarfragen (rund 450 je Bild).

        Dieselbe Rechnung wie `nachbar_deckt` in `_stehende_zeichnen`: ob der
        Nachbar dort ueber das Kachelbild oder ueber den Satz nachgeschlagen
        wird, ergibt fuer jede Kachel dieselben Masse (geprueft)."""
        if st is None:
            return (None, False, True, True, True, True, None)
        T = K.TILE
        voll = (0, 0, T, T)
        voll_k = st["rahmen"] == voll
        grund = self._seitenfarbe(name)
        # Dahinter die Masse aus K.STEHEN, fertig ausgepackt: Rahmen, Hoehe,
        # rund, und ob alle vier Seiten zu sind ("zu").
        masse = tuple(st["rahmen"]) + (st["hoehe"], st["form"] == "rund")
        if not voll_k:
            return (st, False, True, True, True, True, grund) + masse + (False,)

        def deckt(nx, ny):
            daten = K.KACHELN[e.kachel(nx, ny)]
            if not daten["fest"]:
                return False
            n = self._stehend(satz.get(daten["bild"], daten["bild"]), daten)
            if n is None:
                return True
            return n["rahmen"] == voll and n["hoehe"] >= st["hoehe"]
        offen = (not deckt(tx, ty - 1), not deckt(tx, ty + 1),
                 not deckt(tx - 1, ty), not deckt(tx + 1, ty))
        return (st, True) + offen + (grund,) + masse + (not any(offen),)

    def _kleinschatten(self, st: dict, dunkel):
        """Der Schlagschatten eines Hindernisses in seiner eigenen Form
        (Kreis oder Rechteck aus K.STEHEN), nach unten rechts wie der der
        Mauern - je Form und Helligkeit einmal gebaut."""
        schluessel = (st["form"], st["rahmen"], dunkel)
        cache = self.__dict__.setdefault("_kleinschatten_cache", {})
        hit = cache.get(schluessel)
        if hit is None:
            versatz = K.DEKAL["wand_versatz"]
            T = K.TILE
            hit = pygame.Surface((T + versatz, T + versatz), pygame.SRCALPHA)
            rx, ry, rb, rh = st["rahmen"]
            for i in range(versatz):
                a = int(96 * (1 - i / versatz) ** 1.4)
                r = pygame.Rect(rx + i, ry + i, rb, rh)
                if st["form"] == "rund":
                    pygame.draw.ellipse(hit, (0, 0, 0, a), r)
                else:
                    pygame.draw.rect(hit, (0, 0, 0, a), r, border_radius=2)
            if dunkel is not None:
                hit = self.dunkel(hit, dunkel)
            cache[schluessel] = hit
        return hit

    def _weicher_rand(self, name: str, e, tx: int, ty: int, grund_name: str):
        """Das Bild einer weichen Bodenart (Piste, Kies), dort ausgefranst,
        wo Sand angrenzt (seit 0.34.6).

        Ohne das zog jede Kachelkante zwischen Piste und Sand eine gerade
        Linie, und ein Weg, der schraeg lief, war eine Treppe aus
        Quadraten. Jetzt greift der Sand an diesen Seiten ein paar Pixel
        unregelmaessig hinein. An den Ecken ist die Tiefe immer gleich,
        damit zwei Kacheln uebereinander ohne Sprung aneinanderpassen.
        Je Bild und Nachbarschaft einmal gerechnet und gemerkt."""
        maske = 0
        for bit, (dx, dy) in enumerate(((0, -1), (1, 0), (0, 1), (-1, 0))):
            if e.kachel(tx + dx, ty + dy) in self._grundartig:
                maske |= 1 << bit
        if not maske:
            return self.bilder.bild(name)
        schluessel = (name, grund_name, maske)
        hit = self._weich.get(schluessel)
        if hit is not None:
            return hit
        T = K.TILE
        hit = self.bilder.bild(name).copy()
        grund = self.bilder.bild(grund_name)
        zufall = random.Random("%s|%s|%d" % (name, grund_name, maske))
        for bit in range(4):
            if not maske & (1 << bit):
                continue
            phase = zufall.uniform(0, math.tau)
            for i in range(T):
                # Tiefe: Welle plus Rauschen, zu den Ecken hin auf 3 px.
                ende = min(i, T - 1 - i) / 6.0
                welle = 3.5 + 2.5 * math.sin(i * 0.55 + phase) + zufall.uniform(-1.2, 1.2)
                tiefe = 3.0 + (welle - 3.0) * min(1.0, ende)
                for j in range(int(tiefe) + 1):
                    if j == int(tiefe) and zufall.random() < 0.5:
                        continue                # ein Pixel Uebergang, gestreut
                    x, y = ((i, j), (T - 1 - j, i), (i, T - 1 - j), (j, i))[bit]
                    hit.set_at((x, y), grund.get_at((x, y)))
        if len(self._weich) > 1000:
            self._weich.clear()
        self._weich[schluessel] = hit
        return hit

    def _stehend_an(self, welt, e, x: float, y: float):
        """Die Masse der stehenden Kachel am Weltpunkt, wenn er in ihrer
        Grundflaeche liegt - sonst None."""
        T = K.TILE
        tx, ty = int(x // T), int(y // T)
        daten = K.KACHELN[e.kachel(tx, ty)]
        if not daten["fest"]:
            return None
        satz = self.SAETZE.get(getattr(welt, "satz", ""), {})
        st = self._stehend(satz.get(daten["bild"], daten["bild"]), daten)
        if st is None:
            return None
        rx, ry, rb, rh = st["rahmen"]
        lx, ly = x - tx * T - rx, y - ty * T - ry
        if not (0 <= lx < rb and 0 <= ly < rh):
            return None
        if st["form"] == "rund":
            mx, my = rb / 2.0, rh / 2.0
            if (lx - mx) ** 2 + (ly - my) ** 2 > mx * mx:
                return None
        return st

    def verdeckt(self, welt, index: int, pos, hoehe: float) -> bool:
        """Verdeckt eine Mauer, Kiste oder ein Fass diesen Punkt vom Auge?

        Ein Strahl vom Punkt (in `hoehe` ueber dem Boden) zum Auge: liegt
        er irgendwo innerhalb einer stehenden Kachel tiefer als deren
        Oberkante, sieht das Auge den Punkt nicht. Weil das Auge hoch steht
        (die Brennweite, rund 430 Welt-Pixel), steigt der Strahl schnell:
        nach ein paar Pixeln ist er ueber jeder Mauer, und nur dieses kurze
        Stueck wird abgetastet.

        Gebraucht fuer alles, was ueber dem Boden ist und klein genug, um
        ganz oder gar nicht zu sehen zu sein - Geschosse, Funken,
        Muendungsfeuer, was faellt. Figuren am Boden brauchen das nicht:
        sie werden vor den Mauern gezeichnet und Pixel fuer Pixel von ihnen
        verdeckt.
        """
        auge = self._augen.get(index)
        if auge is None or not hasattr(welt, "ebene"):
            return False                 # ohne Karte (Probewelt) nichts davor
        ax, ay, ah = auge
        hoechste = self._hoechste_stehende
        if hoehe >= hoechste:
            return False
        dx, dy = ax - pos[0], ay - pos[1]
        weit = math.hypot(dx, dy)
        if weit < 1.0:
            return False
        bis = (hoechste - hoehe) / max(1.0, ah - hoehe)
        # Jeden Pixel: mit groberen Schritten (erst 3 px) rutschte eine
        # Kugel knapp hinter der Mauer durch die Luecke zwischen zwei Proben.
        schritte = int(weit * bis) + 1
        e = welt.ebene(index)
        # Dieselbe Abtastung wie mit _stehend_an, nur ohne die Nachschlagungen
        # je Probe (seit 0.34.75): Kacheln, Satz und die Masse je Kachelart
        # einmal holen. Ein Geschoss fragt das in jedem Bild.
        T = K.TILE
        satz = self.SAETZE.get(getattr(welt, "satz", ""), {})
        kacheln, breite, hoehe_k = e.kacheln, e.breite, e.hoehe
        tabelle = K.KACHELN
        leer = K.LEER
        je_art = {}
        px, py = pos[0], pos[1]
        for i in range(1, schritte + 1):
            t = bis * i / schritte
            x, y = px + dx * t, py + dy * t
            tx, ty = int(x // T), int(y // T)
            if 0 <= tx < breite and 0 <= ty < hoehe_k:
                kachel = kacheln[ty * breite + tx]
            else:
                kachel = leer
            if kachel in je_art:
                st = je_art[kachel]
            else:
                daten = tabelle[kachel]
                st = (self._stehend(satz.get(daten["bild"], daten["bild"]), daten)
                      if daten["fest"] else None)
                je_art[kachel] = st
            if st is None:
                continue
            rx, ry, rb, rh = st["rahmen"]
            lx, ly = x - tx * T - rx, y - ty * T - ry
            if not (0 <= lx < rb and 0 <= ly < rh):
                continue
            if st["form"] == "rund":
                mx, my = rb / 2.0, rh / 2.0
                if (lx - mx) ** 2 + (ly - my) ** 2 > mx * mx:
                    continue
            if st["hoehe"] > hoehe + (ah - hoehe) * t:
                return True
        return False

    def stehende_nachholen(self) -> None:
        """Die mit `aufschieben` gemerkten Waende jetzt zeichnen.

        Eine Mauer hat Hoehe, eine Figur steht am Boden. Wer vom Auge aus
        hinter einer Mauer steht, liegt im Bild unter ihrer Oberseite und
        wird von ihr verdeckt - das ist so gewollt. Wer davor steht, liegt
        nie darunter: Seiten und Oberseite reichen vom Fusspunkt der Mauer
        nur nach aussen, vom Auge weg.
        """
        auftrag = getattr(self, "_stehend_offen", None)
        self._stehend_offen = None
        if auftrag is not None:
            self._stehende_zeichnen(*auftrag)

    def _dekale_zeichnen(self, ziel, e, ecke, dunkel) -> None:
        d = e.dekale
        if not d:
            return
        zw, zh = ziel.get_size()
        dx0 = max(0, int(ecke.x // DEKAL_PIXEL))
        dy0 = max(0, int(ecke.y // DEKAL_PIXEL))
        dx1 = min((e.pixel_breite - 1) // DEKAL_PIXEL,
                  int((ecke.x + zw) // DEKAL_PIXEL))
        dy1 = min((e.pixel_hoehe - 1) // DEKAL_PIXEL,
                  int((ecke.y + zh) // DEKAL_PIXEL))
        for ky in range(dy0, dy1 + 1):
            for kx in range(dx0, dx1 + 1):
                q = d.get((kx, ky))
                if q is None:
                    continue
                if dunkel is not None:
                    q = self.dunkel(q, dunkel)
                ziel.blit(q, (kx * DEKAL_PIXEL - ecke.x,
                              ky * DEKAL_PIXEL - ecke.y))

    # ---- Stehende Kacheln: Waende und Barrikaden mit Hoehe --------------
    @staticmethod
    def _stehend(name: str, daten: dict):
        """Die Masse aus K.STEHEN fuer ein Kachelbild, oder None (flach)."""
        return K.STEHEN.get(name) or K.STEHEN.get(daten.get("name", ""))

    def _seitenfarbe(self, name: str) -> tuple:
        """Grundfarbe der Seiten: das gemalte Kachelbild, gemittelt - so
        passen sie zu dem, was man vorher von der Kachel kannte."""
        hit = self._seiten_farbe.get(name)
        if hit is None:
            hit = tuple(pygame.transform.average_color(self.bilder.bild(name))[:3])
            self._seiten_farbe[name] = hit
        return hit

    def _oberseite(self, name: str, breite: int, hoehe: int, dunkel):
        """Das Bild der Oberseite in der Groesse, in der es gerade steht."""
        schluessel = (name, breite, hoehe, dunkel)
        hit = self._oberseiten.get(schluessel)
        if hit is None:
            try:
                quelle = self.bilder.bild(name + "_oben")
            except Exception:                   # noqa: BLE001
                quelle = self.bilder.bild(name)
            hit = pygame.transform.scale(quelle, (max(1, breite), max(1, hoehe)))
            if dunkel is not None:
                hit = self.dunkel(hit, dunkel)
            hit = _deckend_wenn_moeglich(hit)
            if len(self._oberseiten) > 300:
                self._oberseiten.clear()
            self._oberseiten[schluessel] = hit
        return hit

    def _stehende_zeichnen(self, ziel, e, satz, fest, ecke, dunkel,
                           auge: float) -> None:
        """Waende und Barrikaden mit Hoehe, in Perspektive (K.STEHEN).

        Dieselbe Rechnung wie fuer die Plateaus: ein Punkt in der Hoehe h
        liegt vom Auge aus um den Faktor auge / (auge - h) weiter von der
        Bildmitte weg als sein Fusspunkt. Die Oberseite rueckt also nach
        aussen, und dazwischen sieht man genau die Seiten, die zur Mitte
        schauen - links von einem eine Ostseite, oberhalb eine Suedseite.
        Das Auge steht ueber der Mitte der Zielflaeche; das gilt fuer das
        normale Bild wie fuer die Tiefenflaeche einer anderen Ebene.

        Gezeichnet wird in zwei Schichten: erst alle Seiten von aussen nach
        innen, dann alle Oberseiten. Eine Oberseite verdeckt so, was hinter
        ihr steht, und keine Seite ragt ueber eine Oberseite.
        """
        T = K.TILE
        zw, zh = ziel.get_size()
        cx, cy = zw / 2.0, zh / 2.0
        hell_f = 1.0 if dunkel is None else dunkel / 255.0
        licht = {(0, 1): 0.82, (1, 0): 0.66, (-1, 0): 0.74, (0, -1): 0.56}
        voll = (0, 0, T, T)
        toene = self._toene
        if len(toene) > 4000:
            toene.clear()

        def ton(grund, f, faktor=1.0):
            # Dieselben wenigen Toene jedes Bild fuer hunderte Seiten und
            # Fugen - gemerkt statt je Seite neu gerechnet (seit 0.34.57).
            schluessel = (grund, f, faktor)
            farbe = toene.get(schluessel)
            if farbe is None:
                farbe = tuple(max(0, min(255, int(c * f * faktor))) for c in grund)
                toene[schluessel] = farbe
            return farbe

        # Welche Seiten ein Nachbar verdeckt, steht seit 0.34.75 fertig in
        # `info` (Renderer._stehend_fest, je Bodenstueck gerechnet): eine
        # Seite gibt es nicht, wo eine gleich hohe volle Kachel anschliesst -
        # eine lange Mauer ist eine Mauer, nicht zwanzig.
        # Die Schleife ist auf Tempo geschrieben (seit 0.34.75): sie laeuft
        # jedes Bild fuer jede sichtbare Mauer. Dieselbe Rechnung wie vorher,
        # nur ohne Hilfsfunktionen, Woerterbuecher und doppelte Wege.
        ex = ecke.x
        seiten, oben, flach, kanten = [], [], [], []
        anhaengen_oben = oben.append
        oberseiten = self._oberseiten

        # Die Oberseite in fester Groesse (seit 0.34.77): je Mauerart und Hoehe
        # immer dieselbe, aufgerundete - gezeigt wird davon nur, was die
        # gerundeten Ecken in diesem Bild verlangen. Vorher wurde sie jedes
        # Bild auf die gerade gerundete Groesse skaliert, die beim Bewegen
        # zwischen zwei Werten sprang, und das Muster darauf veraenderte
        # sich sichtbar (gemeldet: "die Textur veraendert sich beim
        # Umschauen"). Grosser als die Ecken verlangen ist sie nie: zwei
        # gerundete Ecken liegen hoechstens aufgerundet weit auseinander.
        feste_masse = {}

        def oben_dazu(weg, name, x, y, x1, y1, rb, rh, hoehe):
            masse = feste_masse.get((rb, rh, hoehe))
            if masse is None:
                k = faktoren[hoehe]
                masse = feste_masse[(rb, rh, hoehe)] = (
                    max(1, x1 - x, math.ceil(rb * k - 1e-6)),
                    max(1, y1 - y, math.ceil(rh * k - 1e-6)))
            bild_o = oberseiten.get((name, masse[0], masse[1], dunkel))
            if bild_o is None:
                bild_o = self._oberseite(name, masse[0], masse[1], dunkel)
            anhaengen_oben((weg, bild_o, (x, y), (0, 0, x1 - x, y1 - y)))
        faktoren = {}
        achse_x, achse_y = {}, {}
        l_n, l_s, l_w, l_o = licht[(0, -1)], licht[(0, 1)], licht[(-1, 0)], licht[(1, 0)]
        for (tx, ty, name, sy, info) in fest:
            st = info[0]
            if st is None:
                flach.append((tx, ty, name, sy))
                continue
            (st, voll_k, offen_n, offen_s, offen_w, offen_o, grund,
             rx, ry, rb, rh, hoehe, rund, zu) = info
            x0, y0 = tx * T - ex + rx, sy + ry
            # Die Perspektive je Spalte und je Zeile nur einmal im Bild
            # (seit 0.34.75): sie haengt an x0 (bzw. y0), der Breite und der
            # Hoehe der Mauer - dieselben Formeln, nur nicht fuer jede Kachel
            # einer Spalte noch einmal.
            ax = achse_x.get((x0, rb, hoehe))
            if ax is None:
                k = faktoren.get(hoehe)
                if k is None:
                    k = faktoren[hoehe] = auge / max(1.0, auge - hoehe)
                x1 = x0 + rb
                ox0, ox1 = cx + (x0 - cx) * k, cx + (x1 - cx) * k
                ax = achse_x[(x0, rb, hoehe)] = (x1, ox0, ox1, round(ox0), round(ox1),
                                                 (x0 + x1) / 2 - cx)
            ay = achse_y.get((y0, rh, hoehe))
            if ay is None:
                k = faktoren.get(hoehe)
                if k is None:
                    k = faktoren[hoehe] = auge / max(1.0, auge - hoehe)
                y1 = y0 + rh
                oy0, oy1 = cy + (y0 - cy) * k, cy + (y1 - cy) * k
                ay = achse_y[(y0, rh, hoehe)] = (y1, oy0, oy1, round(oy0), round(oy1),
                                                 (y0 + y1) / 2 - cy)
            x1, ox0, ox1, rx_, rx1_, mx = ax
            y1, oy0, oy1, ry_, ry1_, my = ay
            weg = mx ** 2 + my ** 2
            if rund:
                seiten.append((weg, "rund", (x0, y0, x1, y1, ox0, oy0, ox1, oy1),
                               grund, st))
                oben_dazu(weg, name, rx_, ry_, rx1_, ry1_, rb, rh, hoehe)
                continue
            if zu:
                oben_dazu(weg, name, rx_, ry_, rx1_, ry1_, rb, rh, hoehe)
                continue
            # Die Kante der Oberseite: rundherum, wo die Mauer endet -
            # oben und links im Licht, unten und rechts im Schatten.
            rb_, rh_ = rx1_ - rx_ - 1, ry1_ - ry_ - 1
            if offen_n:
                kanten.append(((rx_, ry_), (rx_ + rb_, ry_), True, grund))
            if offen_w:
                kanten.append(((rx_, ry_), (rx_, ry_ + rh_), True, grund))
            if offen_s:
                kanten.append(((rx_, ry_ + rh_), (rx_ + rb_, ry_ + rh_), False, grund))
            if offen_o:
                kanten.append(((rx_ + rb_, ry_), (rx_ + rb_, ry_ + rh_), False, grund))
            if offen_n and oy0 > y0 + 0.5:
                seiten.append((weg, "block", (((x0, y0), (x1, y0)), ((ox1, oy0), (ox0, oy0))),
                               grund, st, l_n))
            if offen_s and oy1 < y1 - 0.5:
                seiten.append((weg, "block", (((x0, y1), (x1, y1)), ((ox1, oy1), (ox0, oy1))),
                               grund, st, l_s))
            if offen_w and ox0 > x0 + 0.5:
                seiten.append((weg, "block", (((x0, y0), (x0, y1)), ((ox0, oy1), (ox0, oy0))),
                               grund, st, l_w))
            if offen_o and ox1 < x1 - 0.5:
                seiten.append((weg, "block", (((x1, y0), (x1, y1)), ((ox1, oy1), (ox1, oy0))),
                               grund, st, l_o))
            oben_dazu(weg, name, rx_, ry_, rx1_, ry1_, rb, rh, hoehe)

        for (tx, ty, name, sy) in flach:
            s = self.bilder.bild(name)
            if dunkel is not None:
                s = self.dunkel(s, dunkel)
            ziel.blit(s, (tx * K.TILE - ecke.x, sy))

        # Absteigend nach `weg`; Gleiches bleibt in seiner Reihenfolge (die
        # Sortierung ist stabil, auch mit reverse) - wie vorher mit -weg.
        seiten.sort(key=_erstes, reverse=True)
        linie = pygame.draw.line
        # Die drei Toene einer Seite haengen nur an Farbe und Licht: je Bild
        # einmal geholt (seit 0.34.75), dieselben Werte wie ton().
        seiten_toene = {}
        for eintrag in seiten:
            if eintrag[1] == "block":
                _w, _art, (basis, kopf), grund, st, l = eintrag
                drei = seiten_toene.get((grund, l))
                if drei is None:
                    f = l * hell_f
                    drei = seiten_toene[(grund, l)] = (ton(grund, f), ton(grund, f, 0.68),
                                                       ton(grund, f, 0.42))
                pygame.draw.polygon(ziel, drei[0], [basis[0], basis[1], kopf[0], kopf[1]])
                # Querfugen: Steinlagen an der Mauer, Bretter an der Kiste.
                fuge = drei[1]
                n = st["fugen"]
                (b0x, b0y), (b1x, b1y) = basis
                (k0x, k0y), (k1x, k1y) = kopf
                for i in range(1, n + 1):
                    t = i / (n + 1)
                    linie(ziel, fuge, (b0x + (k1x - b0x) * t, b0y + (k1y - b0y) * t),
                          (b1x + (k0x - b1x) * t, b1y + (k0y - b1y) * t), 1)
                linie(ziel, drei[2], basis[0], basis[1], 1)
            else:
                _w, _art, (x0, y0, x1, y1, ox0, oy0, ox1, oy1), grund, st = eintrag
                # Ein Fass ist ein Zylinder: Kreise vom Fuss bis zum Deckel,
                # unten dunkel, oben hell. Ein paar Kreise genuegen - der
                # Versatz zwischen Fuss und Deckel ist nur ein paar Pixel.
                fx, fy, fr = (x0 + x1) / 2, (y0 + y1) / 2, (x1 - x0) / 2
                kx, ky, kr = (ox0 + ox1) / 2, (oy0 + oy1) / 2, (ox1 - ox0) / 2
                schritte = max(2, int(abs(kx - fx) + abs(ky - fy)) + 1)
                n = st["fugen"]
                reifen = {int(schritte * i / (n + 1)) for i in range(1, n + 1)}
                for i in range(schritte + 1):
                    t = i / schritte
                    f = (0.45 + 0.4 * t) * hell_f
                    if i in reifen:
                        f *= 0.62
                    pygame.draw.circle(ziel, tuple(int(c * f) for c in grund),
                                       (round(fx + (kx - fx) * t), round(fy + (ky - fy) * t)),
                                       max(1, round(fr + (kr - fr) * t)))

        oben.sort(key=_erstes, reverse=True)
        ziel.blits([(bild_o, ort, teil) for _w, bild_o, ort, teil in oben], doreturn=False)
        kanten_toene = {}
        for a_, b_, im_licht, grund in kanten:
            farbe = kanten_toene.get((grund, im_licht))
            if farbe is None:
                farbe = kanten_toene[(grund, im_licht)] = ton(
                    grund, (1.45 if im_licht else 0.38) * hell_f)
            linie(ziel, farbe, a_, b_, 1)

    def wesen_zeichnen(self, ziel, welt, index, ecke, alpha, dunkel=None) -> None:
        """Was am Boden steht oder liegt: Figuren, Beute, Granaten.

        Seit 0.34.5 ohne das, was fliegt (`hoehe_bild` > 0, also Geschosse
        und Raketen) - das kommt nach den Mauern in `luft_zeichnen` - und
        ohne die Lebensbalken: die sind Anzeige und gehoeren ueber die
        Mauern (`balken_zeichnen`)."""
        # Wer im Buggy sitzt, ist Teil von dessen Bild (seit 0.34.9) und
        # wird nicht noch einmal obendrauf gezeichnet.
        liste = [w for w in welt.wesen if w.ebene == index and w.lebt
                 and w.hoehe_bild <= 0 and not getattr(w, "im_fahrzeug", False)]
        # Was auf etwas anderem liegt (C4 auf dem Buggy), zuletzt. Panzer und
        # Panzerwagen (seit 0.34.59, `schicht` 0) vor allem anderen: ihre
        # Wannen sind niedrig, und nach y sortiert lag alles, was noerdlich
        # von ihnen steht, unter ihren Ketten. Ihre Tuerme kommen nach den
        # Figuren (`aufbauten_zeichnen`).
        liste.sort(key=lambda w: (getattr(w, "schicht", 1), getattr(w, "obenauf", False),
                                  w.pos.y))
        # Was weit ausserhalb des Bildes steht, kann nichts hineinzeichnen
        # (seit 0.34.89): die 3D-Schichten ruecken nach aussen, weg von der
        # Mitte, Schatten und Spur nur ein paar Pixel, ein Panzer samt Rohr
        # keine 120. Mit diesem Rand bleibt das Bild Pixel fuer Pixel gleich.
        rand = K.ZEICHNEN_RAND
        x_max, y_max = ziel.get_width() + rand, ziel.get_height() + rand
        for w in liste:
            p = boden = w.zeichenpos(alpha) - ecke  # Stelle, auf der es steht
            if not (-rand < p.x < x_max and -rand < p.y < y_max):
                continue
            if getattr(w, "zeichnet_selbst", False):
                w.zeichnen_unten(self, ziel, p, dunkel)
                continue
            schatten_bild = getattr(w, "schatten_bild", None)
            # Was hoch oben fliegt (Tragschrauber), wirft seinen Schatten in der
            # Luftschicht (luft.py) - sonst waeren es zwei (seit 0.34.119).
            if schatten_bild and not getattr(w, "hoch_oben", False):
                # Ein eigener, mitgedrehter Schatten fuer alles, was nicht
                # rund ist. Er faellt nach unten rechts wie der der Mauern,
                # egal wohin das Wesen schaut.
                sch = self.bilder.gedreht(schatten_bild, _gezeigter_winkel(w))
                ziel.blit(sch, (boden.x - sch.get_width() / 2 + 2,
                                boden.y - sch.get_height() / 2 + 4))
            if w.schatten:
                f = (1.0 if w.flug <= 0
                     else max(K.DEKAL["schatten_luft"], 1.0 - w.flug / 240.0))
                sch = self.schatten(w.radius, f)
                ziel.blit(sch, (boden.x - sch.get_width() / 2 + 1,
                                boden.y - sch.get_height() / 2 + 3))
            if w.flug > 0:
                # Der Schatten gehoert auf diesen Boden, das Wesen selbst
                # nicht: es haengt zwischen den Ebenen und wird nach allen
                # Ebenen gezeichnet, mit dem Massstab seiner eigenen Hoehe.
                continue
            hub = getattr(w, "luft_hub", 0.0)
            if hub:
                p = p - pygame.Vector2(0, hub)     # in die Luft (seit 0.34.138)
            if w.spur is not None and w.tempo.length_squared() > 1:
                r = w.tempo.normalize()
                pygame.draw.line(ziel, (128, 80, 30), p - r * 17, p - r * 5, 1)
                pygame.draw.line(ziel, w.spur, p - r * 6, p, 1)
            bild = w.bild                 # eine Eigenschaft: einmal fragen (0.34.75)
            if bild is None or getattr(w, "hoch_oben", False):
                continue                  # hoch oben: eigene Schicht (Drohne)
            if getattr(w, "schirm_hoehe", 0.0) > 0.0:
                continue                  # am Fallschirm: schlacht.abwuerfe_zeichnen (0.34.100)
            if (getattr(w, "dash_rest", 0.0) > 0.0
                    or getattr(w, "dash_bild_rest", 0.0) > 0.0):
                self.dash_zeichnen(ziel, p, w)
            # Was ein Boss gleich tut, gehoert unter ihn und nicht auf
            # ihn - sonst verdeckt der Ring genau die Gestalt, die man
            # ansehen muss.
            if getattr(w, "f_vorlauf", 0.0) > 0.0:
                self.ankuendigung(ziel, p, w)
            roh = self.bilder.gedreht(bild, _gezeigter_winkel(w))
            s = roh
            if dunkel is not None:
                s = self.dunkel(s, dunkel)
            elif w.blitz > 0:
                s = s.copy()
                s.fill((210, 210, 210), special_flags=pygame.BLEND_RGB_ADD)
            self.figur_zeichnen(ziel, s, p, getattr(w, "hoehe_3d", 0.0), index,
                                roh, dunkel)
            if getattr(w, "schild", False) and w.lebt and not getattr(w, "am_boden", False):
                # Das Schild des SCHILDTRAEGERS (seit 0.34.138): vor der Figur,
                # mit ihr gedreht.
                sch = self.bilder.gedreht("schild_klasse", _gezeigter_winkel(w))
                if dunkel is not None:
                    sch = self.dunkel(sch, dunkel)
                ziel.blit(sch, (p.x - sch.get_width() / 2, p.y - sch.get_height() / 2))

    def hoch_oben_zeichnen(self, ziel, bild: str, p, winkel: float) -> None:
        """Was hoch ueber allem fliegt (seit 0.34.96, die Drohne): ein
        Schatten am Boden, das Bild etwas groesser und hoeher - so sieht man,
        dass es ueber den Mauern ist."""
        h = K.HOCH_OBEN
        sch = self.schatten(7, 0.55)
        ziel.blit(sch, (p.x - sch.get_width() / 2 + h["schatten"][0],
                        p.y - sch.get_height() / 2 + h["schatten"][1]))
        s = self.bilder.gedreht(bild, winkel)
        if h["gross"] != 1.0:
            s = pygame.transform.scale(s, (max(1, int(s.get_width() * h["gross"])),
                                           max(1, int(s.get_height() * h["gross"]))))
        ziel.blit(s, (p.x - s.get_width() / 2, p.y - s.get_height() / 2 - h["hoehe"]))

    def figur_zeichnen(self, ziel, s, p, hoehe: float, index: int,
                       roh=None, dunkel=None) -> None:
        """Ein Bild mit Hoehe zeichnen, in derselben Perspektive wie die
        stehenden Kacheln (seit 0.34.25, K.FIGUREN_3D).

        Ein Punkt in der Hoehe h liegt vom Auge aus um auge / (auge - h)
        weiter von der Bildmitte weg als sein Fusspunkt (siehe
        `_stehende_zeichnen`). Das Bild ist der Deckel und kommt dorthin;
        von der Stelle am Boden bis darunter liegen Schichten seines
        Umrisses, unten dunkel, oben heller - die Seitenwand. In der Mitte
        des Bildes liegt alles uebereinander, und man sieht die Figur von
        oben, wie jede Kiste dort auch.

        `roh`: das Bild ohne Abdunkeln und Aufblitzen - daraus kommt die
        Seitenwand. Sie soll nicht mitblitzen, und so wird sie je Bild
        nur einmal gebaut statt in jedem Bild neu.
        """
        f3 = K.FIGUREN_3D
        w2, h2 = s.get_width() / 2, s.get_height() / 2
        if hoehe <= 0 or not f3["an"]:
            ziel.blit(s, (p.x - w2, p.y - h2))
            return
        auge = self._augen.get(index)
        auge_h = auge[2] if auge is not None else K.PERSPEKTIVE["brennweite"]
        zw, zh = ziel.get_size()
        mitte = pygame.Vector2(zw / 2.0, zh / 2.0)
        k = auge_h / max(1.0, auge_h - hoehe)
        oben = mitte + (pygame.Vector2(p) - mitte) * k
        weg = oben - p
        # Eine Schicht je Pixel Versatz, aber hoechstens `schichten_max`:
        # eine Horde am Bildrand kostete sonst auf dem iPhone spuerbar
        # Zeit. Die Luecken von da an liegen innerhalb des Umrisses, den
        # die Nachbarschichten ohnehin decken.
        schritte = min(int(max(abs(weg.x), abs(weg.y))), f3["schichten_max"])
        # Alle Schichten und der Deckel in einem Aufruf (seit 0.34.75), in
        # derselben Folge wie vorher einzeln.
        auftraege = []
        if schritte >= 1:
            quelle = roh if roh is not None else s
            stufen = f3["seite_stufen"]
            je_stufe = {}           # dieselbe Stufe, dieselbe Schicht (seit 0.34.75)
            for i in range(schritte):
                t = i / schritte
                # Unten dunkel, unter dem Deckel heller - wie die Mauern.
                stufe = min(stufen - 1, int(t * stufen))
                schicht = je_stufe.get(stufe)
                if schicht is None:
                    hell = f3["seite_unten"] + (f3["seite_oben"] - f3["seite_unten"]) \
                        * stufe / max(1, stufen - 1)
                    schicht = je_stufe[stufe] = self._seite(quelle, round(hell, 3), dunkel)
                seite, rand = schicht
                auftraege.append((seite, (p.x + weg.x * t - w2 + rand[0],
                                          p.y + weg.y * t - h2 + rand[1])))
        auftraege.append((s, (oben.x - w2, oben.y - h2)))
        _viele_blits(ziel, auftraege)

    def _seite(self, s, hell: float, dunkel=None):
        """Eine Schicht der Seitenwand: der Umriss des Bildes, gefuellt mit
        seiner mittleren Farbe - wie die Seiten der Mauern (`_seitenfarbe`).
        Das abgedunkelte Bild selbst sah als Wand verschmiert aus: jedes
        Muster darin wurde zu Streifen.

        Gemerkt je Bild - zusammen mit dem Bild selbst, damit eine neue
        Flaeche, die zufaellig dieselbe id bekommt, nicht die alte Seite
        erbt. Gibt die Schicht und ihre Lage im Bild zurueck."""
        cache = self.__dict__.setdefault("_seiten_3d", {})
        schluessel = (id(s), hell, dunkel)
        hit = cache.get(schluessel)
        if hit is not None and hit[0] is s:
            return hit[1]
        # GRUND fuer die Kopie: average_color laesst die Flaeche gesperrt
        # zurueck, und das Bild selbst wird gleich danach geblittet.
        q = s.copy()
        maske = pygame.mask.from_surface(q, 60)
        # Nur das Rechteck um den Umriss: die Bilder der Figuren haben viel
        # leeren Rand (Platz zum Drehen), und jede Schicht wird geblittet.
        rand = maske.get_bounding_rects()
        rand = rand[0].unionall(rand[1:]) if rand else pygame.Rect(0, 0, 1, 1)
        # Mittel nur ueber den Umriss: average_color zaehlt die
        # durchsichtigen Pixel mit (auch mit consider_alpha), und eine
        # Figur auf 76 x 76 mit viel Rand wurde so fast schwarz. Gemessen
        # im Rechteck um den Umriss, weil average_color ganze Zahlen
        # liefert - ueber das ganze Bild verschluckte das den Farbton.
        voll = maske.count()
        if voll == 0:
            grund = (0, 0, 0)
        else:
            nur = maske.to_surface(setsurface=q, unsetcolor=(0, 0, 0, 255))
            summe = pygame.transform.average_color(nur, rand)[:3]
            anteil = voll / float(rand.width * rand.height)
            grund = tuple(min(255, c / anteil) for c in summe)
        f = hell * (1.0 if dunkel is None else dunkel / 255.0)
        farbe = tuple(max(0, min(255, int(c * f))) for c in grund) + (255,)
        seite = maske.to_surface(setcolor=farbe, unsetcolor=(0, 0, 0, 0))
        seite = seite.subsurface(rand).copy()
        ergebnis = (seite, rand.topleft)
        if len(cache) > 900:
            cache.clear()
        cache[schluessel] = (s, ergebnis)
        return ergebnis

    def balken_zeichnen(self, ziel, welt, index, ecke, alpha) -> None:
        """Lebensbalken der Gegner - Anzeige, also ueber den Mauern."""
        for w in welt.wesen:
            if (w.ebene == index and w.lebt and w.flug <= 0
                    and getattr(w, "fraktion", "") == "feind"):
                self.gegnerbalken(ziel, w.zeichenpos(alpha) - ecke, w)

    def luft_zeichnen(self, ziel, welt, index, ecke, alpha, dunkel=None) -> None:
        """Was ueber dem Boden fliegt: Geschosse und Raketen, mit Spur.

        Nach den Mauern, und nur, wenn keine Mauer davor steht (`verdeckt`).
        Eine Kugel, die knapp hinter einer Mauer vorbeifliegt, ist nicht zu
        sehen; eine, die vor ihr fliegt, schon.
        """
        breite, hoehe = ziel.get_size()
        for w in welt.wesen:
            if w.ebene != index or not w.lebt or w.hoehe_bild <= 0 or w.flug > 0:
                continue
            wp = w.zeichenpos(alpha)
            p = wp - ecke
            # Ausserhalb des Bildes gar nicht erst abtasten (wie bei den
            # Partikeln, seit 0.34.55); 32 px Rand fuer Spur und Bild.
            if not (-32 <= p.x < breite + 32 and -32 <= p.y < hoehe + 32):
                continue
            if self.verdeckt(welt, index, wp, w.hoehe_bild):
                continue
            if w.spur is not None and w.tempo.length_squared() > 1:
                r = w.tempo.normalize()
                # Die Granate der Panzerkanone zieht eine dicke, lange Spur
                # (seit 0.34.59, `spur_dick`).
                dick = getattr(w, "spur_dick", 1)
                lang = 17 if dick <= 1 else 30
                pygame.draw.line(ziel, (128, 80, 30), p - r * lang, p - r * 5, dick)
                pygame.draw.line(ziel, w.spur, p - r * (6 + 4 * (dick - 1)), p, dick)
            if w.bild is None:
                continue
            s_ = self.bilder.gedreht(w.bild, w.winkel)
            if dunkel is not None:
                s_ = self.dunkel(s_, dunkel)
            ziel.blit(s_, (p.x - s_.get_width() / 2, p.y - s_.get_height() / 2))

    def dash_zeichnen(self, ziel, p, w) -> None:
        """Drei kurze, graue Windlinien ziehen dezent hinter der Figur her."""
        d = pygame.Vector2(getattr(w, "dash_richtung", (1, 0)))
        if d.length_squared() < 0.001:
            return
        d.normalize_ip()
        quer = pygame.Vector2(-d.y, d.x)
        p = pygame.Vector2(p)
        rest = max(0.0, float(getattr(w, "dash_rest", 0.0)))
        dauer = K.DASH["dauer"]
        if rest > 0.0:
            vergangen = dauer - rest
            staerke = 1.0
        else:
            ausklang = K.DASH["bild_ausklang"]
            rest_bild = max(0.0, float(getattr(w, "dash_bild_rest", 0.0)))
            staerke = min(1.0, rest_bild / max(0.01, ausklang))
            vergangen = dauer + ausklang - rest_bild
        if staerke <= 0.0:
            return

        hell = K.DASH["bild_wind_hell"]
        dunkel = K.DASH["bild_wind_dunkel"]
        aufbau = max(0.01, K.DASH["bild_wind_aufbau"])
        for i, (start, abstand, laenge, seite) in enumerate(zip(
                K.DASH["bild_wind_start"], K.DASH["bild_wind_abstand"],
                K.DASH["bild_wind_laenge"], K.DASH["bild_wind_seite"])):
            fort = min(1.0, max(0.0, (vergangen - start) / aufbau))
            if fort <= 0.0:
                continue
            anteil = staerke * fort * (1.0 - i * 0.18)
            farbe = tuple(int(dunkel[c] + (hell[c] - dunkel[c]) * anteil)
                          for c in range(3))
            sichtbar = max(2, int(round(laenge * fort)))
            a = p - d * (abstand - laenge * 0.5) + quer * seite
            b = a - d * sichtbar
            pygame.draw.line(ziel, farbe,
                             (round(a.x), round(a.y)),
                             (round(b.x), round(b.y)), 1)

    def gegnerbalken(self, ziel, p, w) -> None:
        """Wie viel ein Gegner noch hat.

        Gab es bisher nur beim Gast - der Gastgeber sah gar keinen. Das
        fiel nie auf, solange ein Laeufer nach zwei Treffern lag; bei
        einem Boss mit 1400 Leben ist es der Unterschied zwischen
        "gleich ist er soweit" und "schiesse ich hier eigentlich ins
        Leere?".
        """
        max_leben = getattr(w, "max_leben", 0.0) or 0.0
        if max_leben <= 0:
            return
        anteil = max(0.0, min(1.0, w.leben / max_leben))
        if anteil > 0.999:
            return
        boss = getattr(w, "ist_boss", False)
        breite, dick = (34, 3) if boss else (20, 2)
        hoch = int(w.radius) + 11
        x, y = int(p.x) - breite // 2, int(p.y) - hoch
        pygame.draw.rect(ziel, (16, 11, 8), (x, y, breite, dick))
        pygame.draw.rect(ziel, K.C_AMBER if boss else K.C_RED,
                         (x, y, int(breite * anteil), dick))

    def ankuendigung(self, ziel, p, w) -> None:
        """Ein Ring, der sich zuzieht: gleich passiert etwas.

        Dieselbe Sprache wie die Zielerfassung des Raketenwerfers, damit
        man sie nicht zweimal lernen muss. Beim Stampfer hat der Ring die
        Reichweite des Schadens - man sieht also nicht nur, **dass**
        etwas kommt, sondern auch **wohin** es reicht.
        """
        f = getattr(w, "faehigkeit", None) or {}
        gesamt = max(0.01, f.get("vorlauf", 0.5))
        anteil = max(0.0, min(1.0, w.f_vorlauf / gesamt))
        radius = float(f.get("radius", w.radius) or w.radius)
        if f.get("art") == "brut":
            radius = w.radius * 2.2
        pygame.draw.circle(ziel, (78, 30, 22), (int(p.x), int(p.y)),
                           int(radius), 1)
        pygame.draw.circle(ziel, K.C_RED, (int(p.x), int(p.y)),
                           max(2, int(radius * (0.25 + 0.75 * anteil))), 2)

    def _bildpunkt(self, weltpos, kamera, k: float) -> pygame.Vector2:
        """Wo ein Weltpunkt im Bild liegt, wenn er mit k verkleinert wird.

        Dieselbe Rechnung, die auch hinter der Tiefenflaeche steckt: gleiche
        Weltmitte, kleinerer Massstab.
        """
        mitte = kamera.ecke + pygame.Vector2(kamera.breite / 2, kamera.hoehe / 2)
        return pygame.Vector2(
            self.groesse[0] / 2 + (weltpos.x - mitte.x) * k,
            self.groesse[1] / 2 + (weltpos.y - mitte.y) * k)

    def fliegende_zeichnen(self, ziel, welt, kamera, alpha, blick_hoehe) -> None:
        """Wesen im Sturz, nach allen Ebenen und mit eigenem Massstab.

        Ein fallendes Wesen gehoert zu keiner Ebene, es haengt zwischen
        ihnen. Wurde es mit seiner Zielebene gezeichnet, trug es auch deren
        Massstab - beim Absprung also den einer Ebene, die noch weit unter
        ihm lag. Es schrumpfte dadurch schlagartig zusammen und sass
        gleichzeitig um die volle Fallhoehe zu hoch im Bild.

        Hier bekommt es den Massstab seiner eigenen Hoehe. Sinkt die Ansicht
        mit ihm - das tut sie bei der eigenen Figur - bleibt es stehen und
        die Welt waechst unter ihm heran. Genau das soll sich anfuehlen wie
        ein Blick von oben in echte Tiefe.
        """
        p = K.PERSPEKTIVE
        fliegende = [w for w in welt.wesen
                     if w.lebt and w.flug > 0 and w.bild is not None]
        if not fliegende:
            return
        # Das hoechste zuletzt, damit es ueber den tieferen liegt.
        fliegende.sort(key=lambda w: welt.hoehe(w.ebene) + w.flug)
        for w in fliegende:
            self.fliegendes(ziel, welt, kamera, blick_hoehe,
                            w.zeichenpos(alpha), w.winkel, w.ebene, w.flug,
                            w.bild, w.blitz > 0)

    def fliegendes(self, ziel, welt, kamera, blick_hoehe, pos, winkel,
                   ebene: int, flug: float, bild: str,
                   blitzt: bool = False) -> None:
        """Ein einzelnes Ding in der Luft, mit dem Massstab seiner Hoehe.

        Eigene Methode, weil nicht nur eigene Wesen fallen: beim Gast im
        Gefecht kommen fallende Granaten als blosse Zahlen aus dem Netz und
        muessen mit derselben Rechnung ins Bild, sonst haengen sie in der
        Luft, wo die Figur daneben schon faellt.
        """
        p = K.PERSPEKTIVE
        dz = blick_hoehe - (welt.hoehe(ebene) + flug)
        if dz < -p["ausblenden"]:
            return                            # zu weit ueber der Ansicht
        if self.verdeckt(welt, ebene, pos, flug):
            return                            # knapp ueber dem Boden hinter einer Mauer
        k = p["brennweite"] / max(60.0, p["brennweite"] + dz)
        s = self.bilder.gedreht(bild, winkel)
        if abs(k - 1.0) > p["massstab_schwelle"]:
            s = pygame.transform.scale(
                s, (max(1, int(round(s.get_width() * k))),
                    max(1, int(round(s.get_height() * k)))))
        if blitzt:
            s = s.copy()
            s.fill((210, 210, 210), special_flags=pygame.BLEND_RGB_ADD)
        b = self._bildpunkt(pos, kamera, k)
        if bild in K.BOGEN["bilder"]:
            # Im Bogen geworfen (seit 0.34.64): je hoeher, desto weiter oben
            # im Bild - wie ein Wurf, den man von schraeg oben sieht. Der
            # Schatten bleibt am Boden.
            b.y -= flug * K.BOGEN["hoch"] / max(0.2, kamera.zoom)
        ziel.blit(s, (b.x - s.get_width() / 2, b.y - s.get_height() / 2))

    def effekte_zeichnen(self, ziel, welt, index, ecke, boden: bool) -> None:
        """Das Effektsystem (seit 0.34.122, effekte.py): `boden` die Schicht
        vor den Figuren (Druckringe), sonst alles ueber den Mauern."""
        liste = getattr(welt, "effekte", None)
        if liste:
            from . import effekte
            effekte.zeichnen(ziel, liste, index, ecke, boden)

    def partikel_zeichnen(self, ziel, welt, index, ecke, alpha) -> None:
        h = K.HOEHEN
        breite, hoehe = ziel.get_size()
        for p in welt.partikel:
            if p.ebene != index or p.art == "bodenstaub":
                continue
            wp = p.zeichenpos(alpha)
            q = wp - ecke
            # Erst ausserhalb des Bildes aussortieren: `verdeckt` tastet
            # jeden Pixel bis zur Mauerhoehe ab und war gemessen der
            # teuerste Teil des Bildes, auch fuer Funken und Huelsen weit
            # ausserhalb (seit 0.34.55).
            if not (-16 <= q.x < breite + 16 and -16 <= q.y < hoehe + 16):
                continue
            if self.verdeckt(welt, index, wp, h.get(p.art, h["partikel"])):
                continue
            f = max(0.0, p.leben / p.dauer)
            if p.art == "huelse":
                s = self.bilder.gedreht("huelse", p.winkel)
                ziel.blit(s, (q.x - s.get_width() / 2, q.y - s.get_height() / 2))
                continue
            g = max(1, int(p.groesse * (0.4 + 0.6 * f)))
            farbe = p.farbe
            if p.art == "funke":
                farbe = (255, min(255, farbe[1] + 40), 160) if f > 0.55 else farbe
            pygame.draw.rect(ziel, farbe, (int(q.x), int(q.y), g, g))

    # ---- Der Flammenstrom (seit 0.34.95, K.FLAMME) -----------------------
    # Hitze je Zelle als Rotwert: so viel Rot ist eine Hitze von 1.
    FLAMMEN_SKALA = 80.0

    def flammen_zeichnen(self, ziel, welt, index, ecke, alpha=1.0) -> None:
        """Wie im Waffenpaket: die Hitze aller Flecken wird je Zelle
        (2 x 2 Pixel) zusammengezaehlt, ein wenig verrauscht und dann
        nach Stufen gefaerbt. GRUND fuer den Umweg ueber Masken: Zelle fuer
        Zelle in Python waeren das bei einem Flammenwerfer gut hunderttausend
        Rechnungen je Bild; so addiert SDL vorbereitete Flecken (BLEND_ADD)
        und die Masken schneiden die Stufen heraus."""
        flammen = welt.flammen
        if not flammen:
            return
        f = K.FLAMME
        z = f["zelle"]
        zeit = welt.flammen_zeit + (alpha - 1.0) * K.FIXED_DT
        breite, hoehe = ziel.get_size()
        ex, ey = ecke.x, ecke.y
        punkte = []
        x0 = y0 = 1e9
        x1 = y1 = -1e9
        jetzt = welt.flamme_jetzt
        for b in flammen:
            if b[9] != index:
                continue
            x, y, r, glut = jetzt(b, zeit)
            if glut <= 0.0:
                continue
            x -= ex
            y -= ey
            if x + r < 0 or y + r < 0 or x - r > breite or y - r > hoehe:
                continue
            punkte.append((x, y, r, glut))
            x0 = min(x0, x - r); y0 = min(y0, y - r)
            x1 = max(x1, x + r); y1 = max(y1, y + r)
        if not punkte:
            return
        gx0, gy0 = int(math.floor(x0 / z)) - 1, int(math.floor(y0 / z)) - 1
        w = int(math.ceil(x1 / z)) + 2 - gx0
        h = int(math.ceil(y1 / z)) + 2 - gy0
        hitze = pygame.Surface((w, h))
        hitze.fill((0, 0, 0))
        add = pygame.BLEND_RGB_ADD
        for x, y, r, glut in punkte:
            fleck, mitte = self._flammen_fleck(r / z, glut)
            hitze.blit(fleck, (int(round(x / z - gx0)) - mitte, int(round(y / z - gy0)) - mitte),
                       special_flags=add)
        # Zuengeln: in jeder Zelle etwas Rauschen, 24-mal je Sekunde neu.
        rausch = self._flammen_rauschen()
        rw, rh = rausch.get_size()
        k = int(zeit * f["rausch_takt"])
        ox, oy = (k * 37) % rw, (k * 53) % rh
        for ty in range(-oy, h, rh):
            for tx in range(-ox, w, rw):
                hitze.blit(rausch, (tx, ty), special_flags=add)
        bild = pygame.Surface((w, h), pygame.SRCALPHA)
        bild.fill((0, 0, 0, 0))
        versatz = f["rauschen"] / 2.0 * self.FLAMMEN_SKALA
        for stufe, farbe in reversed(f["stufen"]):
            ab = int(stufe * self.FLAMMEN_SKALA + versatz) + 1
            if ab > 255:
                continue
            maske = pygame.mask.from_threshold(hitze, (255, 0, 0, 255), (256 - ab, 1, 1, 255))
            maske.to_surface(bild, setcolor=farbe, unsetcolor=None)
        ziel.blit(pygame.transform.scale(bild, (w * z, h * z)), (gx0 * z, gy0 * z))

    def _flammen_fleck(self, r: float, glut: float):
        """Ein Fleck als Rotwerte: (1 - d^2/r^2) * glut^2 * gewicht, in
        Zellen. Gemerkt nach Groesse und Glut (gerundet)."""
        cache = self.__dict__.setdefault("_flammen_flecken", {})
        rq = max(1, int(round(r * 4)))
        gq = max(0, min(20, int(round(glut * 20))))
        hit = cache.get((rq, gq))
        if hit is None:
            rr = rq / 4.0
            g = gq / 20.0
            mitte = int(math.ceil(rr))
            seite = 2 * mitte + 1
            s = pygame.Surface((seite, seite))
            s.fill((0, 0, 0))
            wert = g * g * K.FLAMME["gewicht"] * self.FLAMMEN_SKALA
            for j in range(seite):
                for i in range(seite):
                    q = 1.0 - ((i - mitte) ** 2 + (j - mitte) ** 2) / (rr * rr)
                    if q > 0.0:
                        v = int(round(q * wert))
                        if v > 0:
                            s.set_at((i, j), (min(255, v), 0, 0))
            hit = (s, mitte)
            cache[(rq, gq)] = hit
        return hit

    def _flammen_rauschen(self) -> pygame.Surface:
        s = self.__dict__.get("_flammen_rausch")
        if s is None:
            zufall = random.Random(95)
            hoch = int(K.FLAMME["rauschen"] * self.FLAMMEN_SKALA)
            s = pygame.Surface((61, 47))
            for y in range(s.get_height()):
                for x in range(s.get_width()):
                    s.set_at((x, y), (zufall.randint(0, hoch), 0, 0))
            self._flammen_rausch = s
        return s

    def muendungsfeuer(self, ziel, welt, ecke, index) -> None:
        for m in welt.muendungen:
            pos, winkel, eb, rest = m[0], m[1], m[2], m[3]
            if eb != index or rest <= 0:
                continue
            # Seit 0.34.59 mit Groesse: die Panzerkanone blitzt 2,4-mal so gross.
            gross = m[4] if len(m) > 4 else 1.0
            wp = pos + pygame.Vector2(K.MUENDUNGSFEUER["versatz"] * gross, 0).rotate(winkel)
            if self.verdeckt(welt, index, wp, K.HOEHEN["lauf"]):
                continue
            s = self.bilder.gedreht("muendung", winkel)
            if gross != 1.0:
                s = self._gross_muendung(winkel, gross)
            p = wp - ecke
            ziel.blit(s, (p.x - s.get_width() / 2, p.y - s.get_height() / 2),
                      special_flags=pygame.BLEND_RGB_ADD)

    # ---- Panzer und Panzerwagen (seit 0.34.59) ---------------------------
    def _gross_muendung(self, winkel: float, gross: float) -> pygame.Surface:
        cache = self.__dict__.setdefault("_muendung_gross", {})
        k = int(round(winkel / 3.0)) * 3 % 360
        schluessel = (k, round(gross, 2))
        hit = cache.get(schluessel)
        if hit is None:
            roh = self.bilder.bild("muendung")
            g = pygame.transform.smoothscale(
                roh, (max(1, round(roh.get_width() * gross)),
                      max(1, round(roh.get_height() * gross))))
            hit = pygame.transform.rotate(g, -k)
            if len(cache) > 240:
                cache.clear()
            cache[schluessel] = hit
        return hit

    def bodenstaub_zeichnen(self, ziel, welt, index, ecke, alpha) -> None:
        """Staub, der am Boden bleibt und unter den Fahrzeugen liegt: die
        Druckwelle der Kanone vor der Muendung (Welt.schussknall). Im Paket
        gemeldet: er kam vorher aus der Mitte der Wanne."""
        breite, hoehe = ziel.get_size()
        for p in welt.partikel:
            if p.art != "bodenstaub" or p.ebene != index:
                continue
            q = p.zeichenpos(alpha) - ecke
            if not (-16 <= q.x < breite + 16 and -16 <= q.y < hoehe + 16):
                continue
            f = max(0.0, p.leben / p.dauer)
            g = max(1, int(p.groesse * (0.4 + 0.6 * f)))
            pygame.draw.rect(ziel, p.farbe, (int(q.x), int(q.y), g, g))

    def aufbauten_zeichnen(self, ziel, welt, index, ecke, alpha, dunkel=None) -> None:
        """Tuerme und MG-Ringe - nach allen Figuren: Rohr und MG liegen
        ueber dem, der davor steht (die dritte Ebene aus dem Paket)."""
        for w in welt.wesen:
            if (w.ebene == index and w.lebt and getattr(w, "zeichnet_selbst", False)):
                w.zeichnen_oben(self, ziel, w.zeichenpos(alpha) - ecke, dunkel)

    def flugleichen_zeichnen(self, ziel, welt, index, ecke, alpha, dunkel=None) -> None:
        """Wer nach dem Rammen noch fliegt (entities.Flugleiche)."""
        for f in welt.flugleichen:
            if f.ebene != index:
                continue
            s = self.bilder.gedreht(f.bild, f.winkel)
            if dunkel is not None:
                s = self.dunkel(s, dunkel)
            p = f.zeichenpos(alpha) - ecke
            ziel.blit(s, (p.x - s.get_width() / 2, p.y - s.get_height() / 2))

    def lichtblitze_zeichnen(self, ziel, welt, index, ecke) -> None:
        """Der kurze Blitz einer Explosion (seit 0.34.64): zwei Kreise,
        additiv, die in K.LICHTBLITZ["dauer"] verloeschen."""
        lb = K.LICHTBLITZ
        for pos, ebene, r, rest, dauer in welt.lichtblitze:
            if ebene != index:
                continue
            f = max(0.0, rest / dauer)
            n = int(r) + 2
            fl = pygame.Surface((n * 2, n * 2))
            fl.fill((0, 0, 0))
            aussen = tuple(int(c * f * 0.55) for c in lb["farbe"])
            innen = tuple(int(c * f) for c in lb["kern"])
            pygame.draw.circle(fl, aussen, (n, n), max(1, int(r * (0.7 + 0.3 * f))))
            pygame.draw.circle(fl, innen, (n, n), max(1, int(r * 0.4 * f)))
            m = pos - ecke
            ziel.blit(fl, (m.x - n, m.y - n), special_flags=pygame.BLEND_RGB_ADD)

    def feuerbaelle_zeichnen(self, ziel, welt, index, ecke, teil: str) -> None:
        """Der Einschlag der Panzerkanone (entities.Feuerball). `teil`
        "glut": die Glutballen, additiv. "rauch": der dunkle Rauch danach,
        ueber allem anderen am Boden. Kreise je Ballen und Bild - es sind
        wenige, und die Flaechen sind klein."""
        f = K.FEUERBALL
        for fb in welt.feuerbaelle:
            if fb.ebene != index:
                continue
            mitte = fb.pos - ecke
            if teil == "glut":
                self._druckwelle(ziel, fb, mitte)
                for versatz, radius, start, dauer in fb.ballen:
                    t = fb.alter - start
                    if t < 0.0 or t > dauer:
                        continue
                    anteil = t / dauer
                    hell = (1.0 - anteil) ** 1.2
                    # Der Pilz (seit 0.34.96): jeder Ballen steigt, die
                    # inneren hoeher als die aeusseren.
                    hoch = f["steigen"] * (anteil ** 0.7) * (1.0 - min(1.0, versatz.length()
                                                                       / (f["ballen_streuung"] + 1.0)) * 0.5)
                    for k, farbe in f["glut"]:
                        rr = radius * k * (0.55 + 0.9 * min(1.0, anteil * 3.0)) \
                            * (1.0 - 0.5 * anteil)
                        if rr < 0.6:
                            continue
                        fb_farbe = tuple(int(c * hell) for c in farbe)
                        n = int(rr) + 1
                        fl = pygame.Surface((n * 2 + 1, n * 2 + 1))
                        fl.fill((0, 0, 0))
                        pygame.draw.circle(fl, fb_farbe, (n, n), rr)
                        p = mitte + versatz - pygame.Vector2(0, hoch)
                        ziel.blit(fl, (round(p.x - n), round(p.y - n)),
                                  special_flags=pygame.BLEND_RGB_ADD)
                self._brocken(ziel, fb, mitte)
                continue
            for versatz, r0, r1, start, dauer, tempo, farbe in fb.wolken:
                t = fb.alter - start
                if t < 0.0 or t > dauer:
                    continue
                anteil = t / dauer
                rr = r0 + (r1 - r0) * math.sqrt(anteil)
                deck = int(f["wolke_deckkraft"] * (1.0 - anteil) ** 1.5)
                if deck <= 0:
                    continue
                n = int(rr) + 1
                fl = pygame.Surface((n * 2 + 1, n * 2 + 1), pygame.SRCALPHA)
                pygame.draw.circle(fl, tuple(farbe) + (deck,), (n, n), rr)
                p = mitte + versatz + tempo * t - pygame.Vector2(0, f["rauch_steigen"] * t)
                ziel.blit(fl, (round(p.x - n), round(p.y - n)))

    def _druckwelle(self, ziel, fb, mitte) -> None:
        """Eine flache Ellipse am Boden, die schnell auslaeuft (seit 0.34.96)."""
        f = K.FEUERBALL
        dauer, radius, flach = f["druckwelle"]
        if fb.alter > dauer:
            return
        a = fb.alter / dauer
        rr = radius * (a ** 0.6)
        if rr < 2.0:
            return
        hell = (1.0 - a) ** 1.5
        farbe = tuple(int(c * hell) for c in f["druck_farbe"])
        rect = pygame.Rect(0, 0, int(rr * 2), max(2, int(rr * 2 * flach)))
        rect.center = (round(mitte.x), round(mitte.y))
        fl = pygame.Surface(rect.size)
        fl.fill((0, 0, 0))
        pygame.draw.ellipse(fl, farbe, fl.get_rect(), max(1, int(3 * (1.0 - a)) + 1))
        ziel.blit(fl, rect.topleft, special_flags=pygame.BLEND_RGB_ADD)

    def _brocken(self, ziel, fb, mitte) -> None:
        """Brocken im Bogen: Hoehe aus Wurf und Schwere, der Schatten bleibt
        am Boden und zeigt, wie hoch sie sind (seit 0.34.96)."""
        g = K.FEUERBALL["schwere"]
        t = fb.alter
        for seite, hoch, gross, farbe in fb.brocken:
            flug = 2.0 * hoch / g
            if t > flug:
                continue
            z = hoch * t - 0.5 * g * t * t
            boden = mitte + seite * t
            pygame.draw.rect(ziel, (20, 15, 11), (round(boden.x), round(boden.y), gross, 1))
            pygame.draw.rect(ziel, farbe, (round(boden.x), round(boden.y - z), gross, gross))

    def krater(self, radius: float, saat: int) -> pygame.Surface:
        """Ein Krater als Bodendekal: kein Kreis, sondern ein Haufen
        versetzter Kleckse, Strahlen unterschiedlicher Laenge und Brocken
        (Paket, krater()). Je Saat einmal gebaut - acht Formen reichen."""
        cache = self.__dict__.setdefault("_krater", {})
        schluessel = (round(radius), int(saat) % 8)
        hit = cache.get(schluessel)
        if hit is not None:
            return hit
        r = float(radius)
        rnd = random.Random(schluessel[1] * 977 + schluessel[0])
        farbe = (18, 13, 9)
        g = int(r * 3.2)
        s = pygame.Surface((g * 2, g * 2), pygame.SRCALPHA)
        c = pygame.Vector2(g, g)
        for _ in range(int(10 + r)):
            d = pygame.Vector2(rnd.uniform(0, r * 0.55), 0).rotate(rnd.uniform(0, 360))
            pygame.draw.circle(s, farbe + (rnd.randint(30, 60),), c + d,
                               rnd.uniform(r * 0.18, r * 0.5))
        for _ in range(5):                       # dunkler, unregelmaessiger Kern
            d = pygame.Vector2(rnd.uniform(0, r * 0.25), 0).rotate(rnd.uniform(0, 360))
            pygame.draw.circle(s, farbe + (70,), c + d, rnd.uniform(r * 0.15, r * 0.3))
        for _ in range(rnd.randint(9, 14)):      # Strahlen
            a = rnd.uniform(0, 360)
            p0 = c + pygame.Vector2(r * 0.3, 0).rotate(a)
            p1 = c + pygame.Vector2(rnd.uniform(r * 0.7, r * 1.9), 0).rotate(a + rnd.uniform(-6, 6))
            pygame.draw.line(s, farbe + (rnd.randint(25, 50),), p0, p1,
                             max(1, round(rnd.uniform(1, 2.6))))
        for _ in range(int(r * 1.5)):            # Brocken
            d = pygame.Vector2(rnd.uniform(r * 0.4, r * 2.2), 0).rotate(rnd.uniform(0, 360))
            pygame.draw.rect(s, farbe + (rnd.randint(50, 110),),
                             (c.x + d.x, c.y + d.y, rnd.randint(1, 2), rnd.randint(1, 2)))
        cache[schluessel] = s
        return s

    def _tiefenflaeche(self, k: float, groesse=None) -> pygame.Surface:
        """Hilfsflaeche fuer eine tiefer liegende Ebene.

        Sie zeigt einen groesseren Weltausschnitt und wird danach auf die
        Bildgroesse verkleinert. Genau das laesst die untere Ebene weiter weg
        wirken: gleiche Weltmitte, kleinerer Massstab.
        """
        if groesse is None:
            groesse = (int(self.groesse[0] / k) + 2, int(self.groesse[1] / k) + 2)
        schluessel = groesse
        hit = self._tiefen.get(schluessel)
        if hit is None:
            hit = pygame.Surface(groesse, pygame.SRCALPHA)
            if len(self._tiefen) > 64:
                self._tiefen.clear()
            self._tiefen[schluessel] = hit
        return hit

    def obermaske(self, welt, index: int) -> bytearray:
        """Welche Kacheln der Ebene `index` ueber spielbarem Boden liegen.

        1 heisst: darunter kann man stehen, also verdeckt diese Kachel
        etwas, das man sehen will. 0 heisst: darunter ist Fels, die
        Kachel gehoert zu einem Plateau und bleibt immer sichtbar - das
        Hochland im STAUBTAL steht vollstaendig auf Wand und wird deshalb
        nie ausgeblendet, das Zwischengeschoss der Arena fast ganz.

        Wand ueber Wand ist der Sonderfall. Die Aussenmauer der oberen
        Etage steht auf der Aussenmauer der unteren; bliebe sie stehen,
        wuerde ueber der Karte ein vergroesserter Rahmen ohne Boden
        schweben. Eine feste Kachel geht darum mit, wenn sie an
        ausgeblendeten Boden grenzt und an keinen sichtbaren.

        Haengt an der Welt: die Kacheln darunter aendern sich waehrend
        einer Runde nicht, eine neue Karte bringt eine neue Welt mit.
        """
        cache = welt.__dict__.setdefault("_obermasken", {})
        hit = cache.get(index)
        if hit is not None:
            return hit
        oben, unten = welt.ebene(index), welt.ebene(index - 1)
        b, h = oben.breite, oben.hoehe
        maske = bytearray(b * h)
        if (unten.breite, unten.hoehe) != (b, h):
            cache[index] = maske      # passt nicht aufeinander: alles zeigen
            return maske
        fest = {k: d["fest"] for k, d in K.KACHELN.items()}
        tragend = (K.AUFZUG_HOCH, K.AUFZUG_RUNTER)
        for i, k in enumerate(oben.kacheln):
            if k != K.LEER and not fest[unten.kacheln[i]] \
                    and unten.kacheln[i] not in tragend:
                maske[i] = 1
        # Kleine Stuecke sind kein Plateau. Auf der Testkarte liegen Stege
        # der oberen Etage ueber einzelnen Mauern und Kisten; jede solche
        # Kachel blieb stehen, waehrend der Steg rundherum ausblendete -
        # mit Klippen bis hinunter eine schwebende Saeule, ein Streifen
        # quer durchs Bild (gemeldet nach 0.34.18). Gezaehlt wird nur der
        # begehbare Boden, und nur er geht mit; die Mauern daneben nimmt
        # der Durchgang danach mit, wenn kein sichtbarer Boden mehr bleibt.
        gesehen = bytearray(b * h)
        for start in range(b * h):
            if gesehen[start] or maske[start] or oben.kacheln[start] == K.LEER:
                continue
            stueck, offen = [start], [start]
            gesehen[start] = 1
            while offen:
                i = offen.pop()
                x, y = i % b, i // b
                for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                    j = ny * b + nx
                    if 0 <= nx < b and 0 <= ny < h and not gesehen[j] \
                            and not maske[j] and oben.kacheln[j] != K.LEER:
                        gesehen[j] = 1
                        stueck.append(j)
                        offen.append(j)
            begehbar = [i for i in stueck if not fest[oben.kacheln[i]]]
            if len(begehbar) < K.PERSPEKTIVE["plateau_flaeche"]:
                for i in begehbar:
                    maske[i] = 1
        # Zweiter Durchgang fuer Wand ueber Wand, gegen die erste Maske.
        erst = bytes(maske)
        for ty in range(h):
            for tx in range(b):
                i = ty * b + tx
                k = oben.kacheln[i]
                if erst[i] or k == K.LEER or not fest[k]:
                    continue
                weg = bleibt = False
                for ny in range(max(0, ty - 1), min(h, ty + 2)):
                    for nx in range(max(0, tx - 1), min(b, tx + 2)):
                        j = ny * b + nx
                        nk = oben.kacheln[j]
                        if nk == K.LEER or fest[nk]:
                            continue
                        if erst[j]:
                            weg = True
                        else:
                            bleibt = True
                if weg and not bleibt:
                    maske[i] = 1
        cache[index] = maske
        return maske

    def ebenen_vorbereiten(self, welt) -> None:
        """Masken und Klippen jeder Ebene vorab rechnen, fuer jede
        Blickhoehe und beide Einstellungen der oberen Etage (seit 0.34.58).
        Sie haengen nur an den Kacheln, und die aendern sich im Spiel nicht;
        beim ersten Blick auf eine Ebene gerechnet, hielten sie das Bild
        bis zu 0,9 s an."""
        n = len(welt.ebenen)
        for idx in range(1, n):
            self.obermaske(welt, idx)
            for oben_aus in (False, True):
                self.klippen(welt, idx, oben_aus)
        for blick in range(n):
            for idx in range(blick + 2, n):
                self.turm_auslassen(welt, idx, blick)

    def turm_auslassen(self, welt, index: int, blick: int) -> bytearray:
        """Was von Ebene `index` weg muss, wenn man sie von `blick` aus
        sieht und sie mehr als eine Etage hoeher liegt (seit 0.34.7).

        Zu sehen ist dann nur, was auf einem durchgehenden Felsblock steht:
        jede Etage dazwischen ist an dieser Stelle fest (oder die Kabine
        eines Aufzugs, die im Fels sitzt). So steht die hohe Tafel vom Tal
        aus als ein Block da, zwei Stufen hoch, mit ihrer Oberflaeche - und
        es liegt trotzdem kein Stapel aus allen Stockwerken ueber dem Bild.
        1 heisst: auslassen. Gemerkt an der Welt, die Karte aendert sich
        nicht.
        """
        cache = welt.__dict__.setdefault("_turmmasken", {})
        schluessel = (index, blick)
        hit = cache.get(schluessel)
        if hit is not None:
            return hit
        oben = welt.ebene(index)
        dazwischen = [welt.ebene(j) for j in range(blick + 1, index)]
        b, h = oben.breite, oben.hoehe
        maske = bytearray(b'\x01') * (b * h)
        if all((e.breite, e.hoehe) == (b, h) for e in dazwischen):
            fest = {k: d["fest"] or d.get("treppe") is not None
                    for k, d in K.KACHELN.items()}
            for i, k in enumerate(oben.kacheln):
                if k != K.LEER and all(e.kacheln[i] != K.LEER and fest[e.kacheln[i]]
                                       for e in dazwischen):
                    maske[i] = 0
            # Ein Turm ist eine Tafel: oben muss man stehen koennen. Eine
            # Mauer auf einer Mauer auf einer Mauer (der Aussenrand der
            # Testkarte) waere sonst ein Rahmen, der ueber dem Bild
            # schwebt - genau das, was die Obermaske verhindert. Darum
            # bleiben nur Stuecke mit mindestens K.PERSPEKTIVE["turm_flaeche"]
            # begehbaren Kacheln.
            gesehen = bytearray(b * h)
            for start in range(b * h):
                if maske[start] or gesehen[start]:
                    continue
                stueck, offen = [start], [start]
                gesehen[start] = 1
                while offen:
                    i = offen.pop()
                    x, y = i % b, i // b
                    for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                        j = ny * b + nx
                        if 0 <= nx < b and 0 <= ny < h and not maske[j] and not gesehen[j]:
                            gesehen[j] = 1
                            stueck.append(j)
                            offen.append(j)
                begehbar = sum(1 for i in stueck if not K.KACHELN[oben.kacheln[i]]["fest"])
                if begehbar < K.PERSPEKTIVE["turm_flaeche"]:
                    for i in stueck:
                        maske[i] = 1
        # Grobe Uebersicht in Stuecken von 16 x 16 Kacheln: liegt ueberhaupt
        # ein Turm im Bild? Meistens nicht, und dann kostet er nichts.
        stuecke = set()
        for i, weg in enumerate(maske):
            if not weg:
                stuecke.add(((i % b) // 16, (i // b) // 16))
        cache[schluessel] = maske
        cache[("stuecke",) + schluessel] = stuecke
        return maske

    def _turm_im_bild(self, welt, index: int, blick: int, ecke, k: float) -> bool:
        self.turm_auslassen(welt, index, blick)
        stuecke = welt.__dict__["_turmmasken"][("stuecke", index, blick)]
        if not stuecke:
            return False
        s = 16 * K.TILE
        w = self.groesse[0] / k + 2
        h = self.groesse[1] / k + 2
        for cy in range(int(ecke.y // s), int((ecke.y + h) // s) + 1):
            for cx in range(int(ecke.x // s), int((ecke.x + w) // s) + 1):
                if (cx, cy) in stuecke:
                    return True
        return False

    def _ausstanzen(self, flaeche, welt, index: int, ecke,
                    farbe=(0, 0, 0, 0), modus: int = 0, maske=None) -> None:
        """Loescht aus der fertigen Ebene, was ueber Spielflaeche liegt.

        Mit `farbe` und `modus` = BLEND_RGBA_MULT wird es nicht geloescht,
        sondern nur durchsichtiger: so blendet die Etage darueber dort aus,
        wo sie ueber Spielflaeche liegt, und bleibt ueber Fels deckend
        (siehe `klippen`).

        Nach dem Zeichnen und nicht davor: auch wer dort oben steht,
        verschwindet mit - eine Figur ohne Boden unter sich waere
        verwirrender als keine. Was herunterfaellt, zeichnet
        `fliegende_zeichnen` gesondert und bleibt deshalb sichtbar.
        Zeilenweise zusammengefasst, damit es ein paar Dutzend Fuellungen
        je Bild sind und nicht einige hundert.

        `maske`: statt der Obermaske eine andere (1 = weg), etwa die eines
        Turms (`turm_auslassen`).
        """
        if maske is None:
            maske = self.obermaske(welt, index)
        e = welt.ebene(index)
        zw, zh = flaeche.get_size()
        t0x = max(0, int(ecke.x // K.TILE))
        t0y = max(0, int(ecke.y // K.TILE))
        t1x = min(e.breite - 1, int((ecke.x + zw) // K.TILE))
        t1y = min(e.hoehe - 1, int((ecke.y + zh) // K.TILE))
        for ty in range(t0y, t1y + 1):
            zeile = ty * e.breite
            sy = ty * K.TILE - ecke.y
            tx = t0x
            while tx <= t1x:
                if not maske[zeile + tx]:
                    tx += 1
                    continue
                anfang = tx
                while tx <= t1x and maske[zeile + tx]:
                    tx += 1
                flaeche.fill(farbe, (anfang * K.TILE - ecke.x, sy,
                                     (tx - anfang) * K.TILE, K.TILE), modus)

    # ---- Klippen: die Felswand zwischen Plateau und Boden -------------
    #
    # Ein Plateau ist auf der oberen Ebene ein Stueck Boden, das auf Fels
    # der unteren steht (obermaske 0). Gezeichnet wird die obere Ebene
    # vergroessert - sie liegt naeher am Auge. Ohne Wand dazwischen hing
    # ihr Deckel deshalb versetzt und blass ueber dem Felsblock, und
    # zwischen beiden sah man Boden wie Luft (gemeldet nach 0.31). Hier
    # kommt die Wand: an jeder Kante des Plateaus ein Viereck vom Rand
    # des Deckels hinunter zum Rand des Sockels, beide mit genau der
    # Abbildung ihrer Ebene gerechnet. Was dem Auge zugewandt ist, ist zu
    # sehen; die abgewandten Waende liegen unter dem Deckel und fallen weg.

    def klippen(self, welt, index: int, oben_aus: bool) -> list:
        """Die Kanten der Plateaus von Ebene `index`, in Welt-Pixeln.

        Je Eintrag (ax, ay, bx, by, nx, ny): eine Strecke am Rand des
        Plateaus und die Richtung, in die die Wand schaut. Zusammenhaengende
        Kanten sind zu einer Strecke zusammengefasst - eine Seite des
        grossen Plateaus ist eine Wand und nicht dreissig.

        Eine Wand steht, wo ein Plateaufeld an ein Feld grenzt, auf dem
        oben nichts gezeichnet wird: ein Loch, oder - mit `oben_aus` -
        ein ausgeblendetes Stueck Etage. Am Kartenrand nicht.
        """
        cache = welt.__dict__.setdefault("_klippen", {})
        schluessel = (index, bool(oben_aus))
        hit = cache.get(schluessel)
        if hit is not None:
            return hit
        raus = []
        if index <= 0 or index >= len(welt.ebenen):
            cache[schluessel] = raus
            return raus
        maske = self.obermaske(welt, index)
        oben = welt.ebene(index)
        b, h, T = oben.breite, oben.hoehe, K.TILE
        if (welt.ebene(index - 1).breite, welt.ebene(index - 1).hoehe) != (b, h):
            cache[schluessel] = raus
            return raus

        def plateau(tx, ty):
            i = ty * b + tx
            return oben.kacheln[i] != K.LEER and not maske[i]

        def offen(tx, ty):
            if not (0 <= tx < b and 0 <= ty < h):
                return False
            i = ty * b + tx
            return oben.kacheln[i] == K.LEER or (oben_aus and maske[i])

        # Waagerechte Kanten (Wand nach Norden oder Sueden), zeilenweise.
        for ty in range(h):
            for dy in (-1, 1):
                tx = 0
                while tx < b:
                    if not (plateau(tx, ty) and offen(tx, ty + dy)):
                        tx += 1
                        continue
                    anfang = tx
                    while tx < b and plateau(tx, ty) and offen(tx, ty + dy):
                        tx += 1
                    y = (ty + (1 if dy > 0 else 0)) * T
                    raus.append((anfang * T, y, tx * T, y, 0, dy))
        # Senkrechte Kanten (Wand nach Westen oder Osten), spaltenweise.
        for tx in range(b):
            for dx in (-1, 1):
                ty = 0
                while ty < h:
                    if not (plateau(tx, ty) and offen(tx + dx, ty)):
                        ty += 1
                        continue
                    anfang = ty
                    while ty < h and plateau(tx, ty) and offen(tx + dx, ty):
                        ty += 1
                    x = (tx + (1 if dx > 0 else 0)) * T
                    raus.append((x, anfang * T, x, ty * T, dx, 0))
        cache[schluessel] = raus
        return raus

    def _abbildung(self, kamera, k: float, dz: float):
        """Wie eine Ebene ins Bild kommt: Bildpunkt = (Weltpunkt - ecke) * s.

        Genau die Rechnung von `welt_zeichnen`: die angeschaute Ebene ohne
        Massstab an `kamera.ecke`, jede andere auf ihrer Tiefenflaeche, die
        danach auf die Bildgroesse gebracht wird. Die Flaeche ist eine
        ganze Zahl Pixel gross, ihr Massstab darum nicht ganz k - wer mit
        k rechnete, laege mit der Wand ein paar Pixel neben der Ebene.
        """
        if abs(dz) < 1.0:
            return kamera.ecke, 1.0, 1.0
        return self._tiefen_plan(kamera, k)[4]

    def _tiefen_plan(self, kamera, k: float):
        """Wie eine andere Ebene gezeichnet und aufs Bild gebracht wird:
        (Ecke der Flaeche, Groesse der Flaeche, Groesse nach dem Skalieren,
        Versatz beim Auflegen, Abbildung).

        Seit 0.34.77: das Abtastraster haengt an der Welt, nicht am Bild.
        Vorher lag die Ecke der Flaeche jedes Bild woanders, und beim
        Skalieren fiel jedes Mal ein anderes Pixelmuster aus der Textur -
        beim langsamen Umschauen veraenderte sich Gestruepp, Sand und Fels
        auf der Etage darueber oder darunter sichtbar (gemeldet). Jetzt
        rastet die Ecke auf ein Vielfaches von `q` ein, nach dem Raster und
        Bild wieder zusammenpassen; den Rest gleicht ein ganzer Pixel Versatz
        beim Auflegen aus. Die Flaeche ist dafuer um `q` groesser, und ihre
        Breite darf um ein paar Pixel von gw/k abweichen, damit `q` klein
        bleibt (TIEFENRASTER)."""
        gw, gh = self.groesse
        w, qx = _raster_waehlen(gw, int(gw / k) + 2)
        h, qy = _raster_waehlen(gh, int(gh / k) + 2)
        mitte = kamera.ecke + pygame.Vector2(kamera.breite / 2, kamera.hoehe / 2)
        ex, ey = round(mitte.x - w / 2), round(mitte.y - h / 2)
        sx, sy = gw / w, gh / h
        if qx is None or qy is None:
            ecke = pygame.Vector2(ex, ey)
            return ecke, (w, h), (gw, gh), (0, 0), (ecke, sx, sy)
        ex0, ey0 = (ex // qx) * qx, (ey // qy) * qy
        ox, oy = round((ex - ex0) * sx), round((ey - ey0) * sy)
        wirkt = pygame.Vector2(ex0 + ox / sx, ey0 + oy / sy)
        return (pygame.Vector2(ex0, ey0), (w + qx, h + qy),
                (gw + round(qx * sx), gh + round(qy * sy)), (ox, oy), (wirkt, sx, sy))

    def _klippenfarbe(self, welt):
        """Die Farbe des Felses: die Klippen- oder Wandkachel des
        Kartensatzes, gemittelt."""
        satz = getattr(welt, "satz", "")
        hit = self._klippen_farbe.get(satz)
        if hit is None:
            s = self.SAETZE.get(satz, {})
            name = s.get("klippe", s.get("wand", "wand"))
            hit = tuple(pygame.transform.average_color(self.bilder.bild(name))[:3])
            self._klippen_farbe[satz] = hit
        return hit

    def klippen_zeichnen(self, ziel, welt, index: int, unten, oben,
                         oben_aus: bool, dunkel: float = 1.0) -> int:
        """Die Waende zwischen Ebene `index` und der darunter. Gibt zurueck,
        wie viele gezeichnet wurden (fuer die Tests).

        `unten` und `oben` sind die Abbildungen beider Ebenen (`_abbildung`).
        """
        kanten = self.klippen(welt, index, oben_aus)
        if not kanten:
            return 0
        ue, usx, usy = unten
        oe, osx, osy = oben
        gw, gh = self.groesse
        grund = self._klippenfarbe(welt)
        # Licht von oben links, wie die Schlagschatten der Waende: die Wand
        # nach Sueden ist die hellste, die nach Norden die dunkelste.
        licht = {(0, 1): 0.82, (1, 0): 0.66, (-1, 0): 0.74, (0, -1): 0.56}
        schichten = K.KLIPPEN["schichten"]
        gezeichnet = 0
        je_richtung = {}
        for (ax, ay, bx, by, nx, ny) in self._klippen_im_bild(kanten, unten, oben, gw, gh):
            pa = ((ax - oe.x) * osx, (ay - oe.y) * osy)
            pb = ((bx - oe.x) * osx, (by - oe.y) * osy)
            ua = ((ax - ue.x) * usx, (ay - ue.y) * usy)
            ub = ((bx - ue.x) * usx, (by - ue.y) * usy)
            # Dem Auge zugewandt? Dann liegt der Sockel weiter in
            # Blickrichtung der Wand als der Deckelrand. Sonst steckt die
            # Wand unter dem Deckel.
            if ((ua[0] - pa[0]) * nx + (ua[1] - pa[1]) * ny) <= 0.5:
                continue
            xs = (pa[0], pb[0], ua[0], ub[0])
            ys = (pa[1], pb[1], ua[1], ub[1])
            if max(xs) < 0 or min(xs) > gw or max(ys) < 0 or min(ys) > gh:
                continue
            # Die Farben haengen nur an der Blickrichtung der Wand: je
            # Richtung einmal gerechnet (seit 0.34.75), dieselben Formeln.
            farben = je_richtung.get((nx, ny))
            if farben is None:
                hell = licht.get((nx, ny), 0.7) * dunkel
                baender = []
                for nr in range(schichten):
                    f = hell * (1.0 - K.KLIPPEN["abdunkeln"] * (nr / schichten))
                    baender.append((tuple(max(0, min(255, int(c * f))) for c in grund),
                                    tuple(int(c * f * K.KLIPPEN["fuge"]) for c in grund)))
                farben = je_richtung[(nx, ny)] = (
                    baender,
                    tuple(min(255, int(c * hell * K.KLIPPEN["kante"])) for c in grund),
                    tuple(int(c * hell * 0.45) for c in grund))
            baender, kante, fuss = farben
            # Geschichteter Fels: Baender von oben nach unten, jedes etwas
            # dunkler - das liest sich als Hoehe und nicht als Flaeche.
            for nr in range(schichten):
                t0, t1 = nr / schichten, (nr + 1) / schichten
                farbe, fuge = baender[nr]
                viereck = [
                    (pa[0] + (ua[0] - pa[0]) * t0, pa[1] + (ua[1] - pa[1]) * t0),
                    (pb[0] + (ub[0] - pb[0]) * t0, pb[1] + (ub[1] - pb[1]) * t0),
                    (pb[0] + (ub[0] - pb[0]) * t1, pb[1] + (ub[1] - pb[1]) * t1),
                    (pa[0] + (ua[0] - pa[0]) * t1, pa[1] + (ua[1] - pa[1]) * t1),
                ]
                pygame.draw.polygon(ziel, farbe, viereck)
                if nr:
                    # Eine Fuge zwischen zwei Baendern, wie Schichten im Sandstein.
                    pygame.draw.line(ziel, fuge, viereck[0], viereck[1], 1)
            # Die Kante oben faengt Licht, der Fuss liegt im Schatten.
            pygame.draw.line(ziel, kante, pa, pb, 1)
            pygame.draw.line(ziel, fuss, ua, ub, 1)
            gezeichnet += 1
        return gezeichnet

    KLIPPEN_FELD = 256        # Rastergroesse der Vorauswahl in _klippen_im_bild

    def _klippen_im_bild(self, kanten, unten, oben, gw, gh) -> list:
        """Die Kanten, die ins Bild kommen koennen, in ihrer Reihenfolge
        (seit 0.34.75). Vorher wurde jedes Bild jede Kante der Karte
        umgerechnet - ueber 400, von denen eine Handvoll zu sehen war.

        Grosszuegig ausgewaehlt: was hier durchgeht, prueft klippen_zeichnen
        wie immer. Ausgelassen wird nur, was die Pruefung dort sicher
        verwirft - eine Kante, die in keiner der beiden Abbildungen das
        Bild beruehrt (Bildpunkt = (Weltpunkt - ecke) * s, s > 0)."""
        ue, usx, usy = unten
        oe, osx, osy = oben
        if min(usx, usy, osx, osy) <= 0.0 or len(kanten) < 32:
            return kanten
        merk = self.__dict__.setdefault("_klippen_raster", {})
        hit = merk.get(id(kanten))
        if hit is None or hit[0] is not kanten:
            F = self.KLIPPEN_FELD
            raster = {}
            for i, (ax, ay, bx, by, _nx, _ny) in enumerate(kanten):
                for fy in range(int(min(ay, by) // F), int(max(ay, by) // F) + 1):
                    for fx in range(int(min(ax, bx) // F), int(max(ax, bx) // F) + 1):
                        raster.setdefault((fx, fy), []).append(i)
            if len(merk) > 16:
                merk.clear()
            hit = merk[id(kanten)] = (kanten, raster)
        raster = hit[1]
        F = self.KLIPPEN_FELD
        # Was im Bild liegt, liegt in einer der beiden Abbildungen zwischen
        # ecke und ecke + Bildgroesse / s; zwei Pixel Luft gegen Rundung.
        x0 = min(oe.x, ue.x) - 2.0
        y0 = min(oe.y, ue.y) - 2.0
        x1 = max(oe.x + gw / osx, ue.x + gw / usx) + 2.0
        y1 = max(oe.y + gh / osy, ue.y + gh / usy) + 2.0
        nummern = set()
        for fy in range(int(y0 // F), int(y1 // F) + 1):
            for fx in range(int(x0 // F), int(x1 // F) + 1):
                drin = raster.get((fx, fy))
                if drin:
                    nummern.update(drin)
        return [kanten[i] for i in sorted(nummern)]

    def welt_zeichnen(self, ziel, welt, kamera, alpha, blick_hoehe=None,
                      boden=None, blick=None, oben_aus=False,
                      figuren=None, luft=None, anzeige=None) -> None:
        """Zeichnet alle Ebenen relativ zu einer Ansichtshoehe.

        Die Ansicht haengt bewusst nicht an der Ebene der Figur, sondern an
        einer Hoehe in Welt-Pixeln. Dadurch faellt beim Sturz nicht die
        Darstellung um eine Stufe, sondern die Ansicht sinkt mit: die untere
        Ebene waechst heran, die verlassene rutscht darueber weg. Dieselbe
        Zahl treibt spaeter das freie Scrollen durch die Etagen.

        dz = blick_hoehe - Ebenenhoehe.
            dz > 0   liegt unter der Ansicht: verkleinert, dunkler, im Dunst
            dz = 0   die angeschaute Ebene: unveraendert
            dz < 0   liegt darueber: vergroessert und ausgeblendet

        blick ist die angeschaute Ebene als Nummer. Nach oben wird genau
        **eine** Ebene mitgezeichnet, nicht alle: wer unten steht, soll die
        Etage ueber sich durchscheinen sehen, aber nicht gleich drei
        Stockwerke uebereinander. Ohne diese Grenze liegt ueber der
        untersten Ebene ein Stapel aus allem, was darueber gebaut ist, und
        man erkennt nicht mehr, was wozu gehoert.

        boden ist ein Aufruf (flaeche, ebene, ecke) direkt nach dem Boden
        und vor den Wesen. Damit zeichnet der Mehrspieler seinen Kreis in
        die Karte, statt darueber: er bekommt Verkleinerung, Abdunklung und
        Dunst der jeweiligen Ebene geschenkt, und die Figuren stehen
        sichtbar darauf.

        oben_aus blendet die Etage darueber dort aus, wo sie ueber
        Spielflaeche liegt (siehe `obermaske`). Das will der Mehrspieler:
        dort verdeckt sie sonst genau den Gang, in dem geschossen wird.
        """
        ecke = kamera.ecke
        held = welt.held
        p = K.PERSPEKTIVE
        if blick_hoehe is None:
            blick_hoehe = welt.hoehe(held.ebene if held else 0)

        if blick is None:
            blick = held.ebene if held else 0
        # Wie jede gezeichnete Ebene ins Bild kam - die Klippen zwischen
        # zwei Ebenen brauchen beide Abbildungen.
        abbildung: dict[int, tuple] = {}
        for idx in range(len(welt.ebenen)):
            # Hoechstens eine Etage nach oben - ausser dort, wo eine hoehere
            # Etage auf einem Felsblock steht, der bis zur Ansicht hinunter
            # geschlossen ist (`turm_auslassen`, seit 0.34.7). Vom Tal aus
            # sah die hohe Tafel sonst aus wie eine gewoehnliche: eine Wand,
            # oben nackter Fels, und ihre Oberflaeche fehlte.
            turm = idx > blick + 1
            if turm and idx - 1 not in abbildung:
                continue
            dz = blick_hoehe - welt.hoehe(idx)
            if turm:
                sicht = 1.0
            else:
                if dz < -p["ausblenden"] or dz > p["brennweite"] * p["tiefe_sichtbar"]:
                    continue
                sicht = 1.0 if dz >= 0 else max(0.0, 1.0 + dz / p["ausblenden"])
                if sicht <= 0.01:
                    continue
            k = p["brennweite"] / max(60.0, p["brennweite"] + dz)
            plan = None if abs(dz) < 1.0 else self._tiefen_plan(kamera, k)
            ab = (kamera.ecke, 1.0, 1.0) if plan is None else plan[4]
            if turm and not self._turm_im_bild(welt, idx, blick, ab[0], k):
                continue
            abbildung[idx] = ab
            if idx - 1 in abbildung:
                # Bei einem Turm zaehlt alles, was nicht zum Block gehoert,
                # als offen: die Wand steht ringsum, wo er aufhoert.
                self.klippen_zeichnen(
                    ziel, welt, idx, abbildung[idx - 1], abbildung[idx],
                    oben_aus or turm,
                    max(48, int(p["dunkel"] * k)) / 255.0 if dz > 0 else 1.0)

            if abs(dz) < 1.0:                      # die angeschaute Ebene
                self.ebene_zeichnen(ziel, welt, idx, ecke, None,
                                    p["brennweite"], aufschieben=True)
                self._ebene_inhalt(ziel, welt, idx, ecke, alpha, None, True,
                                   boden, figuren, luft, anzeige)
                continue

            dunkel = max(48, int(p["dunkel"] * k)) if dz > 0 else None
            u_ecke, groesse_f, groesse_b, versatz_b = plan[0], plan[1], plan[2], plan[3]
            flaeche = self._tiefenflaeche(k, groesse_f)
            flaeche.fill((0, 0, 0, 0))
            # Das Auge steht ueber dieser Ebene um die Brennweite plus den
            # Hoehenunterschied - von oben gesehen wirken Waende unten
            # flacher, von unten die oben steiler.
            # Frisch geleert (seit 0.34.75, siehe ebene_zeichnen): ueber ein
            # Merkmal statt eines neuen Arguments - Tests ersetzen die Methode.
            self._ziel_frisch = flaeche
            try:
                self.ebene_zeichnen(flaeche, welt, idx, u_ecke, dunkel,
                                    max(60.0, p["brennweite"] + dz), aufschieben=True)
            finally:
                self._ziel_frisch = None
            self._ebene_inhalt(flaeche, welt, idx, u_ecke, alpha, dunkel, False,
                               boden, figuren, luft, anzeige)
            # Liegt im Ausschnitt dieser Ebene gar nichts (kein Boden, und
            # die Flaeche ist ganz durchsichtig), aendert das Ausstanzen,
            # Hochskalieren und Darueberlegen auf einem deckenden Bild kein
            # Pixel - dann unterbleibt es (seit 0.34.75). Geprueft wird nur
            # ohne Boden: mit Boden ist sie nie leer, und die Frage kostete
            # umsonst.
            leer = (not getattr(self, "_boden_da", True)
                    and not ziel.get_flags() & pygame.SRCALPHA
                    and _ganz_leer(flaeche))
            if dz < 0 and idx > 0:
                # Ueber Spielflaeche blendet die Etage aus (oder ist mit
                # oben_aus ganz weg), damit sie den Gang darunter nicht
                # verdeckt. Ueber Fels - das Plateau - bleibt sie deckend:
                # sie ist der Deckel des Felsblocks, und durch einen
                # Felsblock sieht man nicht. Blass gezeichnet stand dort
                # ein Geist ueber dem Sockel statt eines Plateaus.
                if leer:
                    pass                  # leer bleibt leer, auch ausgestanzt
                elif turm:
                    # Nur der Block selbst; was ueber Spielflaeche einer
                    # tieferen Etage liegt, bleibt ganz weg.
                    self._ausstanzen(flaeche, welt, idx, u_ecke,
                                     maske=self.turm_auslassen(welt, idx, blick))
                elif oben_aus:
                    self._ausstanzen(flaeche, welt, idx, u_ecke)
                elif sicht < 0.999:
                    self._ausstanzen(flaeche, welt, idx, u_ecke,
                                     (255, 255, 255, int(255 * sicht)),
                                     pygame.BLEND_RGBA_MULT)
                sicht = 1.0
            if not leer:
                # In eine gemerkte Flaeche (seit 0.34.75) statt jedes Bild in
                # eine neue: transform.scale schreibt jedes Pixel neu.
                skaliert = self.__dict__.get("_skaliert_puffer")
                if (skaliert is None or skaliert.get_size() != groesse_b
                        or skaliert.get_flags() != flaeche.get_flags()
                        or skaliert.get_bitsize() != flaeche.get_bitsize()):
                    skaliert = pygame.transform.scale(flaeche, groesse_b)
                    self._skaliert_puffer = skaliert
                else:
                    try:
                        pygame.transform.scale(flaeche, groesse_b, skaliert)
                    except (ValueError, pygame.error):
                        skaliert = pygame.transform.scale(flaeche, groesse_b)
                        self._skaliert_puffer = skaliert
                if sicht < 0.999:
                    skaliert = plattform.deckkraft(skaliert, 255 * sicht, kopie=False)
                ziel.blit(skaliert, (-versatz_b[0], -versatz_b[1]))
            if dz > 0:
                a = int(255 * p["dunst_staerke"] * (1.0 - k))
                if a > 0:
                    self._dunst.fill((*p["dunst"], min(255, a)))
                    ziel.blit(self._dunst, (0, 0))

        if not self.nur_gelaende:
            self.fliegende_zeichnen(ziel, welt, kamera, alpha, blick_hoehe)
        if self.vignette_an:
            _rand_blit(ziel, self._vignette)

    def _ebene_inhalt(self, ziel, welt, idx, ecke, alpha, dunkel, eigene,
                      boden, figuren, luft, anzeige) -> None:
        """Alles auf einer Ebene, in der Reihenfolge, in der es sich in
        einer echten Welt verdeckt (seit 0.34.5):

        1. am Boden: Zonenkreis, Feuer, Staubringe, Figuren samt Schatten
        2. die Mauern, Kisten und Faesser - sie verdecken Pixel fuer Pixel,
           was am Boden hinter ihnen liegt
        3. was fliegt: Geschosse, Funken, Muendungsfeuer - jeweils ganz,
           wenn eine Mauer davorsteht (`verdeckt`), sonst ganz zu sehen
        4. Rauch: die Wolke ist hoeher als jede Mauer und quillt darueber
        5. Anzeige: Lebensbalken, Beute- und Schadenszahlen - darf ueber
           allem liegen

        `figuren`, `luft`, `anzeige` sind Aufrufe (flaeche, ebene, ecke)
        fuer das, was der Gast nur gemeldet bekommt (mehrspieler.py) - so
        verdeckt es sich bei ihm genauso wie beim Gastgeber.
        """
        if boden is not None:
            boden(ziel, idx, ecke)
        if self.nur_gelaende:
            self.stehende_nachholen()
            return
        self.feuer_zeichnen(ziel, welt, idx, ecke, eigene)
        self.naegel_zeichnen(ziel, welt, idx, ecke)
        self.gas_zeichnen(ziel, welt, idx, ecke)
        self.ringe_zeichnen(ziel, welt, idx, ecke)
        self.bodenstaub_zeichnen(ziel, welt, idx, ecke, alpha)
        self.effekte_zeichnen(ziel, welt, idx, ecke, True)
        self.wesen_zeichnen(ziel, welt, idx, ecke, alpha, dunkel)
        if figuren is not None:
            figuren(ziel, idx, ecke)
        self.zustaende_zeichnen(ziel, welt, idx, ecke)
        self.flugleichen_zeichnen(ziel, welt, idx, ecke, alpha, dunkel)
        self.aufbauten_zeichnen(ziel, welt, idx, ecke, alpha, dunkel)
        self.laser_zeichnen(ziel, welt, idx, ecke)
        self.stehende_nachholen()
        # Nach den Mauern (seit 0.34.87, gemeldet: "die Aufladung des
        # Spulengewehrs wird unter Mauern gerendert"): der Strahl geht durch
        # Waende, also liegen Ladelinie und Strahl ueber ihnen.
        self.entladungen_zeichnen(ziel, welt, idx, ecke)
        self.luft_zeichnen(ziel, welt, idx, ecke, alpha, dunkel)
        self.feuerbaelle_zeichnen(ziel, welt, idx, ecke, "glut")
        self.partikel_zeichnen(ziel, welt, idx, ecke, alpha)
        self.flammen_zeichnen(ziel, welt, idx, ecke, alpha)
        self.lichtblitze_zeichnen(ziel, welt, idx, ecke)
        self.muendungsfeuer(ziel, welt, ecke, idx)
        if luft is not None:
            luft(ziel, idx, ecke)
        self.feuerbaelle_zeichnen(ziel, welt, idx, ecke, "rauch")
        self.effekte_zeichnen(ziel, welt, idx, ecke, False)
        self.rauch_zeichnen(ziel, welt, idx, ecke, eigene)
        if dunkel is None:
            self.balken_zeichnen(ziel, welt, idx, ecke, alpha)
        self.aufschriften_zeichnen(ziel, welt, idx, ecke)
        if anzeige is not None:
            anzeige(ziel, idx, ecke)

    def _puffer(self, name: str) -> pygame.Surface:
        """Eine durchsichtige Hilfsflaeche in der Groesse, in der gerade
        gezeichnet wird. Mit Zoom ist das eine andere als ohne."""
        s = self._puffer_je.get(name)
        if s is None or s.get_size() != self.groesse:
            s = pygame.Surface(self.groesse, pygame.SRCALPHA)
            self._puffer_je[name] = s
        return s

    @property
    def _dunst(self) -> pygame.Surface:
        return self._puffer("dunst")

    @property
    def _linie(self) -> pygame.Surface:
        return self._puffer("linie")

    def rueckmeldung_zeichnen(self, ziel, welt, index: int, ecke) -> None:
        """Staubringe und Aufschriften der Ebene.

        Beides ist blockig gezeichnet, nicht als weicher Kreis: der Ring
        besteht aus acht Kloetzen, die nach aussen wandern. Runde Verlaeufe
        passen nicht zu einem Spiel, das aus Kacheln gebaut ist.
        """
        self.ringe_zeichnen(ziel, welt, index, ecke)
        self.aufschriften_zeichnen(ziel, welt, index, ecke)

    def ringe_zeichnen(self, ziel, welt, index: int, ecke) -> None:
        """Staubringe: liegen am Boden, also vor den Mauern gezeichnet."""
        st = K.STURZ
        for (pos, ebene, rest, wucht) in welt.ringe:
            if ebene != index:
                continue
            f = 1.0 - max(0.0, rest / st["ring_dauer"])
            weite = st["ring_weite"] * wucht * f
            klotz = max(2, int(4 * (1.0 - f) + 2))
            deckung = int(200 * (1.0 - f))
            if deckung <= 4:
                continue
            p = pos - ecke
            flaeche = pygame.Surface((klotz, klotz), pygame.SRCALPHA)
            flaeche.fill((*K.C_MUTED, deckung))
            for i in range(8):
                a = math.tau * i / 8 + wucht
                ziel.blit(flaeche, (p.x + math.cos(a) * weite - klotz / 2,
                                    p.y + math.sin(a) * weite * 0.6 - klotz / 2))

    def aufschriften_zeichnen(self, ziel, welt, index: int, ecke) -> None:
        """Beute- und Schadenszahlen: Anzeige, ueber den Mauern."""
        b = K.BEUTE_ZEIGEN
        for (pos, ebene, text, farbe, rest) in welt.aufschriften:
            if ebene != index:
                continue
            f = 1.0 - max(0.0, rest / b["dauer"])
            p = pos - ecke
            SCHRIFT.zeichnen(ziel, text, int(p.x),
                             int(p.y - 16 - b["steigt"] * f),
                             farbe if f < 0.7 else K.C_MUTED, 1,
                             ausrichtung="mitte")

    def entladungen_zeichnen(self, ziel, welt, index: int, ecke) -> None:
        """Strahl der Spule, Blitze von Kettenblitz und Kugelblitz (seit
        0.34.68), und die Ladelinie, solange einer aufladt - die sieht auch
        das Ziel (Waffenpaket: "zeigt ihre Linie, sodass das Ziel gewarnt ist")."""
        e = K.ENTLADUNG
        for w in welt.wesen:
            ladung = getattr(w, "ladung", 0.0)
            if ladung <= 0.0 or w.ebene != index or not w.lebt:
                continue
            d = K.WAFFEN.get(getattr(w, "waffe_name", ""), {})
            if d.get("art") not in ("strahl", "kette"):
                continue
            start = w.pos + pygame.Vector2(14, 0).rotate(w.winkel) - ecke
            if d["art"] == "strahl":
                ende = start + pygame.Vector2(d["reichweite"], 0).rotate(w.winkel)
                farbe = tuple(int(c * (0.35 + 0.65 * ladung)) for c in e["tuerkis"])
                pygame.draw.line(ziel, farbe, start, ende, 1)
            zufall = random.Random(int(welt.zeit * 30))
            for _ in range(1 + int(ladung * 4)):
                p = start + pygame.Vector2(zufall.uniform(-4, 4), zufall.uniform(-4, 4))
                pygame.draw.line(ziel, e["kern"], start, p, 1)
        for punkte, ebene, art, rest, dauer, saat in welt.entladungen:
            if ebene != index:
                continue
            f = max(0.0, min(1.0, rest / max(0.01, dauer)))
            pts = [p - ecke for p in punkte]
            if art == "spule":
                breite = max(1, int(5 * f))
                pygame.draw.line(ziel, e["tuerkis"], pts[0], pts[-1], breite + 2)
                pygame.draw.line(ziel, e["kern"], pts[0], pts[-1], max(1, breite - 1))
                continue
            # Ein Blitz: zwischen je zwei Punkten eine Zickzacklinie, die
            # alle paar Bilder neu springt.
            zufall = random.Random(saat + int(rest * 40))
            for a, b in zip(pts, pts[1:]):
                weg = b - a
                laenge = weg.length()
                if laenge < 1.0:
                    continue
                quer = pygame.Vector2(-weg.y, weg.x) / laenge
                teile = max(2, int(laenge / 14))
                linie = [a]
                for i in range(1, teile):
                    linie.append(a + weg * (i / teile) + quer * zufall.uniform(-6, 6))
                linie.append(b)
                pygame.draw.lines(ziel, e["tuerkis"], False, linie, 3 if f > 0.5 else 2)
                pygame.draw.lines(ziel, e["kern"], False, linie, 1)

    def zustaende_zeichnen(self, ziel, welt, index: int, ecke) -> None:
        """Betaeubt, gefroren, festgenagelt (seit 0.34.66): ueber der Figur,
        damit man sieht, warum sie stillsteht."""
        zeit = welt.zeit
        for w in welt.wesen:
            if w.ebene != index or not w.lebt:
                continue
            b, g, f = w.betaeubt_rest, w.gefroren_rest, w.fest_rest
            if b <= 0.0 and g <= 0.0 and f <= 0.0:
                continue
            x, y = int(w.pos.x - ecke.x), int(w.pos.y - ecke.y)
            r = int(getattr(w, "radius", 8.0)) + 3
            if g > 0.0:
                pygame.draw.circle(ziel, (170, 220, 255), (x, y), r, 1)
                pygame.draw.circle(ziel, (230, 245, 255), (x - r // 2, y - r // 2), 1)
            if b > 0.0:
                # Drei Funken kreisen ueber dem Kopf.
                for i in range(3):
                    a = zeit * 6.0 + i * 2.094
                    px = x + int(math.cos(a) * (r - 1))
                    py = y - r + int(math.sin(a) * 3)
                    pygame.draw.rect(ziel, (255, 236, 120) if i else (150, 220, 255),
                                     (px, py, 2, 2))
            if f > 0.0:
                pygame.draw.line(ziel, (150, 152, 156), (x - 3, y + r), (x + 3, y + r))
                pygame.draw.line(ziel, (150, 152, 156), (x, y + r - 3), (x, y + r + 2))

    def gas_zeichnen(self, ziel, welt, index: int, ecke) -> None:
        """Gaswolken (seit 0.34.67): durchscheinend gelbgruen, flach am
        Boden, mit dunkleren Schlieren und kleinen Blasen (Waffenpaket).
        Die Schlieren liegen fest (aus der Kennung), sie wandern langsam."""
        gase = getattr(welt, "gas", None)
        if not gase:
            return
        g = K.GAS
        for wolke_ in gase:
            if wolke_.ebene != index or not wolke_.lebt:
                continue
            r = int(wolke_.radius)
            if r < 2:
                continue
            flaeche = pygame.Surface((r * 2 + 2, r * 2 + 2), pygame.SRCALPHA)
            pygame.draw.circle(flaeche, g["farbe"] + (70,), (r + 1, r + 1), r)
            pygame.draw.circle(flaeche, g["farbe"] + (40,), (r + 1, r + 1), int(r * 0.7))
            zufall = random.Random(wolke_.kennung * 977)
            for i in range(7):
                a = zufall.uniform(0, math.tau) + welt.zeit * 0.15 * (1 if i % 2 else -1)
                d = r * zufall.uniform(0.2, 0.7)
                pygame.draw.circle(flaeche, g["dunkel"] + (55,),
                                   (int(r + 1 + math.cos(a) * d), int(r + 1 + math.sin(a) * d)),
                                   max(2, int(r * zufall.uniform(0.15, 0.3))))
            for i in range(5):
                a = zufall.uniform(0, math.tau)
                d = r * ((zufall.random() + welt.zeit * 0.3) % 1.0) * 0.9
                flaeche.set_at((int(r + 1 + math.cos(a) * d), int(r + 1 + math.sin(a) * d)),
                               (230, 240, 160, 150))
            ziel.blit(flaeche, (int(wolke_.pos.x - ecke.x) - r - 1,
                                int(wolke_.pos.y - ecke.y) - r - 1))

    def naegel_zeichnen(self, ziel, welt, index: int, ecke) -> None:
        """Nagelfelder (seit 0.34.65) am Boden, unter den Figuren. Die
        Naegel liegen fest (Nagelfeld.stellen); zum Ende hin verblassen
        sie nicht - wer drueberfaehrt, soll sie bis zuletzt sehen."""
        naegel = getattr(welt, "naegel", None)
        if not naegel:
            return
        breite, hoehe = ziel.get_size()
        for n in naegel:
            if n.ebene != index or not n.lebt:
                continue
            for x, y, winkel in n.stellen():
                sx, sy = x - ecke.x, y - ecke.y
                if -4 <= sx <= breite + 4 and -4 <= sy <= hoehe + 4:
                    b = self.bilder.gedreht("nagel", winkel)
                    ziel.blit(b, (sx - b.get_width() // 2, sy - b.get_height() // 2))

    def feuer_zeichnen(self, ziel, welt, index: int, ecke,
                       eigene_ebene: bool = True) -> None:
        """Brandflaechen der Ebene - **unter** allem, was dort steht.

        Das ist der Unterschied zum Rauch, und er ist wichtig: Rauch
        steht zwischen dem Betrachter und den Figuren, Feuer liegt am
        Boden und die Figuren stehen darin. Wer durch ein Feuer laeuft,
        muss sichtbar bleiben - sonst waere ein Molotow eine Sichtwand,
        und dafuer gibt es die Rauchgranate.

        Das Zuengeln kommt **nicht** aus neuem Wuerfeln je Bild. Das Feld
        steht fest; was wandert, ist die Schwelle, ab der ein Punkt
        brennt. Neu gewuerfeltes Feuer flackert wie Rauschen und sieht
        nach Fehler aus, nicht nach Flamme.
        """
        if not welt.feuer:
            return
        breite, hoehe = ziel.get_size()
        for brand in welt.feuer:
            if brand.ebene != index or not brand.lebt:
                continue
            if brand.staerke <= 0.01:
                continue
            # Erst fragen, ob es ueberhaupt im Bild liegt (seit 0.34.101): das
            # Bild eines Feuers wird gut zehnmal je Sekunde neu gebaut, und ein
            # Napalm-Angriff legt zwanzig und mehr - die meisten weit weg.
            r = brand.radius + 8
            if (brand.pos.x - r - ecke.x > breite or brand.pos.y - r - ecke.y > hoehe
                    or brand.pos.x + r - ecke.x < 0 or brand.pos.y + r - ecke.y < 0):
                continue
            flaeche, versatz = self._feuerbild(brand, welt.zeit, eigene_ebene)
            if flaeche is None:
                continue
            sx = versatz[0] - ecke.x
            sy = versatz[1] - ecke.y
            if (sx > breite or sy > hoehe
                    or sx + flaeche.get_width() < 0
                    or sy + flaeche.get_height() < 0):
                continue
            ziel.blit(flaeche, (sx, sy))

    def _feuerbild(self, brand, zeit: float, eigene_ebene: bool):
        """Eine Brandflaeche als Bild, in Stufen aus dem Dichtefeld.

        Gemerkt wird nach Kennung und einem groben Zeitschritt: die
        Flammen sollen zuengeln, aber nicht jedes Bild neu gezeichnet
        werden - bei dreihundert Bildern je Sekunde waere das dreihundert
        Mal dieselbe Rechnung fuer ein Bild, das sich kaum aendert.
        """
        f = K.FEUER
        korn = f["korn"]
        napalm = getattr(brand, "napalm", False)
        schritt = 1.0 / max(1.0, f["napalm_zunge" if napalm else "zunge"] * 6.0)
        takt = int(zeit / schritt)
        schluessel = (brand.kennung, takt, round(brand.staerke, 2), eigene_ebene)
        hit = self._feuer_puffer.get(brand.kennung)
        if hit is not None and hit[0] == schluessel:
            return hit[1], hit[2]
        breite, x0, y0, werte = brand.feld(korn)
        flaeche = pygame.Surface((breite * korn, breite * korn), pygame.SRCALPHA)
        toene = f["napalm_toene"] if napalm else f["toene"]
        # Die wandernde Schwelle: einmal je Zeitschritt ein neuer Wert,
        # aus der Kennung und dem Takt gewuerfelt. Damit zuengelt es auf
        # jedem Rechner gleich, ohne dass etwas uebertragen werden muss.
        zunge = ((brand.kennung * 2654435761 + takt * 40503) % 1000) / 1000.0
        grund = f["napalm_schwelle" if napalm else "schwelle"] * (0.80 + 0.40 * zunge)
        stufen = len(toene)
        deckung = brand.staerke if eigene_ebene else brand.staerke * 0.65
        russ = grund - 0.12                    # Napalm: oeliger Russ am Rand
        for gy in range(breite):
            zeile = gy * breite
            for gx in range(breite):
                w = werte[zeile + gx]
                if w <= grund:
                    if napalm and w > russ:
                        pygame.draw.rect(flaeche, (*f["napalm_russ"], int(170 * deckung)),
                                         (gx * korn, gy * korn, korn, korn))
                    continue
                # Je dichter, desto heisser: aussen Glimmen, innen heller
                # Kern. Der Kern ist klein, sonst sieht es aus wie eine
                # Lampe und nicht wie Feuer.
                anteil = min(1.0, (w - grund) / max(0.01, 1.0 - grund))
                # Linear, weil das Feld schon auf 0 bis 1 normiert ist.
                # Der helle Kern ist damit genau das oberste Viertel der
                # Dichte - ein Kern, keine Flaeche.
                stufe = min(stufen - 1, int(anteil * stufen))
                ton = toene[stufe]
                a = int(255 * deckung * (0.55 + 0.45 * anteil))
                pygame.draw.rect(flaeche, (*ton, a),
                                 (gx * korn, gy * korn, korn, korn))
        self._feuer_puffer[brand.kennung] = (schluessel, flaeche, (x0, y0))
        # Was nicht mehr brennt, muss auch nicht mehr gemerkt werden. Die
        # Grenze lag bei 24 - mit einem Napalm-Angriff brennen mehr, und der
        # Puffer wurde bei jedem neuen Bild geleert (seit 0.34.101: 96).
        if len(self._feuer_puffer) > 96:
            self._feuer_puffer.clear()
        return flaeche, (x0, y0)

    def rauch_zeichnen(self, ziel, welt, index: int, ecke,
                       eigene_ebene: bool = True) -> None:
        """Rauchwolken der Ebene, ueber allem, was dort steht.

        Drei Dinge machen den Unterschied zu einer gemalten Wolke:

        1. **Wirklich deckend.** Innen liegt sie bei voller Deckkraft. Wer
           darin steht, ist nicht zu sehen - und sein Name auch nicht,
           siehe `welt.verdeckt`.
        2. **Aufloesung wie der Rest.** Gezeichnet wird in Bildpunkten von
           `RAUCH["korn"]` Pixeln, also im selben Massstab wie die Kacheln
           daneben. Die Form kommt aus einem glatten Dichtefeld, nicht aus
           einzeln gewuerfelten Kloetzen - sonst sieht es nach Konfetti
           aus statt nach Rauch.
        3. **Ebene erkennbar.** Rauch einer fremden Ebene ist blasser.
           Ohne das sieht eine Wand eine Etage hoeher genauso aus wie die
           vor der eigenen Nase.
        """
        if not welt.rauch:
            return
        breite, hoehe = ziel.get_size()
        for wolke_ in welt.rauch:
            if wolke_.ebene != index or not wolke_.lebt:
                continue
            if wolke_.dichte <= 0.01:
                continue
            flaeche, versatz = self._rauchbild(wolke_, eigene_ebene)
            if flaeche is None:
                continue
            sx = versatz[0] - ecke.x
            sy = versatz[1] - ecke.y
            if (sx > breite or sy > hoehe
                    or sx + flaeche.get_width() < 0
                    or sy + flaeche.get_height() < 0):
                continue
            ziel.blit(flaeche, (sx, sy))

    def _rauchbild(self, wolke_, eigene_ebene: bool):
        """Die fertige Wolke als Flaeche, dazu ihre linke obere Weltecke.

        Das Dichtefeld kommt fertig von der Wolke; hier wird daraus nur
        noch Farbe. Gebaut wird in einem kleinen Puffer, in dem ein
        Bildpunkt einem Korn entspricht, und erst am Schluss hart
        hochskaliert - das ist um Groessenordnungen schneller, als ein
        paar tausend Rechtecke einzeln zu zeichnen, und ergibt genau die
        harten Kanten, die zum Rest des Spiels passen.

        **Volumen** kommt aus dem Gefaelle des Feldes: wo die Wolke zum
        Licht hin dichter wird, ist sie hell, auf der Gegenseite dunkel.
        Licht von oben links, wie ueberall sonst im Spiel. Das ist der
        Unterschied zwischen einer Flaeche in Grau und etwas, das nach
        einem Koerper aussieht.
        """
        r = K.RAUCH
        stufe = int(wolke_.dichte * 5)
        schluessel = (id(wolke_), stufe, eigene_ebene)
        fertig = self._rauch_puffer.get(schluessel)
        if fertig is not None:
            return fertig

        korn = max(1, int(r["korn"]))
        breite, x0, y0, werte = wolke_.feld(korn)
        toene = r["toene"]
        anzahl = len(toene)
        dichte = wolke_.dichte
        # Beim Aufziehen waechst die Wand von innen nach aussen, beim
        # Verwehen zieht sie sich wieder zusammen. Die Form bleibt, nur
        # die Schwelle wandert.
        schwelle = r["schwelle"] + (1.0 - dichte) * 0.55
        # Das Licht als Schritt im Feld, nicht in Weltpixeln: so bleibt
        # die Schattierung gleich, wenn man am Korn dreht.
        lx = int(round(r["licht"][0] * r["licht_weite"] / korn))
        ly = int(round(r["licht"][1] * r["licht_weite"] / korn))
        staerke = r["licht_staerke"]
        grund = r["grund"]
        dicke_hell = r["dicke_hell"]
        # Wie dick die Wolke an der dicksten Stelle ist - danach richtet
        # sich, was "hell" heisst. Sonst waere eine verwehende Wolke
        # gleichmaessig dunkel statt duenner.
        dickste = max(werte) if werte else 1.0
        spanne_d = max(0.01, dickste - schwelle)
        # Die Deckkraft haengt am Abstand zur Mitte, nicht am Rauschen.
        # Sonst riss jede Delle im Feld ein durchsichtiges Loch mitten in
        # die Wand - und genau dort, wo `welt.verdeckt` sagt, hier sei
        # niemand zu sehen. Beides muss dieselbe Grenze benutzen.
        mx = (wolke_.pos.x - x0) / korn
        my = (wolke_.pos.y - y0) / korn
        schichten = [((wolke_.radius * bis / korn) ** 2, deck)
                     for (bis, deck) in r["schichten"]]
        if not eigene_ebene:
            schichten = [(g, int(d * r["fremde_ebene"])) for (g, d) in schichten]

        roh = bytearray(breite * breite * 4)
        for gy in range(breite):
            zeile = gy * breite
            dy = gy + 0.5 - my
            dy2 = dy * dy
            for gx in range(breite):
                d = werte[zeile + gx]
                if d <= schwelle:
                    continue
                qx, qy = gx + lx, gy + ly
                gegen = (werte[qy * breite + qx]
                         if 0 <= qx < breite and 0 <= qy < breite else 0.0)
                tief = (d - schwelle) / spanne_d
                hell = grund + dicke_hell * tief + (d - gegen) * staerke
                i = int((1.0 - max(0.0, min(1.0, hell))) * (anzahl - 1) + 0.5)
                ton = toene[max(0, min(anzahl - 1, i))]
                dx = gx + 0.5 - mx
                weg2 = dx * dx + dy2
                a = 0
                for (grenze, deck) in schichten:
                    if weg2 <= grenze:
                        a = deck
                        break
                if not a:
                    continue
                stelle = (zeile + gx) * 4
                roh[stelle] = ton[0]
                roh[stelle + 1] = ton[1]
                roh[stelle + 2] = ton[2]
                roh[stelle + 3] = a

        klein = pygame.image.frombytes(bytes(roh), (breite, breite), "RGBA")
        flaeche = (klein if korn == 1 else
                   pygame.transform.scale(klein, (breite * korn, breite * korn)))
        # Ins Format des Fensters (seit 0.34.74). Aus rohen Bytes hat die
        # Flaeche die Byte-Folge RGBA, das Fenster meist eine andere; auf
        # einem Intel-Mac kam die Wolke damit auf einem schwarzen Viereck an
        # (gemeldet mit Bild). Dieselbe Art Fehler wie auf dem iPhone in
        # 0.34.21. Ohne Fenster (Tests, Aufnahmen) bleibt sie, wie sie ist.
        if pygame.display.get_surface() is not None:
            try:
                flaeche = flaeche.convert_alpha()
            except pygame.error:
                pass
        if len(self._rauch_puffer) > r["puffer"]:
            self._rauch_puffer.clear()
        self._rauch_puffer[schluessel] = (flaeche, (x0, y0))
        return flaeche, (x0, y0)

    def kreis_zone(self, ziel, mitte, radius: float, farbe, anteil: float = 0.0,
                   puls: float = 0.0, ring: int = 3, fuellung: int = 34) -> None:
        """Der Kreis in der Kartenmitte, wie ihn der Mehrspieler braucht.

        Absichtlich ohne Kamera und ohne Ebene: der Aufrufer uebergibt den
        Mittelpunkt bereits in der Flaeche, in die gezeichnet wird. So
        stimmt der Kreis auch auf den verkleinerten Tiefenflaechen, ohne
        dass hier irgendetwas von Perspektive wissen muesste.

        anteil zeichnet den Ladestand als Bogen, oben beginnend und im
        Uhrzeigersinn - das liest man schneller als eine Zahl.
        """
        r = int(round(radius))
        if r < 2:
            return
        m = pygame.Vector2(mitte)
        rand = max(ring + 2, 4)
        flaeche = pygame.Surface((2 * (r + rand), 2 * (r + rand)),
                                 pygame.SRCALPHA)
        mp = (r + rand, r + rand)
        pygame.draw.circle(flaeche, (*farbe, fuellung), mp, r)
        # Der Ring pulst leicht. Ein ruhiger Kreis verschwindet im Boden,
        # ein pulsender sagt: hier geht es um etwas.
        schlag = 0.5 + 0.5 * math.sin(puls * math.tau)
        pygame.draw.circle(flaeche, (*farbe, int(120 + 90 * schlag)), mp, r,
                           max(1, ring))
        if anteil > 0.001:
            kasten = pygame.Rect(rand, rand, 2 * r, 2 * r)
            bogen = math.tau * max(0.0, min(1.0, anteil))
            pygame.draw.arc(flaeche, (*farbe, 255), kasten,
                            math.pi / 2 - bogen, math.pi / 2,
                            max(2, ring + 1))
        ziel.blit(flaeche, (m.x - r - rand, m.y - r - rand))

    def kreis_weiter(self, ziel, mitte, radius: float, richtung, farbe,
                     zeit: float = 0.0) -> None:
        """Ein ">" im Kreis, das dorthin zeigt, wohin er als naechstes
        zieht (seit 0.34.8). Liegt auf dem Boden wie der Kreis selbst,
        also unter den Figuren, und rueckt sacht in seine Richtung vor -
        so liest man es als Bewegung und nicht als Muster im Sand.

        `mitte` ist schon in der Flaeche gerechnet, wie bei `kreis_zone`.
        """
        r = pygame.Vector2(richtung)
        if r.length_squared() < 1.0 or radius < 4:
            return
        z = K.ZONE
        winkel = math.degrees(math.atan2(r.y, r.x))
        s = radius * z["weiter_groesse"]
        d = z["weiter_dicke"]
        vor = radius * (0.12 + 0.06 * math.sin(zeit * math.tau * 0.8))
        # Ein dickes ">" mit der Spitze nach +x, dann gedreht.
        form = [(-s * 0.5, -s), (-s * 0.5 + d, -s), (s * 0.5 + d, 0.0),
                (-s * 0.5 + d, s), (-s * 0.5, s), (s * 0.5, 0.0)]
        punkte = [pygame.Vector2(x + vor, y).rotate(winkel) for x, y in form]
        rand = int(s + d + vor) + 4
        flaeche = pygame.Surface((2 * rand, 2 * rand), pygame.SRCALPHA)
        mp = pygame.Vector2(rand, rand)
        pygame.draw.polygon(flaeche, (16, 11, 8, z["weiter_deckkraft"] // 2),
                            [mp + p + (2, 2) for p in punkte])
        pygame.draw.polygon(flaeche, (*farbe, z["weiter_deckkraft"]),
                            [mp + p for p in punkte])
        m = pygame.Vector2(mitte)
        ziel.blit(flaeche, (m.x - rand, m.y - rand))

    def tracer(self, ziel, welt, kamera, spieler) -> None:
        """Zielhilfe: eine duenne Linie von der Waffe zum Mauszeiger.

        Mit tracer_weit laeuft sie darueber hinaus weiter, bis etwas im Weg
        steht. Beides sind Schalter am Spieler, T und Z.
        """
        if not spieler.tracer or not spieler.lebt:
            return
        t = K.TRACER
        ecke = kamera.ecke
        muendung = spieler.pos + pygame.Vector2(14, 0).rotate(spieler.winkel)
        ende = pygame.Vector2(spieler.ziel)
        richtung = ende - muendung
        if richtung.length_squared() < 4:
            return
        if spieler.tracer_weit:
            ende = welt.strahl(muendung, richtung.normalize(), t["weite"],
                               spieler.ebene)
        a = muendung - ecke
        b = ende - ecke
        linie = self._linie
        linie.fill((0, 0, 0, 0))
        # Durchgehend rot. Frueher lag auf den ersten Prozenten ein heller
        # Kern; weil er am Anteil der Strecke hing, wuchs er mit, sobald man
        # die Linie mit Z verlaengert hat, und sah aus wie ein Fehler.
        pygame.draw.line(linie, (*t["farbe"], t["staerke"]), a, b, 1)
        ziel.blit(linie, (0, 0))
        pygame.draw.rect(ziel, t["punkt"], (int(b.x) - 1, int(b.y) - 1, 3, 3))

    def laser_zeichnen(self, ziel, welt, index: int, ecke) -> None:
        """Der Ziellaser der Panzerbuechse (seit 0.34.62): jeder sieht ihn,
        bei jedem, der sie haelt - er verraet den Schuetzen. Bis zur ersten
        Mauer, hoechstens K.LASER["weite"]."""
        t = K.LASER
        linie = None
        for w in welt.wesen:
            if (w.ebene != index or not w.lebt or not hasattr(w, "waffe_daten")
                    or getattr(w, "am_boden", False) or getattr(w, "im_fahrzeug", False)
                    or getattr(w, "schwingt", False) or not w.waffen):
                continue
            if not K.WAFFEN.get(w.waffe_name, {}).get("laser"):
                continue
            richtung = pygame.Vector2(1, 0).rotate(w.winkel)
            muendung = w.pos + richtung * t["ab"]
            ende = welt.strahl(muendung, richtung, t["weite"], index)
            if linie is None:
                linie = self._linie
                linie.fill((0, 0, 0, 0))
            pygame.draw.line(linie, (*t["farbe"], t["staerke"]), muendung - ecke,
                             ende - ecke, 1)
            b = ende - ecke
            pygame.draw.rect(linie, (*t["punkt"], 230), (int(b.x) - 1, int(b.y) - 1, 2, 2))
        if linie is not None:
            ziel.blit(linie, (0, 0))

    def zielhilfen(self, ziel, welt, kamera, spieler) -> None:
        """Streukegel der Scharfschuetzenwaffe und der Nahkampfbogen."""
        if not spieler.lebt:
            return
        ecke = kamera.ecke
        d = spieler.waffe_daten
        p = spieler.pos - ecke

        if d.get("fokus_dauer"):
            halb = spieler.streuung_jetzt
            # So weit, wie man sieht (seit 0.34.96 mit dem Zoom - vorher
            # fest eine halbe Bildbreite, also im weiten Blick zu kurz).
            weite = min(d["reichweite"], max(340.0, kamera.breite * 0.6))
            muendung = spieler.pos + pygame.Vector2(14, 0).rotate(spieler.winkel)
            a = muendung - ecke
            linie = self._linie
            linie.fill((0, 0, 0, 0))
            deck = int(40 + 90 * spieler.fokus)
            for vz in (-1, 1):
                b = a + pygame.Vector2(weite, 0).rotate(spieler.winkel + halb * vz)
                pygame.draw.line(linie, (*K.C_AMBER, deck), a, b, 1)
            # Ruhig genug fuer die Mittellinie - nicht beim Praezisionsgewehr
            # (seit 0.34.62, gemeldet: "die weisse Linie raus").
            if spieler.fokus > 0.55 and d.get("fokus_mittellinie", True):
                b = a + pygame.Vector2(weite, 0).rotate(spieler.winkel)
                pygame.draw.line(linie, (*K.C_CREAM, int(60 + 120 * spieler.fokus)),
                                 a, b, 1)
            ziel.blit(linie, (0, 0))

        # Der Schwung gehoert jetzt zum Brecheisen auf der eigenen Taste,
        # nicht mehr zur gewaehlten Waffe. Gezeichnet wird er deshalb mit
        # **dessen** Daten - sonst haette ein Schlag mit dem Sturmgewehr in
        # der Hand die Reichweite des Sturmgewehrs.
        if spieler.schlag_zeigen > 0:
            nah = K.WAFFEN.get(K.NAHKAMPF["waffe"], d)
            if nah.get("art") == "nahkampf" or d.get("art") == "nahkampf":
                self.schwung_zeichnen(ziel, spieler, p, nah)

    def schwung_zeichnen(self, ziel, spieler, p, d) -> None:
        """Der Schlag mit dem Brecheisen, als Bewegung statt als Kegel.

        Vorher lag waehrend des Schlags ein heller Kegel vor der Figur und
        verblasste - man sah, *dass* geschlagen wurde, aber nichts schwang.
        Jetzt faehrt das Eisen in der Zeit des Schlags einmal durch den
        Kegel, von der einen Seite zur anderen, und zieht eine kurze
        Spur hinter sich her.

        Gezeichnet wird mit Kloetzen statt mit einem weichen Bogen: das
        passt zum Rest des Spiels und liest sich bei 640 Pixeln Breite
        besser als eine duenne Kurve.
        """
        dauer = d.get("schwung", 0.26)
        lauf = spieler.schlag_zeigen - K.NAHKAMPF["nachhalten"]
        if lauf <= 0.0:
            return                  # Nachhalten: das Eisen steht, keine Spur
        f = 1.0 - max(0.0, min(1.0, lauf / dauer))
        halb = d["winkel"] * 0.5
        # Von -halb nach +halb, am Anfang schnell, am Ende auslaufend.
        weg = 1.0 - (1.0 - f) * (1.0 - f)
        jetzt = spieler.winkel - halb + 2 * halb * weg
        # Seit 0.32.8 haelt die Figur selbst das Eisen (Bildfolge
        # spieler_schwung_*). Hier bleibt nur die Spur der Spitze: ein paar
        # blasse Punkte auf dem Bogen hinter ihr - die Bewegung, die das
        # Auge zwischen zwei Bildern sonst verliert.
        linie = self._linie
        linie.fill((0, 0, 0, 0))
        spitze = 12.0 + 21.0          # Hand + Laenge des Eisens bis zur Klaue
        for i in range(1, 7):
            zurueck = jetzt - (2 * halb) * 0.07 * i
            if zurueck < spieler.winkel - halb:
                break
            deck = int(120 * (1.0 - i / 7.0) * (1.0 - f * 0.6))
            if deck <= 4:
                continue
            q = p + pygame.Vector2(spitze, 0).rotate(zurueck)
            pygame.draw.rect(linie, (*K.C_CREAM, deck), (int(q.x) - 1, int(q.y) - 1, 2, 2))
        ziel.blit(linie, (0, 0))

    # ---- HUD -------------------------------------------------------
    def hud(self, ziel, welt, spieler, wellen_text, punkte, blick=None,
            kopf: bool = True) -> None:
        """kopf=False laesst die Kopfzeile weg. Im Gefecht gibt es weder
        Wellen noch Schrott, und "SCHROTT 3" fuer drei Abschuesse waere
        schlicht gelogen."""
        f = SCHRIFT
        # Lebensbalken
        x, y = 12, K.GAME_H - 26
        breite = 128
        anteil = max(0.0, spieler.leben / spieler.max_leben)
        pygame.draw.rect(ziel, (18, 12, 9), (x - 2, y - 2, breite + 4, 12))
        pygame.draw.rect(ziel, K.C_MUTED_DK, (x - 2, y - 2, breite + 4, 12), 1)
        farbe = K.C_TEAL if anteil > 0.35 else K.C_RED
        segmente = 16
        for i in range(segmente):
            if i / segmente < anteil:
                pygame.draw.rect(ziel, farbe, (x + i * (breite // segmente), y,
                                               breite // segmente - 2, 8))
        f.zeichnen(ziel, "PANZERUNG", x, y - 12, K.C_MUTED, 1)
        f.zeichnen(ziel, "%d" % max(0, round(spieler.leben)), x + breite + 8, y,
                   K.C_CREAM, 1)

        # Waffe und Magazin
        d = spieler.waffe_daten
        rx = K.GAME_W - 12
        f.zeichnen(ziel, d["name"], rx, y - 12, K.C_AMBER, 1, ausrichtung="rechts")
        # Hat die Waffe Betriebsarten, steht die gewaehlte daneben. Ohne
        # das weiss man nicht, was gleich passiert, wenn man drueckt - und
        # das ist bei einem MG der Unterschied zwischen einer Salve und
        # einem halben Magazin.
        kurz = d.get("kurz")
        if kurz:
            breite_name = f.breite(d["name"], 1)
            f.zeichnen(ziel, kurz, rx - breite_name - 6, y - 12,
                       K.C_TEAL, 1, ausrichtung="rechts")
        # Der Anlauf einer Waffe mit Drehzahl: ein schmaler Streifen unter
        # dem Namen. Er sagt, ob der naechste Druck schon Feuer ergibt.
        if getattr(spieler, "anlauf", 0.0) > 0.02:
            bw = 40
            pygame.draw.rect(ziel, (18, 12, 9), (rx - bw, y - 3, bw, 2))
            pygame.draw.rect(ziel, K.C_TEAL,
                             (rx - bw, y - 3, int(bw * spieler.anlauf), 2))
        if spieler.nachlade_rest > 0:
            p = 1.0 - spieler.nachlade_rest / d["nachladen"]
            bw = 74
            pygame.draw.rect(ziel, (18, 12, 9), (rx - bw, y, bw, 8))
            pygame.draw.rect(ziel, K.C_AMBER, (rx - bw, y, int(bw * p), 8))
            f.zeichnen(ziel, "NACHLADEN", rx - bw - 6, y, K.C_MUTED, 1,
                       ausrichtung="rechts")
        else:
            # Rechts steht **nur** das Magazin, nicht mehr "12 / 30". Die
            # zweite Zahl war der Inhalt eines vollen Magazins, also eine
            # Konstante - und im Gefecht liest niemand eine Konstante. Was
            # man wissen will, ist "wie viele noch", und das soll gross und
            # allein dastehen. Der Vorrat steht in der Hotbar, bei der
            # Waffe, zu der er gehoert.
            munition = spieler.magazin[spieler.waffe_name]
            leer = not munition and d.get("magazin")
            farbe = K.C_CREAM
            if leer:
                # Ein leeres Magazin blinkt. Rot allein reicht nicht: rot
                # ist im HUD auch der Lebensbalken, und wer gerade beschossen
                # wird, schaut nicht genau hin.
                farbe = K.C_RED if (welt.zeit * 4.0) % 1.0 < 0.6 else (90, 26, 20)
            f.zeichnen(ziel, "%d" % munition, rx, y, farbe, 2,
                       ausrichtung="rechts")

        # Ebenenanzeige, wie die Scrollleiste in den Mockups
        ex = K.GAME_W - 26
        if blick is None:
            blick = spieler.ebene
        for i in range(len(welt.ebenen) - 1, -1, -1):
            ey = 16 + (len(welt.ebenen) - 1 - i) * 14
            angeschaut = (i == blick)
            r = pygame.Rect(ex, ey, 18, 11)
            pygame.draw.rect(ziel, K.C_AMBER if angeschaut else (18, 12, 9), r)
            pygame.draw.rect(ziel, K.C_AMBER if angeschaut else K.C_MUTED_DK, r, 1)
            f.zeichnen(ziel, "E%d" % i, r.centerx, ey + 2,
                       (18, 12, 8) if angeschaut else K.C_MUTED, 1, ausrichtung="mitte")
            if i == spieler.ebene:          # wo die Figur wirklich steht
                pygame.draw.rect(ziel, K.C_TEAL, (ex - 5, ey + 3, 3, 5))

        # Hotbar unten in der Mitte
        knapp = bool(getattr(spieler, "knapp", False))
        vorrat = getattr(spieler, "vorrat", {})
        n = len(spieler.waffen)
        bw, bh, luecke = 34, 18, 3
        gesamt = n * bw + (n - 1) * luecke
        hx = (K.GAME_W - gesamt) // 2
        hy = K.GAME_H - 22
        for i, name in enumerate(spieler.waffen):
            r = pygame.Rect(hx + i * (bw + luecke), hy, bw, bh)
            aktiv = (i == spieler.waffe)
            wd = K.WAFFEN[name]
            # Der Platz der gewaehlten Waffe sieht anders aus, wenn ihr
            # Magazin leer ist. Nicht nur die Zahl daneben: im Gefecht
            # schaut man auf die Hotbar, um zu entscheiden, worauf man
            # wechselt, und dann muss man "der hier ist leer" sehen, ohne
            # drei Zahlen zu lesen.
            leer = aktiv and wd.get("magazin") and not spieler.magazin[name]
            pygame.draw.rect(ziel, (34, 10, 8) if leer else (10, 7, 5), r)
            pygame.draw.rect(ziel, K.C_RED if leer else
                             (K.C_AMBER if aktiv else K.C_MUTED_DK), r, 1)
            if leer:
                # Ein Balken quer, wie ein durchgestrichenes Feld.
                pygame.draw.line(ziel, (120, 34, 26), (r.x + 2, r.bottom - 3),
                                 (r.right - 3, r.bottom - 3))
            # Symbol statt abgeschnittenem Namen: auf 34 Pixel Breite passen
            # nur vier Buchstaben, und "SCHA" sagt niemandem etwas.
            sym = self.bilder.bild("waffe_" + name)
            ziel.blit(sym, (r.centerx - sym.get_width() // 2,
                            r.centery - sym.get_height() // 2))
            f.zeichnen(ziel, "%d" % (i + 1), r.x + 2, r.y + 2,
                       K.C_RED if leer else
                       (K.C_AMBER if aktiv else K.C_MUTED_DK), 1)
            # In der Hotbar steht der **Vorrat**, nicht das Magazin. Das
            # Magazin der gewaehlten Waffe steht schon gross rechts; es ein
            # zweites Mal hinzuschreiben kostet den Platz, an dem die
            # eigentliche Frage steht: reicht es ueberhaupt noch?
            if not wd.get("magazin"):
                text, farbe = "--", K.C_MUTED_DK
            elif not knapp:
                # Ohne knappe Munition wird nichts abgezogen. Eine Zahl,
                # die nie kleiner wird, waere eine Luege.
                text, farbe = "∞", (K.C_MUTED if aktiv else K.C_MUTED_DK)
            else:
                uebrig = vorrat.get(name, 0)
                text = "%d" % uebrig
                farbe = (K.C_RED if not uebrig else
                         (K.C_AMBER if aktiv else K.C_MUTED))
            f.zeichnen(ziel, text, r.right - 2, r.bottom - 9, farbe, 1,
                       ausrichtung="rechts")

        # Medkits links neben der Hotbar
        mx = hx - 40
        f.zeichnen(ziel, "[H]", mx, hy + 1, K.C_MUTED_DK, 1)
        for i in range(K.MEDKIT["hoechstens"]):
            r = pygame.Rect(mx + i * 9, hy + 9, 7, 7)
            pygame.draw.rect(ziel, K.C_TEAL if i < spieler.medkits else (24, 18, 13), r)
            pygame.draw.rect(ziel, K.C_TEAL_DK, r, 1)
        if spieler.heilt_rest > 0:
            anteil = 1.0 - spieler.heilt_rest / K.MEDKIT["dauer"]
            pygame.draw.rect(ziel, K.C_TEAL, (mx, hy - 4, int(30 * anteil), 2))

        # Kopfzeile
        if kopf:
            f.zeichnen(ziel, wellen_text, 12, 12, K.C_MUTED, 1)
            f.zeichnen(ziel, "SCHROTT %d" % punkte, 12, 22, K.C_AMBER, 1)

    def hinweis(self, ziel, text) -> None:
        w = SCHRIFT.breite(text, 1) + 14
        r = pygame.Rect((K.GAME_W - w) // 2, K.GAME_H - 58, w, 15)
        pygame.draw.rect(ziel, (14, 10, 8), r)
        pygame.draw.rect(ziel, K.C_AMBER, r, 1)
        SCHRIFT.zeichnen(ziel, text, r.centerx, r.y + 4, K.C_CREAM, 1,
                         ausrichtung="mitte")

    def schaden_blende(self, ziel, staerke: float) -> None:
        self.blende(ziel, K.C_RED, 90 * min(1.0, staerke))

    def blende(self, ziel, farbe, deckung: float) -> None:
        """Ein Farbschleier ueber dem ganzen Bild."""
        d = int(max(0, min(255, deckung)))
        if d <= 0:
            return
        s = pygame.Surface((K.GAME_W, K.GAME_H), pygame.SRCALPHA)
        s.fill((*farbe, d))
        ziel.blit(s, (0, 0))

    def randglut(self, ziel, farbe, staerke: float) -> None:
        """Farbe an den Bildraendern, die Mitte bleibt frei.

        Fuer Zustaende, die man die ganze Zeit sieht und trotzdem nicht im
        Weg haben will - das Aufhelfen zum Beispiel: man muss weiter
        erkennen, wer von wo kommt, soll aber keine Sekunde vergessen,
        dass man gerade festgehalten ist.
        """
        staerke = max(0.0, min(1.0, staerke))
        if staerke <= 0.01:
            return
        s = pygame.Surface((K.GAME_W, K.GAME_H), pygame.SRCALPHA)
        breit = int(K.GLUT["breite"] * staerke)
        stufen = max(1, K.GLUT["stufen"])
        for i in range(stufen):
            d = int(K.GLUT["deckung"] * staerke * (1.0 - i / stufen))
            if d <= 0:
                continue
            dick = max(1, breit // stufen)
            rand = i * dick
            pygame.draw.rect(s, (*farbe, d),
                             (rand, rand, K.GAME_W - 2 * rand,
                              K.GAME_H - 2 * rand), dick)
        ziel.blit(s, (0, 0))

    def debug(self, ziel, app, welt) -> None:
        f = SCHRIFT
        zeilen = [
            "FPS %d" % round(app.fps),
            "WESEN %d" % len(welt.wesen),
            "PARTIKEL %d" % len(welt.partikel),
            "EBENE %d VON %d" % (welt.held.ebene, len(welt.ebenen)),
        ]
        for i, z in enumerate(zeilen):
            f.zeichnen(ziel, z, K.GAME_W - 12, 60 + i * 9, K.C_TEAL, 1,
                       ausrichtung="rechts")


# ══════════════════════════════════════════════════════════════════
# Befinden: wie es einem geht, ohne dass man auf eine Zahl schaut
# ══════════════════════════════════════════════════════════════════

class Trefferzeichen:
    """Das X am Mauszeiger, wenn ein eigener Treffer ankommt (seit 0.34.15).

    Gemeldet: "irgendwas, was klar symbolisiert, wenn man einen Gegner
    trifft". Der Getroffene blitzte zwar schon kurz auf - aber nur dort, wo
    er steht, und das ist im Gedraenge, hinter Rauch oder am Bildrand nicht
    da, wo man hinschaut. Hingeschaut wird auf den Zeiger. Dort springt
    jetzt ein X auf: weiss je Treffer, rot und groesser, wenn er erledigt
    oder umwirft. Dazu ein Ticken, nur fuer den Schuetzen.

    Gezaehlt wird am Spieler (Spieler.treffer_melden), hier wird nur
    verglichen. GRUND: Beim Gast kommen die Zaehler mit der Weltmeldung,
    und ein Zaehler verliert keinen Treffer, der zwischen zwei Meldungen
    passiert - ein Ereignis koennte das.
    """

    def __init__(self) -> None:
        self.rest = 0.0
        self.dauer = 1.0
        self.toedlich = False
        self._wer = None
        self._t = 0
        self._k = 0

    def beobachten(self, spieler, dt: float) -> str:
        """Einmal je Schritt. Gibt den Ton zurueck, der jetzt dran ist, oder ""."""
        self.rest = max(0.0, self.rest - dt)
        if spieler is None:
            return ""
        t = int(getattr(spieler, "treffer_marken", 0))
        k = int(getattr(spieler, "toedlich_marken", 0))
        if spieler is not self._wer or t < self._t or k < self._k:
            # Neue Figur oder neue Zaehlung: nur merken, nichts zeigen.
            self._wer, self._t, self._k = spieler, t, k
            return ""
        ton = ""
        m = K.TREFFERMARKE
        if k > self._k:
            self.toedlich, self.dauer = True, m["dauer_toedlich"]
            self.rest = self.dauer
            ton = "trefferzeichen_toedlich"
        elif t > self._t and not (self.toedlich and self.rest > m["dauer"]):
            # Ein gewoehnlicher Treffer ueberdeckt ein frisches rotes X
            # nicht - das soll man sehen.
            self.toedlich, self.dauer = False, m["dauer"]
            self.rest = self.dauer
            ton = "trefferzeichen"
        self._t, self._k = t, k
        return ton

    def zeichnen(self, ziel, pos) -> None:
        if self.rest <= 0.0:
            return
        m = K.TREFFERMARKE
        f = self.rest / max(1e-6, self.dauer)          # 1 -> 0
        # Erst aufspringen, dann stehen, dann verblassen.
        gross = 1.0 + m["pop"] * max(0.0, (f - 0.7) / 0.3)
        deck = 255 if f > 0.35 else int(255 * f / 0.35)
        laenge = m["laenge_toedlich"] if self.toedlich else m["laenge"]
        farbe = K.C_RED if self.toedlich else (255, 250, 236)
        rand = int(laenge * gross + m["luecke"] * gross) + 4
        s = pygame.Surface((2 * rand, 2 * rand), pygame.SRCALPHA)
        c = pygame.Vector2(rand, rand)
        for sx, sy in ((1, 1), (1, -1), (-1, 1), (-1, -1)):
            d = pygame.Vector2(sx, sy).normalize()
            a = c + d * (m["luecke"] * gross)
            b = c + d * ((m["luecke"] + laenge) * gross)
            # Als Vieleck, nicht als dicke Linie: pygame setzt die Breite
            # schraeger Linien einseitig daneben, der dunkle Rand laege
            # dann nur auf einer Seite. Der Rand macht das X auf Sand,
            # Rauch und Feuer gleich lesbar.
            quer = pygame.Vector2(-d.y, d.x)
            for f_farbe, breit, vor in (((16, 11, 8), 1.9, 1.0), (farbe, 0.9, 0.0)):
                a2, b2 = a - d * vor, b + d * vor
                pygame.draw.polygon(s, f_farbe, [a2 + quer * breit, b2 + quer * breit,
                                                 b2 - quer * breit, a2 - quer * breit])
        # Nicht set_alpha: auf dem iPhone ein schwarzes Viereck dahinter.
        s = plattform.deckkraft(s, deck, kopie=False)
        ziel.blit(s, (int(pos[0]) - rand, int(pos[1]) - rand))


class Befinden:
    """Roter Rand, Herzschlag, dumpfe Welt - und das Medkit dagegen.

    Ein eigenes Ding und kein Teil der Spielszene, weil beide Szenen es
    brauchen und weil es **nichts entscheidet**: es liest den Lebensanteil
    und macht daraus Bild und Ton. Nimmt man es heraus, spielt sich die
    Runde genauso, sie fuehlt sich nur nach nichts an.

    Wie es zusammenhaengt:

        Leben faellt   ->  roter Schein am Rand waechst
        unter `dauerhaft_ab`  ->  er bleibt stehen und pulst
        jeder Puls     ->  Schein flackert auf, Herzschlag im Ohr,
                           alles andere wird dumpfer
        Treffer        ->  ein sofortiger Aufschlag, der verklingt
        Medkit         ->  blau, kalt, sehr klar - und danach Ruhe
    """

    def __init__(self) -> None:
        self.stoss = 0.0          # was ein Treffer gerade dazugibt
        self.puls = 0.0           # 0 bis 1, wo im Herzschlag wir stehen
        self.schlag = 0.0         # 0 bis 1, Helligkeit dieses Schlags
        self.klasse = -1          # welche Herzschlagklasse gerade gilt
        self.medkit_rest = 0.0
        self.ruhe_rest = 0.0
        self.anteil = 1.0
        # Blendung. `blend` ist, wie weiss das Bild gerade ist; `blend_rest`
        # wie lange es noch dauert. Zwei Werte, weil das Weiss hart kommt
        # und weich geht - umgekehrt waere es kein Blitz.
        self.blend = 0.0
        self.blend_rest = 0.0
        self._puffer = None

    # ---- Meldungen -----------------------------------------------------
    def treffer(self, menge: float = 1.0) -> None:
        b = K.BEFINDEN
        self.stoss = min(1.0, self.stoss + b["treffer_stoss"] * min(1.0, menge))

    def blenden(self, staerke: float) -> None:
        """Ein Blitz hat getroffen. Staerke 0 bis 1.

        Das Groessere von beidem zaehlt: zwei Blendgranaten kurz
        hintereinander sollen nicht addieren, sondern die schlimmere
        gelten lassen. Addieren hiesse, dass zwei halbe Treffer schlimmer
        waeren als ein voller, und das ergibt keinen Sinn.
        """
        b = K.BLENDEN
        staerke = max(0.0, min(1.0, staerke))
        if staerke <= 0.01:
            return
        self.blend = max(self.blend, staerke)
        self.blend_rest = max(self.blend_rest,
                              b["mindest"] + (b["dauer"] - b["mindest"])
                              * staerke)

    def medkit(self) -> None:
        m = K.MEDKIT_BLICK
        self.medkit_rest = m["dauer"]
        self.ruhe_rest = m["ruhe"]
        self.stoss = 0.0

    def zuruecksetzen(self) -> None:
        """Nach dem Wiedereinstieg faengt alles von vorn an."""
        self.stoss = 0.0
        self.puls = 0.0
        self.schlag = 0.0
        self.klasse = -1
        self.medkit_rest = 0.0
        self.ruhe_rest = 0.0
        self.blend = 0.0
        self.blend_rest = 0.0

    # ---- Ablauf --------------------------------------------------------
    @property
    def not_anteil(self) -> float:
        """0 bis 1: wie weit unter der Dauerschwelle das Leben steht."""
        b = K.BEFINDEN
        if self.anteil >= b["dauerhaft_ab"]:
            return 0.0
        return min(1.0, 1.0 - self.anteil / max(0.01, b["dauerhaft_ab"]))

    @property
    def staerke(self) -> float:
        """Wie stark der rote Schein gerade ist, 0 bis 1."""
        b = K.BEFINDEN
        if self.ruhe_rest > 0.0:
            # Nach einem Medkit ist Ruhe. Das ist der Punkt an einem
            # Medkit: es soll sich anfuehlen, als faende man wieder Luft.
            return 0.0
        grund = 0.0
        if self.anteil < b["ab"]:
            grund = min(1.0, (b["ab"] - self.anteil) / max(0.01, b["ab"]))
        atem = 1.0 + b["puls_tiefe"] * self.schlag * self.not_anteil
        return max(0.0, min(1.0, grund * atem + self.stoss))

    @property
    def dumpf(self) -> float:
        """Wie dumpf alles andere klingen soll, 0 bis 1."""
        b = K.BEFINDEN
        if self.ruhe_rest > 0.0:
            return 0.0
        # Die Daempfung folgt demselben Schlag wie der Schein. Beides
        # zusammen ist der Effekt: die Welt zieht sich im Takt zurueck.
        return min(1.0, b["dumpf_max"] * self.not_anteil
                   * (0.55 + 0.45 * self.schlag))

    def schritt(self, dt: float, anteil: float, klang=None) -> None:
        b = K.BEFINDEN
        self.anteil = max(0.0, min(1.0, anteil))
        self.stoss = max(0.0, self.stoss - b["treffer_abbau"] * dt)
        # Die Blendung klingt ab, und zwar langsamer, je laenger sie noch
        # dauert: die erste halbe Sekunde ist fast alles weiss, danach
        # wird es zuegig wieder klar.
        if self.blend_rest > 0.0:
            self.blend_rest = max(0.0, self.blend_rest - dt)
            bl = K.BLENDEN
            ganz = max(0.01, bl["mindest"] + (bl["dauer"] - bl["mindest"]))
            rest = self.blend_rest / ganz
            self.blend = min(self.blend, rest ** (1.0 / bl["abklingen"]))
        else:
            self.blend = 0.0
        self.medkit_rest = max(0.0, self.medkit_rest - dt)
        self.ruhe_rest = max(0.0, self.ruhe_rest - dt)

        not_anteil = self.not_anteil
        if not_anteil <= 0.0 or self.ruhe_rest > 0.0:
            self.puls = 0.0
            self.schlag = max(0.0, self.schlag - 4.0 * dt)
            self.klasse = -1
            return
        dauer = (b["puls_langsam"]
                 + (b["puls_schnell"] - b["puls_langsam"]) * not_anteil)
        vorher = self.puls
        self.puls = (self.puls + dt / max(0.05, dauer)) % 1.0
        # Der Schlag ist kurz und der Rest der Runde still: eine Kurve,
        # die schnell ansteigt und langsam faellt, mit `puls_schaerfe` als
        # Griff dafuer.
        self.schlag = max(0.0, 1.0 - self.puls * b["puls_schaerfe"])
        if self.puls < vorher and klang is not None:
            klasse = self._klasse()
            self.klasse = klasse
            if klasse >= 0:
                klang("herzschlag", b["klassen_laut"][klasse])

    def _klasse(self) -> int:
        """Welche der drei Herzschlagklassen gerade gilt."""
        b = K.BEFINDEN
        klasse = -1
        for i, grenze in enumerate(b["klassen"]):
            if self.anteil <= grenze:
                klasse = i
        return klasse

    # ---- Bild ----------------------------------------------------------
    def zeichnen(self, ziel, renderer=None) -> None:
        """Erst das Medkit auf das ganze Bild, dann der Rand, dann Weiss.

        Die Blendung kommt zuletzt und ueber alles - auch ueber die
        Anzeige. Sie ist nicht "ein Effekt in der Welt", sie ist das, was
        die Augen gerade noch hergeben.
        """
        if self.medkit_rest > 0.0:
            self._medkit_zeichnen(ziel)
        staerke = self.staerke
        if staerke > 0.01:
            self._rand_zeichnen(ziel, K.BEFINDEN["farbe"], staerke,
                                K.BEFINDEN["deckung_max"],
                                K.BEFINDEN["breite"], K.BEFINDEN["stufen"])

    def blendung_zeichnen(self, ziel, farbe=(255, 255, 255)) -> None:
        """Das Weiss. Getrennt, weil es ueber die Anzeige gehoert.

        `farbe` ist seit 0.32 einstellbar (Barrierefreiheit: NUR SCHWARZ).
        Staerke und Dauer bleiben dieselben - es aendert nur, wie es
        aussieht, nicht, wie lange man nichts sieht.
        """
        if self.blend <= 0.01:
            return
        b = K.BLENDEN
        d = int(255 * b["weiss"] * min(1.0, self.blend / max(0.01, b["deckend_ab"])))
        if d <= 0:
            return
        if d >= 255:
            ziel.fill(farbe)                  # ganz zu: nichts scheint durch
            return
        flaeche = pygame.Surface((K.GAME_W, K.GAME_H), pygame.SRCALPHA)
        flaeche.fill((*farbe, d))
        ziel.blit(flaeche, (0, 0))

    def _rand_zeichnen(self, ziel, farbe, staerke, deckung, breite,
                       stufen) -> None:
        s = pygame.Surface((K.GAME_W, K.GAME_H), pygame.SRCALPHA)
        breit = max(stufen, int(breite * (0.45 + 0.55 * staerke)))
        for i in range(stufen):
            d = int(deckung * staerke * (1.0 - i / stufen) ** 1.6)
            if d <= 0:
                continue
            dick = max(1, breit // stufen)
            rand = i * dick
            pygame.draw.rect(s, (*farbe, d),
                             (rand, rand, K.GAME_W - 2 * rand,
                              K.GAME_H - 2 * rand), dick)
        ziel.blit(s, (0, 0))

    def _medkit_zeichnen(self, ziel) -> None:
        """Kalt, klar und einen Augenblick lang hell.

        Der Kontrast entsteht ohne Shader: das Bild wird auf sich selbst
        addiert (also verdoppelt) und dann um einen Grauwert gesenkt.
        `out = 2*in - g` ist eine harte Kontrastkurve, und Kontrast ist
        das, was das Auge als "scharf" liest. Damit es sich einblenden
        laesst, wird das Ergebnis mit einer Deckkraft ueber das Original
        gelegt statt es zu ersetzen.
        """
        m = K.MEDKIT_BLICK
        t = self.medkit_rest / max(0.01, m["dauer"])      # 1 -> 0
        # Sanft auslaufen, nicht abschneiden.
        weich = t * t * (3.0 - 2.0 * t)
        if self._puffer is None or self._puffer.get_size() != ziel.get_size():
            self._puffer = pygame.Surface(ziel.get_size()).convert()
        puffer = self._puffer
        puffer.blit(ziel, (0, 0))
        # 1. Kontrast: verdoppeln, dann die Mitte zurueckziehen.
        puffer.blit(puffer, (0, 0), special_flags=pygame.BLEND_RGB_ADD)
        g = m["kontrast_mitte"]
        puffer.fill((g, g, g), special_flags=pygame.BLEND_RGB_SUB)
        # 2. Kaelte: mit einem kuehlen Ton multiplizieren. Der Rostton der
        #    Welt faellt dabei zusammen, das Blau bleibt stehen.
        kalt = m["kalt_ton"]
        anteil = m["kaelte"] * weich
        ton = tuple(int(255 + (c - 255) * anteil) for c in kalt)
        puffer.fill(ton, special_flags=pygame.BLEND_RGB_MULT)
        # Multiplizieren allein macht nur die hellen Stellen kuehler - die
        # dunklen bleiben, wo sie sind, und die Welt hier besteht fast nur
        # aus dunklen Stellen. Also zusaetzlich ein wenig Blau **dazu**:
        # das hebt die Schatten ins Kalte. Genau so arbeitet eine kuehle
        # Farbkorrektur auch sonst - Schatten anheben, Lichter entwaermen.
        hebung = int(m["kalt_hebung"] * anteil)
        if hebung > 0:
            puffer.fill((0, hebung // 2, hebung),
                        special_flags=pygame.BLEND_RGB_ADD)
        puffer.set_alpha(int(255 * m["kontrast"] * weich))
        ziel.blit(puffer, (0, 0))
        # 3. Der helle Anschlag, hart einsetzend und langsam ausklingend.
        rest_blitz = self.medkit_rest - (m["dauer"] - m["blitz"])
        if rest_blitz > 0.0:
            b = rest_blitz / max(0.01, m["blitz"])
            flaeche = pygame.Surface((K.GAME_W, K.GAME_H), pygame.SRCALPHA)
            flaeche.fill((*m["farbe"], int(130 * b * b)))
            ziel.blit(flaeche, (0, 0))
        # 4. Der blaue Rand - der Gegenschlag zum roten.
        self._rand_zeichnen(ziel, m["farbe"], weich, m["rand_deckung"],
                            K.BEFINDEN["breite"], K.BEFINDEN["stufen"])
