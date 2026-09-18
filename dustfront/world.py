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

    # ---- Aufbau ------------------------------------------------------
    @classmethod
    def aus_text(cls, zeilen: list[str], index: int) -> "Ebene":
        hoehe = len(zeilen)
        breite = max(len(z) for z in zeilen)
        e = cls(breite, hoehe, index)
        for ty, zeile in enumerate(zeilen):
            for tx in range(breite):
                z = zeile[tx] if tx < len(zeile) else " "
                e.setzen(tx, ty, ZEICHEN.get(z, K.BODEN))
                # gestreute Auswahl, sonst sieht man ein Muster im Boden
                e.variante[ty * breite + tx] = ((tx * 73856093) ^ (ty * 19349663)) % 4
        return e

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


class Welt:
    """Haelt die Ebenen und alle Wesen."""

    ZELLE = 48          # Rastergroesse der Nachbarschaftssuche

    def __init__(self, ebenen: list[Ebene]) -> None:
        self.ebenen = ebenen
        self.wesen: list = []
        self.neue: list = []
        self.partikel: list = []
        self._raster: dict[tuple, list] = {}
        self.zeit = 0.0
        self.held = None                 # setzt die Spielszene
        self.muendungen: list = []       # kurze Lichtblitze am Lauf

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
        """Hoehe einer Ebene in Welt-Pixeln, aus der Tabelle in config."""
        i = max(0, min(len(K.EBENEN_HOEHE) - 1, index))
        return K.EBENEN_HOEHE[i]

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
        """Weiche Abstossung, damit Gegner sich nicht ineinander schieben."""
        for a in self.nahe(wesen.pos, wesen.radius * 2, wesen.ebene):
            if a is wesen or not a.schiebt:
                continue
            d = wesen.pos - a.pos
            abstand = d.length()
            mindest = wesen.radius + a.radius
            if 0.0001 < abstand < mindest:
                schub = d / abstand * (mindest - abstand) * 0.5
                wesen.pos += schub
                a.pos -= schub

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
    return Welt([Ebene.aus_text(KARTE_E0, 0),
                 Ebene.aus_text(KARTE_E1, 1),
                 Ebene.aus_text(KARTE_E2, 2)])


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
