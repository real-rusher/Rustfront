"""
DUSTFRONT - Welt
================

Die Welt besteht aus **Ebenen**. Eine Ebene ist ein Kachelgitter mit einer
Hoehe (0 = Boden, 1 = erste Etage, 2 = zweite, und so weiter). Jedes Wesen
gehoert zu genau einer Ebene, kollidiert nur mit deren Kacheln und sieht nur
deren Nachbarn.

Das ist der Punkt, an dem die meisten Projekte spaeter neu anfangen muessen.
Hier ist es von Anfang an drin: es gibt keinen Code, der davon ausgeht, dass
es nur eine Ebene gibt. Eine weitere Etage ist ein weiterer Texteintrag in der
Kartenliste, sonst nichts.

Karten sind Text. Ein Zeichen ist eine Kachel. Damit kann man eine Etage in
einem Editor tippen, und spaeter kann ein Tiled-Importeur genau dieselbe
Struktur erzeugen, ohne dass der Spielcode es merkt.
"""

from __future__ import annotations

import math

import pygame

from . import config as K

# Zeichen -> Kachel. Alles, was hier nicht steht, wird zu Boden.
ZEICHEN = {
    " ": K.LEER,
    ".": K.BODEN,
    ",": K.GITTER,
    "#": K.WAND,
    "X": K.KISTE,
    "<": K.TREPPE_RUNTER,
    ">": K.TREPPE_HOCH,
    "o": K.LUKE,
}


