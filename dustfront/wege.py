"""
DUSTFRONT - Wege zwischen den Ebenen
====================================

Wie ein Gegner von einer Ebene auf eine andere kommt.

Bis 0.26 lief ein Gegner, dessen Ziel eine Ebene hoeher stand, einfach
auf die Stelle unter diesem Ziel zu - und wechselte nur, wenn er dabei
zufaellig auf eine Treppe trat. Auf der Testkarte klappte das gelegentlich,
weil die Treppen nahe der Mitte liegen. Auf STAUBTAL fast nie: die Rampen
liegen am Rand der Plateaus, und wer unter einem Plateau steht, steht vor
einer Felswand.

Hier wird der Weg deshalb **gesucht**, und zwar in zwei Stufen:

1. **Gebiete.** Jede Ebene zerfaellt in zusammenhaengende Stuecke Boden.
   Auf der Testkarte ist jede Ebene eines; auf STAUBTAL ist der Sand eines
   und jedes der drei Plateaus ein eigenes. Treppen verbinden Gebiete, und
   das ergibt einen kleinen Graphen - ein paar Dutzend Knoten. Darin wird
   gesucht, welche Treppe als naechste zu nehmen ist. Nur so kommt ein
   Gegner von einem Plateau auf ein anderes: hinunter, quer ueber den
   Sand, wieder hinauf. Die naechstgelegene Treppe waere dort oft die
   falsche.
2. **Abstandsfelder.** Fuer jede Treppe einmal ausgerechnet, wie weit jede
   Kachel ihrer Ebene von ihr entfernt ist - zu Fuss, um Waende herum.
   Ein Gegner folgt dem Feld bergab und kommt damit auch um ein Plateau
   von 32 mal 19 Kacheln herum, an dem das Ausweichen allein haengen
   bleibt.

Die Karten aendern sich nicht, also wird das beim Laden einmal gerechnet
und nie wieder. Gemessen auf STAUBTAL: siehe tests/test_spiel.py.

Dazu der Weg zu einem Spieler **auf derselben Ebene**, wenn der gerade
Weg versperrt ist - durch eine Plateauwand, oder durch Loecher wie auf
Ebene 2 der Testkarte. Das Feld dafuer haengt an der Kachel, auf der der
Spieler steht, und wird geteilt und gemerkt (`feld_zu`). Ist der gerade
Weg frei, wird es gar nicht erst gebraucht. Die Haengerwache in
mehrspieler.py bleibt als letzter Ausweg.
"""

from __future__ import annotations

from collections import deque

import pygame

from . import config as K

# Acht Richtungen. Diagonal nur, wenn beide Nachbarn frei sind - sonst
# schnitte ein Gegner die Ecke einer Wand und bliebe daran haengen.
_NACHBARN = ((1, 0), (-1, 0), (0, 1), (0, -1),
             (1, 1), (1, -1), (-1, 1), (-1, -1))


