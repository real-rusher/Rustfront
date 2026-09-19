"""
DUSTFRONT - Bedienelemente
==========================

Die Bausteine, aus denen Pausenmenue, Einstellungen und Inventar bestehen.
Alles wird im Code gezeichnet, es gibt keine Bilddateien dafuer.

Gestaltungsregeln, an die sich jedes Element haelt:

* **Abgeschnittene Ecken.** Kein Rechteck hat rechte Winkel, jede Ecke ist um
  ein paar Pixel gekappt. Das ist die Form, die sich durch Menue, HUD und
  Splash zieht.
* **Eckwinkel statt voller Rahmen.** Grosse Flaechen bekommen kurze Striche
  in den Ecken, keinen durchgezogenen Kasten. Das haelt das Bild ruhig.
* **Vier Zustaende.** Jeder Knopf kennt ruhig, ueberfahren, gedrueckt und
  gesperrt, und sieht in jedem davon anders aus.
* **Ein Pixel Linienstaerke.** Bei 640x360 ist alles andere zu fett.

Die Elemente zeichnen nur. Was passiert, wenn man klickt, entscheidet die
Szene, die sie benutzt.
"""

from __future__ import annotations

import pygame

from . import config as K
from .font import SCHRIFT

RUHIG, UEBER, GEDRUECKT, GESPERRT = range(4)

# Farben je Zustand: (Rahmen, Fuellung, Schrift)
ZUSTAND_FARBEN = {
    RUHIG:     (K.C_MUTED_DK, (16, 11, 8), K.C_MUTED),
    UEBER:     (K.C_AMBER, (34, 24, 14), K.C_CREAM),
    GEDRUECKT: (K.C_AMBER, K.C_AMBER, (18, 12, 8)),
    GESPERRT:  ((44, 34, 25), (12, 9, 7), (66, 52, 39)),
}


# ══════════════════════════════════════════════════ Formen