class Ebene:
    """Ein Kachelgitter auf einer Hoehe."""

    def __init__(self, breite: int, hoehe: int, index: int) -> None:
        self.breite, self.hoehe, self.index = breite, hoehe, index
        self.kacheln = [K.LEER] * (breite * hoehe)
        self.variante = [0] * (breite * hoehe)     # fuer abwechselnde Bodenbilder
        self.dekale = pygame.Surface((breite * K.TILE, hoehe * K.TILE), pygame.SRCALPHA)
        # Benannte Punkte aus der Karte: "start", "rampe", "steuerstand", ...
        # Damit muss kein Code mehr wissen, wo etwas liegt - es steht im Text.
        self.marken: dict[str, pygame.Vector2] = {}

    # ---- Aufbau ------------------------------------------------------
    @classmethod
    def aus_text(cls, zeilen: list[str], index: int,
                 zeichen: dict | None = None) -> "Ebene":
        """Baut eine Ebene aus Textzeilen.

        `zeichen` waehlt die Kachelfamilie: Wasteland oder Rumpf. Ohne Angabe
        bleibt es bei der alten Tabelle, damit bestehende Aufrufe unveraendert
        weiterlaufen.
        """
        tabelle = ZEICHEN if zeichen is None else zeichen
        grund = tabelle.get(".", K.BODEN)
        hoehe = len(zeilen)
        breite = max(len(z) for z in zeilen)
        e = cls(breite, hoehe, index)
        for ty, zeile in enumerate(zeilen):
            for tx in range(breite):
                z = zeile[tx] if tx < len(zeile) else " "
                marke = K.MARKEN.get(z)
                if marke is not None:
                    name, kachel = marke
                    e.setzen(tx, ty, grund if kachel is None else kachel)
                    e.marken[name] = pygame.Vector2(tx * K.TILE + K.TILE / 2,
                                                    ty * K.TILE + K.TILE / 2)
                else:
                    e.setzen(tx, ty, tabelle.get(z, grund))
                # gestreute Auswahl, sonst sieht man ein Muster im Boden
                e.variante[ty * breite + tx] = ((tx * 73856093) ^ (ty * 19349663)) % 4
        return e

    def stationen(self) -> dict[str, pygame.Vector2]:
        """Alle Stationskacheln dieser Ebene, Name -> Mitte der Kachel."""
        gefunden = {}
        for ty in range(self.hoehe):
            for tx in range(self.breite):
                st = self.daten(tx, ty).get("station")
                if st:
                    gefunden[st] = pygame.Vector2(tx * K.TILE + K.TILE / 2,
                                                  ty * K.TILE + K.TILE / 2)
        return gefunden

    def setzen(self, tx: int, ty: int, kachel: int) -> None:
        if 0 <= tx < self.breite and 0 <= ty < self.hoehe:
            self.kacheln[ty * self.breite + tx] = kachel

    # ---- Abfragen ----------------------------------------------------
    def kachel(self, tx: int, ty: int) -> int:
        if 0 <= tx < self.breite and 0 <= ty < self.hoehe:
            return self.kacheln[ty * self.breite + tx]
        return K.LEER

    def daten(self, tx: int, ty: int) -> dict:
        return K.KACHELN[self.kachel(tx, ty)]

    def fest(self, tx: int, ty: int) -> bool:
        return K.KACHELN[self.kachel(tx, ty)]["fest"]

    def sichtdicht(self, tx: int, ty: int) -> bool:
        return K.KACHELN[self.kachel(tx, ty)]["sicht"]

    def fest_an(self, x: float, y: float) -> bool:
        return self.fest(int(x // K.TILE), int(y // K.TILE))

    def loch(self, tx: int, ty: int) -> bool:
        return K.KACHELN[self.kachel(tx, ty)].get("loch", False)

    def begehbar(self, tx: int, ty: int) -> bool:
        return not self.fest(tx, ty) and self.kachel(tx, ty) != K.LEER

    @property
    def pixel_breite(self) -> int:
        return self.breite * K.TILE

    @property
    def pixel_hoehe(self) -> int:
        return self.hoehe * K.TILE

    def dekal(self, bild: pygame.Surface, x: float, y: float) -> None:
        """Brandfleck, Blut, Einschlag. Bleibt liegen, kostet nichts."""
        self.dekale.blit(bild, (x - bild.get_width() / 2, y - bild.get_height() / 2))


def hoehen_staffel(decks: int, mit_boden: bool = True) -> list[float]:
    """Hoehentabelle fuer einen Rumpf mit beliebig vielen Decks.

    Die von Hand gesetzte Tabelle `EBENEN_HOEHE` ist keine willkuerliche
    Liste: sie kodiert einen gleichbleibenden Wahrnehmungsschritt. Steht man
    oben, erscheint jedes Deck darunter genau `HOEHEN["schritt"]` so gross
    wie das darueber - nur der Boden faellt bewusst aus der Reihe und sitzt
    tiefer, damit er sich von den Decks absetzt.

    Mit der Perspektive `k = brennweite / (brennweite + dz)` laesst sich das
    umkehren: aus der gewuenschten scheinbaren Groesse folgt die Hoehe. Damit
    ist die Staffel fuer *jede* Deckzahl erzeugbar, und fuer vier Decks kommt
    auf den Pixel das heraus, was bisher von Hand dastand:

        >>> [round(h) for h in hoehen_staffel(4)]
        [0, 118, 181, 237, 287]

    Zurueck kommt die Tabelle von unten nach oben, also so, wie die
    Ebenenindizes laufen: Eintrag 0 ist der Boden, Eintrag 1 das unterste
    Deck.
    """
    f = K.PERSPEKTIVE["brennweite"]
    schritt = K.HOEHEN["schritt"]
    decks = max(1, min(int(decks), K.HOEHEN["decks_hoechstens"]))

    # Scheinbare Groesse je Ebene, vom obersten Deck abwaerts.
    groessen = [1.0]
    for _ in range(decks - 1):
        groessen.append(groessen[-1] * schritt)
    if mit_boden:
        groessen.append(groessen[-1] * K.HOEHEN["boden_schritt"])

    tiefen = [f / g - f for g in groessen]        # dz vom obersten Deck aus
    unten = tiefen[-1]
    return [unten - dz for dz in reversed(tiefen)]


class Welt:
    """Haelt die Ebenen und alle Wesen."""

    ZELLE = 48          # Rastergroesse der Nachbarschaftssuche

    def __init__(self, ebenen: list[Ebene], staffel: list[float] | None = None,
                 name: str = "") -> None:
        self.ebenen = ebenen
        self.wesen: list = []
        self.neue: list = []
        self.partikel: list = []
        self._raster: dict[tuple, list] = {}
        self.zeit = 0.0
        self.held = None                 # setzt die Spielszene
        self.muendungen: list = []       # kurze Lichtblitze am Lauf
        self.name = name
        # Eigene Hoehenstaffel. None heisst: die Tabelle aus config. Ein
        # Rumpf bekommt hier seine eigene, damit ein Warhound mit drei Decks
        # und ein Imperator mit zehn beide richtig aussehen (siehe
        # hoehen_staffel unten).
        self.staffel = staffel
        # Wo dieser Rumpf in der Welt steht. Fuer den Boden und fuer jede
        # heutige Karte bleibt das (0,0). Ein laufender Wandler traegt hier
        # seine Position - als **Kommazahl**, nie als Kachelmass, damit sich
        # kein Gitter je gegen sein eigenes Raster verschiebt.
        self.versatz = pygame.Vector2()

    # ---- Aus einer Kartendatei ----------------------------------------
    @classmethod
    def aus_karte(cls, karte, staffel: list[float] | None = None) -> "Welt":
        """Baut eine Welt aus einer gelesenen `karten.Karte`."""
        zeichen = karte.zeichen
        ebenen = [Ebene.aus_text(block, idx, zeichen)
                  for idx, block in enumerate(karte.bloecke)]
        if staffel is None and karte.grund == "deck":
            # Ein Rumpf bekommt seine Staffel aus seiner Deckzahl. Ein Ort
            # behaelt die Tabelle aus config, damit sich an bestehenden
            # Karten nichts aendert.
            staffel = hoehen_staffel(len(ebenen), mit_boden=False)
        return cls(ebenen, staffel, karte.name)

    @classmethod
    def aus_datei(cls, name: str, staffel: list[float] | None = None) -> "Welt":
        """Liest `karten/<name>.txt` und baut die Welt daraus."""
        from .karten import lesen
        return cls.aus_karte(lesen(name), staffel)

    def marke(self, name: str, ebene: int | None = None):
        """Position einer Marke, oder None.

        Ohne Ebenenangabe wird von unten nach oben gesucht und die erste
        Fundstelle genommen. Zurueck kommt `(ebene, Vector2)`.
        """
        if ebene is not None:
            p = self.ebene(ebene).marken.get(name)
            return None if p is None else (ebene, pygame.Vector2(p))
        for e in self.ebenen:
            p = e.marken.get(name)
            if p is not None:
                return e.index, pygame.Vector2(p)
        return None

    def marken(self) -> dict[str, tuple]:
        """Alle Marken aller Ebenen, Name -> (ebene, Vector2)."""
        alle = {}
        for e in self.ebenen:
            for name, p in e.marken.items():
                alle.setdefault(name, (e.index, pygame.Vector2(p)))
        return alle

    def startpunkt(self, ersatz_ebene: int = 0):
        """Wo der Spieler anfaengt: die Marke `S`, sonst die Mitte.

        Kein Zufallspunkt mehr - wer eine Karte baut, bestimmt, wo man
        aufwacht.
        """
        treffer = self.marke("start")
        if treffer is not None:
            return treffer
        e = self.ebene(ersatz_ebene)
        return ersatz_ebene, pygame.Vector2(e.pixel_breite / 2, e.pixel_hoehe / 2)

    # ---- Rueckmeldungen an die Spielszene ------------------------------
    # Standardmaessig passiert nichts. Die Szene haengt sich hier ein, damit
    # Wesen Kameraruckeln oder Dekale ausloesen koennen, ohne den Renderer zu
    # kennen.
    def ruckeln(self, kraft: float) -> None:
        pass

    def kurz_langsam(self, sekunden: float) -> None:
        pass

    def blutfleck(self, pos, ebene: int, radius: float) -> None:
        pass

    def klang(self, name: str, lautstaerke: float = 1.0) -> None:
        pass

    def brandfleck(self, pos, ebene: int, radius: float) -> None:
        pass

    def muendung(self, pos, winkel: float, ebene: int) -> None:
        self.muendungen.append([pygame.Vector2(pos), winkel, ebene, 0.055])

    # ---- Bestand -----------------------------------------------------
    def dazu(self, w):
        self.neue.append(w)
        w.welt = self
        return w

    def ebene(self, index: int) -> Ebene:
        return self.ebenen[max(0, min(len(self.ebenen) - 1, index))]

    def hoehe(self, index: int) -> float:
        """Hoehe einer Ebene in Welt-Pixeln.

        Die **eine** Stelle, an der eine Ebenenhoehe herkommt. Renderer,
        Sturz und Blickhoehe rufen alle hierher, nie die Tabelle direkt -
        deshalb genuegt eine eigene Staffel an dieser Welt, damit ein Rumpf
        beliebig viele Decks haben kann.
        """
        tabelle = self.staffel if self.staffel else K.EBENEN_HOEHE
        i = max(0, min(len(tabelle) - 1, index))
        return tabelle[i]

    def abstand(self, oben: int, unten: int) -> float:
        return max(1.0, self.hoehe(oben) - self.hoehe(unten))

    def schritt(self, dt: float) -> None:
        self.zeit += dt
        if self.neue:
            self.wesen.extend(self.neue)
            self.neue.clear()
        self._raster_bauen()
        for w in self.wesen:
            if w.lebt:
                w.schritt(dt)
        for p in self.partikel:
            p.schritt(dt)
        if self.muendungen:
            for m in self.muendungen:
                m[3] -= dt
            self.muendungen = [m for m in self.muendungen if m[3] > 0]
        if any(not w.lebt for w in self.wesen):
            self.wesen = [w for w in self.wesen if w.lebt]
        if any(not p.lebt for p in self.partikel):
            self.partikel = [p for p in self.partikel if p.lebt]

    # ---- Nachbarschaft ------------------------------------------------
    def _raster_bauen(self) -> None:
        self._raster.clear()
        for w in self.wesen:
            if not w.lebt or w.radius <= 0 or not w.trefferbar:
                continue
            k = (int(w.pos.x // self.ZELLE), int(w.pos.y // self.ZELLE), w.ebene)
            self._raster.setdefault(k, []).append(w)

    def nahe(self, pos: pygame.Vector2, radius: float, ebene: int):
        """Alle Wesen der Ebene, deren Zelle den Kreis beruehrt."""
        r = int(radius // self.ZELLE) + 1
        cx, cy = int(pos.x // self.ZELLE), int(pos.y // self.ZELLE)
        for gy in range(cy - r, cy + r + 1):
            for gx in range(cx - r, cx + r + 1):
                for w in self._raster.get((gx, gy, ebene), ()):
                    yield w

    def treffer(self, pos: pygame.Vector2, radius: float, ebene: int, feind_von: str):
        """Naechstes lebendes Ziel einer anderen Fraktion im Kreis."""
        bestes, beste_d = None, 1e18
        for w in self.nahe(pos, radius + 24, ebene):
            if not w.lebt or w.fraktion == feind_von or w.leben <= 0:
                continue
            d = pos.distance_squared_to(w.pos)
            grenze = (radius + w.radius) ** 2
            if d < grenze and d < beste_d:
                bestes, beste_d = w, d
        return bestes

    # ---- Kollision ----------------------------------------------------
    def frei(self, pos: pygame.Vector2, radius: float, ebene: int,
             loch_fest: bool = False) -> bool:
        """loch_fest: Loecher zaehlen als Wand. Fuer alles, was nicht fallen soll."""
        e = self.ebene(ebene)
        t0x = int((pos.x - radius) // K.TILE)
        t1x = int((pos.x + radius) // K.TILE)
        t0y = int((pos.y - radius) // K.TILE)
        t1y = int((pos.y + radius) // K.TILE)
        for ty in range(t0y, t1y + 1):
            for tx in range(t0x, t1x + 1):
                if not (e.fest(tx, ty) or (loch_fest and e.loch(tx, ty))):
                    continue
                nx = max(tx * K.TILE, min(pos.x, tx * K.TILE + K.TILE))
                ny = max(ty * K.TILE, min(pos.y, ty * K.TILE + K.TILE))
                if (pos.x - nx) ** 2 + (pos.y - ny) ** 2 < radius * radius:
                    return False
        return True

    def bewegen(self, wesen, dx: float, dy: float) -> tuple[bool, bool]:
        """Achsenweise schieben. Gibt zurueck, ob an x bzw. y angestossen wurde.

        Getrennt nach Achsen, damit man an einer Wand entlanggleitet statt
        kleben zu bleiben. Grosse Schritte werden unterteilt, damit nichts
        durch duenne Waende rutscht.
        """
        pos, r, eb = wesen.pos, wesen.radius, wesen.ebene
        # Auch im Sturz zaehlen die Waende der Ebene, auf die es hinuntergeht:
        # man gleitet im Flug an ihnen entlang statt hindurchzufliegen. Nur so
        # steht die Figur beim Aufsetzen schon auf freiem Grund und muss nicht
        # im letzten Bild noch zur Seite gesetzt werden.
        lf = not getattr(wesen, "faellt", False)
        stoss_x = stoss_y = False
        schritte = max(1, int(max(abs(dx), abs(dy)) / (r * 0.75)) + 1)
        sx, sy = dx / schritte, dy / schritte
        for _ in range(schritte):
            if sx:
                pos.x += sx
                if not self.frei(pos, r, eb, lf):
                    pos.x -= sx
                    stoss_x = True
                    sx = 0.0
            if sy:
                pos.y += sy
                if not self.frei(pos, r, eb, lf):
                    pos.y -= sy
                    stoss_y = True
                    sy = 0.0
            if not sx and not sy:
                break
        return stoss_x, stoss_y

    def auseinander(self, wesen) -> None:
        """Weiche Abstossung, damit Gegner sich nicht ineinander schieben.

        Geschoben wird nur, wenn das Ziel frei ist. Sonst drueckt eine Gruppe
        Gegner den Spieler in die naechste Wand.
        """
        for a in self.nahe(wesen.pos, wesen.radius * 2, wesen.ebene):
            if a is wesen or not a.schiebt:
                continue
            d = wesen.pos - a.pos
            abstand = d.length()
            mindest = wesen.radius + a.radius
            if 0.0001 < abstand < mindest:
                schub = d / abstand * (mindest - abstand) * 0.5
                if self.frei(wesen.pos + schub, wesen.radius, wesen.ebene,
                             not getattr(wesen, "faellt", False)):
                    wesen.pos += schub
                if self.frei(a.pos - schub, a.radius, a.ebene,
                             not getattr(a, "faellt", False)):
                    a.pos -= schub

    def befreien(self, wesen) -> bool:
        """Holt ein Wesen aus der Wand, falls es doch einmal darin steckt.

        Passiert durch Rueckstoss, Gedraenge oder einen ungluecklichen
        Landeplatz. Gesucht wird der naechste freie Punkt in wachsenden
        Ringen, damit der Ausweg so kurz wie moeglich bleibt.
        """
        if getattr(wesen, "sturz_rest", 0.0) > 0:
            return False          # in der Luft steckt niemand in einer Wand
        lf = not getattr(wesen, "faellt", False)
        if self.frei(wesen.pos, wesen.radius, wesen.ebene, lf):
            return False
        for r in (3.0, 6.0, 10.0, 15.0, 21.0, 29.0, 40.0, 54.0):
            for i in range(12):
                a = math.tau * i / 12 + r * 0.7
                p = wesen.pos + pygame.Vector2(math.cos(a), math.sin(a)) * r
                if self.frei(p, wesen.radius, wesen.ebene, lf):
                    wesen.pos.update(p)
                    wesen.vorher.update(p)
                    wesen.tempo *= 0.4
                    return True
        return False

    def strahl(self, von, richtung, laenge: float, ebene: int):
        """Erster Punkt auf der Linie, an dem etwas im Weg steht."""
        e = self.ebene(ebene)
        schritte = max(1, int(laenge / (K.TILE * 0.4)))
        for i in range(1, schritte + 1):
            p = von + richtung * (laenge * i / schritte)
            if e.sichtdicht(int(p.x // K.TILE), int(p.y // K.TILE)):
                return von + richtung * (laenge * (i - 1) / schritte)
        return von + richtung * laenge

    def boden_unter(self, pos, ebene: int) -> int:
        """Erste Ebene unterhalb, die an dieser Stelle wirklich Boden hat."""
        tx, ty = int(pos.x // K.TILE), int(pos.y // K.TILE)
        ziel = ebene - 1
        while ziel > 0 and self.ebene(ziel).loch(tx, ty):
            ziel -= 1
        return max(0, ziel)

    def sicht_frei(self, von: pygame.Vector2, nach: pygame.Vector2, ebene: int) -> bool:
        """Grober Sichttest entlang der Linie, Schrittweite halbe Kachel."""
        e = self.ebene(ebene)
        d = nach - von
        laenge = d.length()
        if laenge < 1.0:
            return True
        schritte = int(laenge / (K.TILE * 0.5)) + 1
        for i in range(1, schritte + 1):
            p = von + d * (i / schritte)
            if e.sichtdicht(int(p.x // K.TILE), int(p.y // K.TILE)):
                return False
        return True

    # ---- Ebenenwechsel --------------------------------------------------
    def loch_unter(self, wesen) -> bool:
        """Steht das Wesen ueber einem Loch, unter dem es eine Ebene gibt?"""
        if wesen.ebene <= 0:
            return False
        e = self.ebene(wesen.ebene)
        return e.loch(int(wesen.pos.x // K.TILE), int(wesen.pos.y // K.TILE))

    def landeplatz(self, pos: pygame.Vector2, radius: float, ebene: int):
        """Naechste freie Stelle auf der Zielebene, falls direkt darunter
        etwas im Weg steht."""
        if self.frei(pos, radius, ebene):
            return pygame.Vector2(pos)
        for r in (K.TILE * 0.5, K.TILE, K.TILE * 1.5):
            for i in range(12):
                a = math.tau * i / 12
                p = pos + pygame.Vector2(math.cos(a), math.sin(a)) * r
                if self.frei(p, radius, ebene):
                    return p
        return pygame.Vector2(pos)

    def treppe_unter(self, wesen) -> int | None:
        """Zielebene, wenn das Wesen auf einer Treppe oder Luke steht."""
        e = self.ebene(wesen.ebene)
        tx, ty = int(wesen.pos.x // K.TILE), int(wesen.pos.y // K.TILE)
        daten = e.daten(tx, ty)
        rel = daten.get("treppe")
        if rel is None:
            return None
        ziel = wesen.ebene + rel
        if 0 <= ziel < len(self.ebenen):
            return ziel
        return None

    def ebene_wechseln(self, wesen, ziel: int) -> bool:
        """Wechselt die Ebene, wenn der Platz dort frei ist."""
        alt = wesen.ebene
        wesen.ebene = ziel
        if self.frei(wesen.pos, wesen.radius, ziel):
            wesen.vorher.update(wesen.pos)
            return True
        wesen.ebene = alt
        return False


# ══════════════════════════════════════════════════════════════════
# Testkarte
# ══════════════════════════════════════════════════════════════════

# Ebene 0 ist eine offene Halle: Saeulen und kurze Mauerstuecke als Deckung,
# nichts davon schliesst einen Bereich ab. Ebene 1 ist ein Ring aus Laufstegen
# mit einer Plattform in der Mitte. Die Leerzeichen sind Loecher, durch die man
# die Halle darunter sieht.
#
# Beide Etagen sind mit einer Flutfuellung geprueft: von der Treppe aus ist
# jede begehbare Kachel erreichbar, und jeder Landepunkt eines Uebergangs ist
# auf der Zielebene frei.

KARTE_E0 = [
    "############################################",
    "#..........................................#",
    "#.................,,,,,,,,.................#",
    "#.................,,,,,,,,.................#",
    "#.....##......##......##......##......##...#",
    "#.....##......##......##......##......##...#",
    "#........X........................X........#",
    "#....................#.....................#",
    "#.........#######....#.....#######.........#",
    "#..,,,,,.............#..............,,,,,..#",
    "#..,,,,,.............#..............,,,,,..#",
    "#..,,,,,..........X............X....,,,,,..#",
    "#..,,,,,....X.........>..X..........,,,,,..#",
    "#..,,,,,.............#..............,,,,,..#",
    "#..,,,,,.............#..............,,,,,..#",
    "#.........#######....#.....#######.........#",
    "#....................#.....................#",
    "#........X........................X........#",
    "#..........................................#",
    "#.....##......##......##......##......##...#",
    "#.....##......##......##......##......##...#",
    "#..........................................#",
    "#..........................................#",
    "############################################",
]

KARTE_E1 = [
    "############################################",
    "#..........................................#",
    "#.....X..............................X..o..#",
    "#..........................................#",
    "#...                ....                ...#",
    "#...                ..X.                ...#",
    "#.X.                ....                ...#",
    "#...                ....                ...#",
    "#...                ....                ...#",
    "#...              ........              ...#",
    "#...              .,,,,,,.              ...#",
    "#..................,,,,,,........>.........#",
    "#..................,,,<,,..................#",
    "#...              .,,,,,,.              ...#",
    "#...              ........              ...#",
    "#...                ....                ...#",
    "#...                ....                ...#",
    "#...                ....                .X.#",
    "#...                ..X.                ...#",
    "#...                ....                ...#",
    "#..........................................#",
    "#.....X..............................X.....#",
    "#..........................................#",
    "############################################",
]


KARTE_E2 = [
    "############################################",
    "#                                          #",
    "#                                          #",
    "#                                          #",
    "#               ......                     #",
    "#               ......                     #",
    "# ......        ..X...                     #",
    "# ......        ......                     #",
    "# ..X...        ......        ............ #",
    "# ......        ......        .,,,,,,,,,,. #",
    "# .............................,,,,,,,X,,. #",
    "# .............................,,<,,,,,,,. #",
    "# .............................,,,,,,,,,,. #",
    "# ......        ......        .,,,,X,,,,,. #",
    "# ......        ......        .,,,,,,,,,,. #",
    "# ...X..        ......        ............ #",
    "# ......        ......                     #",
    "# ......        ..X...                     #",
    "#               ......                     #",
    "#               ......                     #",
    "#                                          #",
    "#                                          #",
    "#                                          #",
    "############################################",
]


def testkarte() -> Welt:
    """Die eingebaute Karte. Bleibt als Rueckfallebene bestehen.

    Seit die Karten aus Dateien kommen, ist sie nicht mehr die Karte,
    sondern die Versicherung: fehlt der Ordner `karten/` oder ist eine
    Datei kaputt, startet das Spiel trotzdem.
    """
    return Welt([Ebene.aus_text(KARTE_E0, 0),
                 Ebene.aus_text(KARTE_E1, 1),
                 Ebene.aus_text(KARTE_E2, 2)])


def karte_laden(name: str | None = None) -> Welt:
    """Laedt eine Karte aus `karten/`, mit Rueckfall auf die eingebaute.

    Ein Spiel darf an einer fehlenden Datei nicht sterben. Faellt das Laden
    aus, kommt `testkarte()` und der Grund steht auf der Konsole - sichtbar
    genug, dass es auffaellt, harmlos genug, dass man weiterspielen kann.
    """
    from .karten import KartenFehler
    try:
        return Welt.aus_datei(name or K.KARTEN["start"])
    except (KartenFehler, OSError) as fehler:
        print("Karte %r nicht ladbar (%s) - nehme die eingebaute."
              % (name or K.KARTEN["start"], fehler))
        return testkarte()


def freier_punkt(welt: Welt, ebene: int, rnd, weg_von=None, mindest=0.0):
    """Sucht eine begehbare Stelle, optional mit Abstand zu einem Punkt."""
    e = welt.ebene(ebene)
    for _ in range(400):
        tx = rnd.randrange(1, e.breite - 1)
        ty = rnd.randrange(1, e.hoehe - 1)
        if not e.begehbar(tx, ty):
            continue
        p = pygame.Vector2(tx * K.TILE + K.TILE / 2, ty * K.TILE + K.TILE / 2)
        if weg_von is not None and p.distance_to(weg_von) < mindest:
            continue
        if welt.frei(p, 12, ebene):
            return p
    return pygame.Vector2(e.pixel_breite / 2, e.pixel_hoehe / 2)