class Wegenetz:
    """Gebiete, Treppen und Abstandsfelder einer Welt. Einmal gerechnet."""

    # So viele Felder zu Spielerstellen werden gemerkt. Vier Spieler auf
    # je ein paar Kacheln Bewegung - mehr braucht es nicht, und jedes
    # Feld ist auf STAUBTAL 9600 Zahlen gross.
    _FELDER_ZIEL = 24

    def __init__(self, welt) -> None:
        self.welt = welt
        self.ebenen = len(welt.ebenen)
        self.breite = [e.breite for e in welt.ebenen]
        self.hoehe = [e.hoehe for e in welt.ebenen]
        # begehbar[ebene][index]: kann ein Gegner hier stehen? Loecher
        # zaehlen als Wand - Gegner fallen nicht (Wesen.faellt ist aus).
        self.begehbar = []
        for e in welt.ebenen:
            feld = bytearray(e.breite * e.hoehe)
            for ty in range(e.hoehe):
                for tx in range(e.breite):
                    if e.begehbar(tx, ty) and not e.loch(tx, ty):
                        feld[ty * e.breite + tx] = 1
            self.begehbar.append(feld)
        self.gebiet = [self._gebiete(i) for i in range(self.ebenen)]
        # Treppen: (ebene, tx, ty, ziel_ebene)
        self.treppen = []
        for i, e in enumerate(welt.ebenen):
            for ty in range(e.hoehe):
                for tx in range(e.breite):
                    rel = e.daten(tx, ty).get("treppe")
                    if rel is None:
                        continue
                    ziel = i + rel
                    if not 0 <= ziel < self.ebenen:
                        continue
                    if not self._frei(ziel, tx, ty):
                        continue      # oben kein Boden: keine Verbindung
                    self.treppen.append((i, tx, ty, ziel))
        # Graph der Gebiete: Knoten (ebene, gebiet) -> [(nachbar, treppe)]
        self.kanten: dict[tuple, list] = {}
        for nr, (i, tx, ty, ziel) in enumerate(self.treppen):
            von = (i, self.gebiet[i][ty * self.breite[i] + tx])
            nach = (ziel, self.gebiet[ziel][ty * self.breite[ziel] + tx])
            if von[1] < 0 or nach[1] < 0:
                continue
            self.kanten.setdefault(von, []).append((nach, nr))
        self._felder: dict[int, list] = {}
        for nr in range(len(self.treppen)):
            self._feld(nr)
        self._zielfelder: dict[tuple, list] = {}
        self._letztes_bild = -1

    # ---- Grundlagen -----------------------------------------------------
    def _frei(self, ebene: int, tx: int, ty: int) -> bool:
        if not (0 <= tx < self.breite[ebene] and 0 <= ty < self.hoehe[ebene]):
            return False
        return bool(self.begehbar[ebene][ty * self.breite[ebene] + tx])

    def kachel(self, pos) -> tuple[int, int]:
        return int(pos.x // K.TILE), int(pos.y // K.TILE)

    def _gebiete(self, ebene: int) -> list:
        """Zusammenhaengende Stuecke Boden, als Nummer je Kachel (-1: keins)."""
        b, h = self.breite[ebene], self.hoehe[ebene]
        frei = self.begehbar[ebene]
        nummer = [-1] * (b * h)
        naechste = 0
        for start in range(b * h):
            if not frei[start] or nummer[start] >= 0:
                continue
            nummer[start] = naechste
            offen = deque([start])
            while offen:
                i = offen.popleft()
                x, y = i % b, i // b
                for dx, dy in _NACHBARN[:4]:
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < b and 0 <= ny < h:
                        j = ny * b + nx
                        if frei[j] and nummer[j] < 0:
                            nummer[j] = naechste
                            offen.append(j)
            naechste += 1
        return nummer

    def gebiet_bei(self, ebene: int, pos) -> int:
        tx, ty = self.kachel(pos)
        if not (0 <= tx < self.breite[ebene] and 0 <= ty < self.hoehe[ebene]):
            return -1
        return self.gebiet[ebene][ty * self.breite[ebene] + tx]

    def _feld(self, nr: int) -> list:
        """Wie weit jede Kachel der Ebene zu Fuss von Treppe `nr` entfernt ist."""
        if nr in self._felder:
            return self._felder[nr]
        ebene, sx, sy, _ = self.treppen[nr]
        b, h = self.breite[ebene], self.hoehe[ebene]
        frei = self.begehbar[ebene]
        weit = [-1] * (b * h)
        start = sy * b + sx
        weit[start] = 0
        offen = deque([start])
        while offen:
            i = offen.popleft()
            x, y = i % b, i // b
            for dx, dy in _NACHBARN:
                nx, ny = x + dx, y + dy
                if not (0 <= nx < b and 0 <= ny < h):
                    continue
                j = ny * b + nx
                if not frei[j] or weit[j] >= 0:
                    continue
                if dx and dy and not (frei[y * b + nx] and frei[ny * b + x]):
                    continue
                weit[j] = weit[i] + 1
                offen.append(j)
        self._felder[nr] = weit
        return weit

    # ---- Fragen --------------------------------------------------------
    def braucht_weg(self, ebene: int, pos, ziel_ebene: int, ziel_pos) -> bool:
        """Kommt man nur ueber eine Treppe hin?

        Ja, wenn das Ziel auf einer anderen Ebene steht - oder auf
        derselben, aber in einem anderen Gebiet (von einem Plateau auf ein
        anderes).
        """
        if ebene != ziel_ebene:
            return True
        a = self.gebiet_bei(ebene, pos)
        z = self.gebiet_bei(ziel_ebene, ziel_pos)
        return a >= 0 and z >= 0 and a != z

    def naechste_treppe(self, ebene: int, pos, ziel_ebene: int, ziel_pos):
        """Welche Treppe als naechste zu nehmen ist, oder None.

        Breitensuche im Graphen der Gebiete - der hat ein paar Dutzend
        Knoten, das kostet nichts.
        """
        start = (ebene, self.gebiet_bei(ebene, pos))
        ziel = (ziel_ebene, self.gebiet_bei(ziel_ebene, ziel_pos))
        if start[1] < 0 or ziel[1] < 0 or start == ziel:
            return None
        erste = {start: None}
        offen = deque([start])
        while offen:
            knoten = offen.popleft()
            if knoten == ziel:
                break
            for nachbar, nr in self.kanten.get(knoten, ()):
                if nachbar in erste:
                    continue
                erste[nachbar] = erste[knoten] if erste[knoten] is not None else nr
                offen.append(nachbar)
        return erste.get(ziel)

    # ---- Auf derselben Ebene ------------------------------------------
    def gerade_frei(self, ebene: int, von, nach, radius: float = 8.0) -> bool:
        """Kommt man geradewegs hin, ohne Wand und ohne Loch dazwischen?

        Halbe Kachelschritte, und an jedem Punkt auch seitlich um den
        Radius versetzt - sonst schrammt der Gegner an einer Ecke entlang,
        die die Mittellinie gerade noch verfehlt.
        """
        d = nach - von
        laenge = d.length()
        if laenge < 1.0:
            return True
        quer = pygame.Vector2(-d.y, d.x) / laenge * radius
        schritte = int(laenge / (K.TILE * 0.5)) + 1
        b, h = self.breite[ebene], self.hoehe[ebene]
        frei = self.begehbar[ebene]
        for i in range(1, schritte + 1):
            p = von + d * (i / schritte)
            for q in (p, p + quer, p - quer):
                tx, ty = int(q.x // K.TILE), int(q.y // K.TILE)
                if not (0 <= tx < b and 0 <= ty < h) or not frei[ty * b + tx]:
                    return False
        return True

    def feld_zu(self, ebene: int, pos) -> tuple:
        """Abstandsfeld zu einer Stelle auf einer Ebene. Gemerkt.

        Alle Gegner, die denselben Spieler jagen, teilen sich ein Feld.
        Neu gerechnet wird nur, wenn der Spieler auf eine andere Kachel
        tritt - und davon hoechstens die letzten `_FELDER_ZIEL` gemerkt.
        Gemessen: rund 10 ms auf STAUBTAL, unter 1 ms auf der Testkarte.
        """
        tx, ty = self.kachel(pos)
        schluessel = (ebene, tx, ty)
        feld = self._zielfelder.get(schluessel)
        if feld is not None:
            return schluessel, feld
        # Hoechstens ein neues Feld je Bild. Laufen zwei Spieler im selben
        # Bild auf eine neue Kachel, kostete das sonst zweimal 9 ms am
        # Stueck - ein sichtbarer Ruckler. Wer in diesem Bild keins mehr
        # bekommt, nimmt das naechstgelegene, das es schon gibt: ein Feld
        # zu einer Kachel daneben fuehrt genauso gut in die Richtung.
        bild = getattr(self.welt, "bildnummer", 0)
        if bild == self._letztes_bild:
            naechstes = None
            for (e, x, y), f in self._zielfelder.items():
                if e != ebene:
                    continue
                abstand = abs(x - tx) + abs(y - ty)
                if naechstes is None or abstand < naechstes[0]:
                    naechstes = (abstand, (e, x, y), f)
            if naechstes is not None:
                return naechstes[1], naechstes[2]
        self._letztes_bild = bild
        b, h = self.breite[ebene], self.hoehe[ebene]
        frei = self.begehbar[ebene]
        weit = [-1] * (b * h)
        if 0 <= tx < b and 0 <= ty < h:
            start = ty * b + tx
            weit[start] = 0
            offen = deque([start])
            while offen:
                i = offen.popleft()
                x, y = i % b, i // b
                for dx, dy in _NACHBARN:
                    nx, ny = x + dx, y + dy
                    if not (0 <= nx < b and 0 <= ny < h):
                        continue
                    j = ny * b + nx
                    if not frei[j] or weit[j] >= 0:
                        continue
                    if dx and dy and not (frei[y * b + nx] and frei[ny * b + x]):
                        continue
                    weit[j] = weit[i] + 1
                    offen.append(j)
        if len(self._zielfelder) >= self._FELDER_ZIEL:
            self._zielfelder.pop(next(iter(self._zielfelder)))
        self._zielfelder[schluessel] = weit
        return schluessel, weit

    def schritt_ueber(self, ebene: int, feld: list, pos):
        """Wie `schritt_zu`, fuer ein beliebiges Feld. Gibt (Punkt, Rest)."""
        b, h = self.breite[ebene], self.hoehe[ebene]
        tx, ty = self.kachel(pos)
        if not (0 <= tx < b and 0 <= ty < h):
            return None, -1
        hier = feld[ty * b + tx]
        bestes, beste = None, hier if hier >= 0 else 1 << 30
        for dx, dy in _NACHBARN:
            nx, ny = tx + dx, ty + dy
            if not (0 <= nx < b and 0 <= ny < h):
                continue
            w = feld[ny * b + nx]
            if w < 0 or w >= beste:
                continue
            if dx and dy and (feld[ty * b + nx] < 0 or feld[ny * b + tx] < 0):
                continue
            bestes, beste = (nx, ny), w
        if bestes is None:
            return None, max(0, hier)
        return (pygame.Vector2((bestes[0] + 0.5) * K.TILE,
                               (bestes[1] + 0.5) * K.TILE), beste)

    def schritt_zu(self, nr: int, pos):
        """Wohin man von `pos` aus gehen muss, um zu Treppe `nr` zu kommen.

        Gibt (Punkt, Rest) zurueck: die Mitte der Nachbarkachel, die der
        Treppe am naechsten ist, und wie weit es von hier noch ist. Rest 0
        heisst: man steht drauf.
        """
        ebene, sx, sy, _ = self.treppen[nr]
        feld = self._feld(nr)
        b, h = self.breite[ebene], self.hoehe[ebene]
        tx, ty = self.kachel(pos)
        if not (0 <= tx < b and 0 <= ty < h):
            return None, -1
        hier = feld[ty * b + tx]
        if hier == 0:
            return pygame.Vector2((sx + 0.5) * K.TILE, (sy + 0.5) * K.TILE), 0
        bestes, beste = None, hier if hier >= 0 else 1 << 30
        for dx, dy in _NACHBARN:
            nx, ny = tx + dx, ty + dy
            if not (0 <= nx < b and 0 <= ny < h):
                continue
            w = feld[ny * b + nx]
            if w < 0 or w >= beste:
                continue
            if dx and dy and (feld[ty * b + nx] < 0 or feld[ny * b + tx] < 0):
                continue
            bestes, beste = (nx, ny), w
        if bestes is None:
            # Auf einer Kachel ohne Feld (etwa halb in einer Wand, oder ein
            # anderes Gebiet): geradewegs auf die Treppe zu, das Ausweichen
            # macht den Rest.
            return pygame.Vector2((sx + 0.5) * K.TILE, (sy + 0.5) * K.TILE), \
                max(0, hier)
        return (pygame.Vector2((bestes[0] + 0.5) * K.TILE,
                               (bestes[1] + 0.5) * K.TILE), beste)