def ecken(rect: pygame.Rect, schnitt: int = 4):
    """Achteck: Rechteck mit gekappten Ecken."""
    x, y, w, h = rect
    s = min(schnitt, w // 2, h // 2)
    return [
        (x + s, y), (x + w - 1 - s, y), (x + w - 1, y + s),
        (x + w - 1, y + h - 1 - s), (x + w - 1 - s, y + h - 1),
        (x + s, y + h - 1), (x, y + h - 1 - s), (x, y + s),
    ]


def kasten(ziel, rect, rahmen=K.C_MUTED_DK, fuellung=(12, 9, 7), schnitt=4):
    rect = pygame.Rect(rect)
    punkte = ecken(rect, schnitt)
    if fuellung is not None:
        if len(fuellung) == 4:
            flaeche = pygame.Surface(rect.size, pygame.SRCALPHA)
            pygame.draw.polygon(flaeche, fuellung,
                                [(px - rect.x, py - rect.y) for px, py in punkte])
            ziel.blit(flaeche, rect.topleft)
        else:
            pygame.draw.polygon(ziel, fuellung, punkte)
    if rahmen is not None:
        pygame.draw.polygon(ziel, rahmen, punkte, 1)
    return rect


def eckwinkel(ziel, rect, farbe=K.C_AMBER, laenge=8, schnitt=5):
    """Kurze Striche in den vier Ecken, wie an einer Panzerplatte."""
    x, y, w, h = pygame.Rect(rect)
    L, s = laenge, schnitt
    for a, b in (((x + s, y), (x + s + L, y)),
                 ((x, y + s), (x, y + s + L)),
                 ((x + w - 1 - s, y), (x + w - 1 - s - L, y)),
                 ((x + w - 1, y + s), (x + w - 1, y + s + L)),
                 ((x + s, y + h - 1), (x + s + L, y + h - 1)),
                 ((x, y + h - 1 - s), (x, y + h - 1 - s - L)),
                 ((x + w - 1 - s, y + h - 1), (x + w - 1 - s - L, y + h - 1)),
                 ((x + w - 1, y + h - 1 - s), (x + w - 1, y + h - 1 - s - L))):
        pygame.draw.line(ziel, farbe, a, b, 1)


def tafel(ziel, rect, titel: str = "", rahmen=K.C_LINE if hasattr(K, "C_LINE")
          else K.C_MUTED_DK, fuellung=(9, 6, 5, 238)):
    """Grosse Flaeche mit Eckwinkeln und einer Lasche auf der Oberkante."""
    rect = pygame.Rect(rect)
    kasten(ziel, rect, rahmen, fuellung, 6)
    eckwinkel(ziel, rect, K.C_AMBER, 9, 6)
    if titel:
        breite = SCHRIFT.breite(titel, 1) + 14
        lasche = pygame.Rect(rect.x + 14, rect.y - 5, breite, 11)
        pygame.draw.rect(ziel, (14, 10, 8), lasche)
        pygame.draw.rect(ziel, K.C_AMBER, lasche, 1)
        SCHRIFT.zeichnen(ziel, titel, lasche.x + 7, lasche.y + 2, K.C_AMBER, 1)
    return rect


def pfeil(ziel, x, y, farbe, richtung=1, hoehe=7):
    """Kleines Dreieck. Die Pixelschrift hat keine Pfeilzeichen, also wird
    gezeichnet statt gesetzt - das bleibt bei jeder Vergroesserung scharf.

    x, y ist die Mitte. richtung: 1 nach rechts, -1 nach links.
    """
    h = hoehe if hoehe % 2 else hoehe + 1        # ungerade, sonst keine Spitze
    b = h // 2 + 1
    sx = x - (b - 1) // 2
    for i in range(b):
        laenge = h - 2 * i
        if laenge <= 0:
            break
        pygame.draw.rect(ziel, farbe, (sx + i * richtung, y - laenge // 2,
                                       1, laenge))


def schleier(ziel, deckkraft=170):
    s = pygame.Surface(ziel.get_size(), pygame.SRCALPHA)
    s.fill((0, 0, 0, deckkraft))
    ziel.blit(s, (0, 0))


# ══════════════════════════════════════════════════ Bedienelemente

class Element:
    """Gemeinsamer Teil aller anklickbaren Dinge."""

    def __init__(self, rect, name: str = "", gesperrt: bool = False) -> None:
        self.rect = pygame.Rect(rect)
        self.name = name
        self.gesperrt = gesperrt
        self.ueber = False
        self.gedrueckt = False

    def zustand(self) -> int:
        if self.gesperrt:
            return GESPERRT
        if self.gedrueckt:
            return GEDRUECKT
        return UEBER if self.ueber else RUHIG

    def maus(self, pos) -> bool:
        self.ueber = (not self.gesperrt) and self.rect.collidepoint(pos)
        return self.ueber

    def klick(self, pos) -> bool:
        """Gibt True, wenn dieses Element den Klick bekommt."""
        return (not self.gesperrt) and self.rect.collidepoint(pos)

    def zeichnen(self, ziel) -> None:
        pass


class Knopf(Element):
    def __init__(self, rect, text: str, name: str = "", gesperrt: bool = False,
                 hinweis: str = "") -> None:
        super().__init__(rect, name or text, gesperrt)
        self.text = text
        self.hinweis = hinweis

    def zeichnen(self, ziel) -> None:
        z = self.zustand()
        rahmen, fuellung, schrift = ZUSTAND_FARBEN[z]
        r = self.rect.copy()
        if z == GEDRUECKT:
            r.y += 1
        kasten(ziel, r, rahmen, fuellung, 4)
        if z == UEBER:
            # Markierung an der linken Kante, wie im Hauptmenue
            pygame.draw.rect(ziel, K.C_ORANGE, (r.x, r.y + 3, 2, r.height - 6))
            pfeil(ziel, r.x + 8, r.centery, K.C_AMBER, 1, 7)
        SCHRIFT.zeichnen(ziel, self.text, r.centerx, r.centery - 3, schrift, 1,
                         ausrichtung="mitte")


class Reiter(Element):
    """Knopf fuer eine Seitenauswahl, oben an der Tafel."""

    def __init__(self, rect, text: str, name: str = "") -> None:
        super().__init__(rect, name or text)
        self.text = text
        self.aktiv = False

    def zeichnen(self, ziel) -> None:
        r = self.rect
        if self.aktiv:
            kasten(ziel, r, K.C_AMBER, (38, 26, 14), 3)
            farbe = K.C_CREAM
        elif self.ueber:
            kasten(ziel, r, K.C_MUTED, (20, 14, 10), 3)
            farbe = K.C_CREAM
        else:
            kasten(ziel, r, K.C_MUTED_DK, (13, 9, 7), 3)
            farbe = K.C_MUTED
        SCHRIFT.zeichnen(ziel, self.text, r.centerx, r.centery - 3, farbe, 1,
                         ausrichtung="mitte")
        if self.aktiv:
            pygame.draw.line(ziel, K.C_AMBER, (r.x + 2, r.bottom),
                             (r.right - 3, r.bottom))


class Regler(Element):
    """Schieber von 0 bis 100, in Segmenten wie die Balken im HUD."""

    SEGMENTE = 20

    def __init__(self, rect, text: str, name: str, wert: int,
                 schritt: int = 5, einheit: str = "%") -> None:
        super().__init__(rect, name)
        self.text = text
        self.wert = int(wert)
        self.schritt = schritt
        self.einheit = einheit
        self.zieht = False

    @property
    def bahn(self) -> pygame.Rect:
        r = self.rect
        return pygame.Rect(r.x + 116, r.y + 3, r.width - 116 - 34, r.height - 6)

    def aus_x(self, x: int) -> int:
        b = self.bahn
        anteil = (x - b.x) / max(1, b.width - 1)
        roh = anteil * 100.0
        return max(0, min(100, int(round(roh / self.schritt)) * self.schritt))

    def aendern(self, d: int) -> None:
        self.wert = max(0, min(100, self.wert + d * self.schritt))

    def zeichnen(self, ziel) -> None:
        r = self.rect
        hell = self.ueber or self.zieht
        SCHRIFT.zeichnen(ziel, self.text, r.x + 4, r.centery - 3,
                         K.C_CREAM if hell else K.C_MUTED, 1)
        b = self.bahn
        gefuellt = int(round(self.wert / 100.0 * self.SEGMENTE))
        sw = max(1, (b.width - (self.SEGMENTE - 1) * 1) // self.SEGMENTE)
        for i in range(self.SEGMENTE):
            x = b.x + i * (sw + 1)
            an = i < gefuellt
            pygame.draw.rect(ziel, K.C_AMBER if an else (32, 23, 16),
                             (x, b.y, sw, b.height))
        SCHRIFT.zeichnen(ziel, "%d%s" % (self.wert, self.einheit), r.right - 4,
                         r.centery - 3, K.C_CREAM if hell else K.C_MUTED, 1,
                         ausrichtung="rechts")


class Wahl(Element):
    """Blaettert durch eine Liste von Werten, mit Pfeilen links und rechts."""

    def __init__(self, rect, text: str, name: str, optionen: list,
                 index: int = 0, anzeige: dict | None = None) -> None:
        super().__init__(rect, name)
        self.text = text
        self.optionen = list(optionen)
        self.index = max(0, min(len(self.optionen) - 1, index))
        self.anzeige = anzeige or {}

    @property
    def wert(self):
        return self.optionen[self.index]

    def beschriftung(self) -> str:
        w = self.wert
        return str(self.anzeige.get(w, w)).upper()

    def links_rect(self) -> pygame.Rect:
        r = self.rect
        return pygame.Rect(r.x + 116, r.y + 1, 12, r.height - 2)

    def rechts_rect(self) -> pygame.Rect:
        r = self.rect
        return pygame.Rect(r.right - 14, r.y + 1, 12, r.height - 2)

    def blaettern(self, d: int) -> None:
        self.index = (self.index + d) % len(self.optionen)

    def klick(self, pos) -> bool:
        if self.gesperrt:
            return False
        if self.links_rect().collidepoint(pos):
            self.blaettern(-1)
            return True
        if self.rechts_rect().collidepoint(pos):
            self.blaettern(1)
            return True
        if self.rect.collidepoint(pos):
            self.blaettern(1)
            return True
        return False

    def zeichnen(self, ziel) -> None:
        r = self.rect
        hell = self.ueber
        SCHRIFT.zeichnen(ziel, self.text, r.x + 4, r.centery - 3,
                         K.C_CREAM if hell else K.C_MUTED, 1)
        lr, rr = self.links_rect(), self.rechts_rect()
        pfarbe = K.C_AMBER if hell else K.C_MUTED_DK
        pfeil(ziel, lr.centerx, lr.centery, pfarbe, -1, 7)
        pfeil(ziel, rr.centerx, rr.centery, pfarbe, 1, 7)
        mitte = (lr.right + rr.left) // 2
        SCHRIFT.zeichnen(ziel, self.beschriftung(), mitte, r.centery - 3,
                         K.C_CREAM if hell else K.C_MUTED, 1, ausrichtung="mitte")


class Schalter(Element):
    """An oder aus."""

    def __init__(self, rect, text: str, name: str, an: bool) -> None:
        super().__init__(rect, name)
        self.text = text
        self.an = bool(an)

    def zeichnen(self, ziel) -> None:
        r = self.rect
        hell = self.ueber
        SCHRIFT.zeichnen(ziel, self.text, r.x + 4, r.centery - 3,
                         K.C_CREAM if hell else K.C_MUTED, 1)
        k = pygame.Rect(r.x + 116, r.y + 2, 26, r.height - 4)
        kasten(ziel, k, K.C_AMBER if self.an else K.C_MUTED_DK,
               (34, 24, 14) if self.an else (14, 10, 8), 3)
        knopf = pygame.Rect(k.x + (k.width - 11) if self.an else k.x + 1,
                            k.y + 1, 10, k.height - 2)
        pygame.draw.rect(ziel, K.C_AMBER if self.an else K.C_MUTED_DK, knopf)
        SCHRIFT.zeichnen(ziel, "AN" if self.an else "AUS", k.right + 6,
                         r.centery - 3, K.C_AMBER if self.an else K.C_MUTED, 1)


def kuerzen(text: str, breite: int, skala: int = 1) -> str:
    """Schneidet Text ab, der nicht in `breite` Pixel passt.

    Lieber ein sichtbar gekuerztes Wort als eines, das in die Nachbarspalte
    laeuft. Das abschliessende `>` zeigt an, dass da noch etwas fehlt.
    """
    if SCHRIFT.breite(text, skala) <= breite:
        return text
    kurz = text
    while kurz and SCHRIFT.breite(kurz + ">", skala) > breite:
        kurz = kurz[:-1]
    return kurz + ">" if kurz else ""


class Zeile(Element):
    """Eine Tastenbelegung: Aktion links, Taste rechts, anklickbar."""

    def __init__(self, rect, text: str, name: str, tasten: str,
                 gesperrt: bool = False, label_breite: int = 150) -> None:
        super().__init__(rect, name, gesperrt)
        self.text = text
        self.tasten = tasten
        self.label_breite = label_breite
        self.wartet = False        # wartet auf den naechsten Tastendruck

    @property
    def feld_rect(self) -> pygame.Rect:
        r = self.rect
        return pygame.Rect(r.x + self.label_breite, r.y + 1,
                           r.width - self.label_breite - 4, r.height - 2)

    def zeichnen(self, ziel) -> None:
        r = self.rect
        hell = self.ueber and not self.gesperrt
        SCHRIFT.zeichnen(ziel, kuerzen(self.text, self.label_breite - 8),
                         r.x + 4, r.centery - 3,
                         K.C_MUTED_DK if self.gesperrt else
                         (K.C_CREAM if hell else K.C_MUTED), 1)
        feld = self.feld_rect
        if self.wartet:
            kasten(ziel, feld, K.C_TEAL, (10, 24, 22), 3)
            SCHRIFT.zeichnen(ziel, kuerzen("TASTE DRUECKEN", feld.width - 8),
                             feld.centerx, feld.centery - 3, K.C_TEAL, 1,
                             ausrichtung="mitte")
        else:
            kasten(ziel, feld, K.C_AMBER if hell else K.C_MUTED_DK,
                   (18, 13, 9), 3)
            SCHRIFT.zeichnen(ziel, kuerzen(self.tasten.upper(), feld.width - 4),
                             feld.centerx, feld.centery - 3,
                             K.C_MUTED_DK if self.gesperrt else K.C_CREAM, 1,
                             ausrichtung="mitte")


# ══════════════════════════════════════════════════ Rasterfelder

def feld(ziel, rect, gefuellt=False, gewaehlt=False, ueber=False):
    """Ein Platz im Inventar."""
    rect = pygame.Rect(rect)
    if gewaehlt:
        rahmen, fuellung = K.C_AMBER, (34, 24, 14)
    elif ueber:
        rahmen, fuellung = K.C_MUTED, (22, 16, 11)
    elif gefuellt:
        rahmen, fuellung = K.C_MUTED_DK, (18, 13, 9)
    else:
        rahmen, fuellung = (38, 29, 21), (11, 8, 6)
    kasten(ziel, rect, rahmen, fuellung, 3)
    return rect
