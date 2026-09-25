"""
DUSTFRONT - Der Wandler
=======================

Der Wandler ist die Basis, das Fahrzeug und die Waffe in einem Stueck. Hier
steht, wie aus einer Kartendatei eine Maschine wird, die laeuft.

Was wo steht
------------

Nichts an einem bestimmten Wandler steht in dieser Datei. Was ein Warhound
ist, steht in `karten/wandler/warhound.txt`: seine Decks als Text, seine
Beine als Zeilen, seine Klasse als Wort. Diese Datei weiss nur, **wie** man
eine solche Beschreibung liest.

    karten/wandler/<name>.txt    was diese Maschine ist
    K.WANDLER_KLASSEN            was eine Bauklasse bedeutet
    K.WANDLER, K.GANG, K.BEIN    wie sich Laufen anfuehlt
    beine.py                     wie Laufen funktioniert
    wandler.py                   wie das alles zusammenkommt

Wer eine neue Maschine will, legt eine Textdatei an. Wer eine bestehende
umbaut, tippt in ihr. Beides ohne eine Zeile Python.

Der Rumpf als Welt
------------------

Ein Wandler *ist* eine `Welt` - dieselbe Struktur wie ein Ort, dieselbe
Kollision, dieselben Treppen, dieselben Stuerze. Seine Ebenen sind seine
Decks. Wer an Bord laeuft, laeuft in einer ganz normalen Welt, und der
Umstand, dass sie sich durch die Wueste bewegt, faellt dabei nicht auf:
an Bord ist der Rumpf der ruhende Bezugsrahmen.

Was sich bewegt, ist **eine Zahl** - `welt.versatz`, die Lage des Rumpfes
in der Aussenwelt. Sie ist eine Kommazahl, nie ein Kachelmass, damit sich
kein Gitter je gegen sein eigenes Raster verschiebt.
"""

from __future__ import annotations

import math

import pygame

from . import config as K
from .beine import Bein, Gangwerk, _dreh
from .karten import KartenFehler, lesen
from .world import Welt, hoehen_staffel


class Bauplan:
    """Was in einer Wandler-Kartendatei steht, geprueft und ausgepackt."""

    def __init__(self, karte) -> None:
        self.karte = karte
        self.name = karte.text("name", karte.name)
        self.klasse = karte.text("klasse", "reaver").lower()
        if self.klasse not in K.WANDLER_KLASSEN:
            raise KartenFehler(
                "%s: Klasse %r unbekannt - bekannt sind %s"
                % (karte.name, self.klasse, ", ".join(sorted(K.WANDLER_KLASSEN))))
        vor = K.WANDLER_KLASSEN[self.klasse]

        # Klassenvorgabe, von der Datei ueberschreibbar. In dieser
        # Reihenfolge, damit eine Datei immer gewinnt.
        self.klassenname = karte.text("klassenname", vor["name"])
        self.gewicht = int(karte.zahl("gewicht", vor["gewicht"]))
        self.tempo = karte.zahl("tempo", vor["tempo"])
        self.dreh = karte.zahl("dreh", vor.get("dreh", K.WANDLER["dreh"]))
        self.takt = karte.zahl("takt", vor.get("takt", 1.0))

        self.decks = len(karte.bloecke)
        self.bein_masse = self._beinmasse_rechnen(karte, vor)

        # Wo die Masse wirklich sitzt, in Kacheln von der Rumpfmitte aus.
        #
        # Das ist keine Feinheit. Ein Laufvogel traegt seine Beine hinten
        # und balanciert den Koerper darueber - haelt man seinen
        # Schwerpunkt in der geometrischen Mitte, liegt er einen halben
        # Rumpf vor den Fuessen und faellt nach vorn. Genau das ist beim
        # Bauen passiert, und das Modell hatte recht: so etwas steht nicht.
        roh = karte.text("schwerpunkt", vor.get("schwerpunkt", "0 0"))
        teile = str(roh).split()
        try:
            self.schwerpunkt = pygame.Vector2(float(teile[0]) * K.TILE,
                                              float(teile[1]) * K.TILE)
        except (ValueError, IndexError):
            raise KartenFehler("%s: schwerpunkt: %r - erwartet zwei Zahlen"
                               % (karte.name, roh))
        self.beine = self._beine_lesen(karte)
        if not self.beine:
            raise KartenFehler("%s: kein einziges `bein:` - eine Maschine "
                               "ohne Beine kann nicht laufen" % karte.name)

    # ---- Beinmasse -------------------------------------------------------
    def _beinmasse_rechnen(self, karte, vor) -> dict:
        """Wie gross die Beine sind - abgeleitet aus dem Rumpf.

        **Das ist der Unterschied zwischen einem Tragwerk und Spaghetti.**
        Feste Pixelwerte sehen bei einem Warhound noch brauchbar aus und bei
        einem Imperator laecherlich: ein Bein, das eine Maschine von sechs
        Metern Rumpfbreite traegt, ist kein Stock. Es ist ein riesiges
        mechanisches Bauteil.

        Gerechnet wird aus der **halben Rumpfbreite** des untersten Decks:
        ein Bein ist ungefaehr so lang wie der Rumpf breit ist, und sein
        Oberschenkel ein gutes Viertel davon dick. Wer es anders will,
        schreibt `bein_ober:` und so weiter in die Kartendatei - das gewinnt
        immer.
        """
        block = karte.bloecke[0]
        breite = max(len(z) for z in block) * K.TILE
        hoehe = len(block) * K.TILE
        # Massgebend ist die **schmale** Achse, nicht die lange. Wie hoch
        # eine Maschine auf ihren Beinen steht, haengt daran, wie breit sie
        # ist, nicht daran, wie lang - sonst bekaeme ein Belagerungslaeufer
        # von 45 Kacheln Laenge Beine wie Bruecken.
        halb = min(breite, hoehe) / 2.0

        m = dict(K.BEIN)
        m["ober"] = halb * K.BEIN["ober_anteil"]
        m["unter"] = halb * K.BEIN["unter_anteil"]
        m["dicke_ober"] = max(4, int(round(halb * K.BEIN["dicke_anteil"])))
        m["dicke_unter"] = max(3, int(round(m["dicke_ober"]
                                            * K.BEIN["dicke_unter_anteil"])))
        m["fuss"] = max(6, int(round(m["dicke_ober"] * K.BEIN["fuss_anteil"])))
        m["huefte"] = max(6, int(round(m["dicke_ober"]
                                       * K.BEIN["huefte_anteil"])))
        m.update(vor.get("bein", {}))
        for schluessel in ("ober", "unter", "dicke_ober", "dicke_unter",
                           "fuss", "huefte", "spreizen"):
            roh = karte.text("bein_" + schluessel, "")
            if roh:
                m[schluessel] = float(roh)
        m["rumpf_breite"] = min(breite, hoehe)
        return m

    # ---- Beine ---------------------------------------------------------
    def _beine_lesen(self, karte) -> list[dict]:
        """Wertet die `bein:`-Zeilen aus.

            bein: <huefte_x> <huefte_y> <knieseite> [fuss_x fuss_y]

        Angaben in Kacheln, gemessen von der Mitte des Rumpfes. Die
        Ruhelage des Fusses darf fehlen - dann wird sie aus der
        Beinreichweite gerechnet, nach aussen und ein Stueck in die
        Richtung, in der die Huefte sitzt. Vordere Beine spreizen dadurch
        nach vorn, hintere nach hinten, und das sieht aus wie eine
        Maschine, die steht, statt wie ein Tisch.
        """
        gefunden = []
        for nummer, zeile in enumerate(karte.liste("bein"), start=1):
            teile = zeile.split()
            if len(teile) < 3:
                raise KartenFehler(
                    "%s, bein-Zeile %d: %r - erwartet 'x y seite'"
                    % (karte.name, nummer, zeile))
            try:
                hx, hy = float(teile[0]), float(teile[1])
            except ValueError:
                raise KartenFehler("%s, bein-Zeile %d: %r ist keine Zahl"
                                   % (karte.name, nummer, zeile))
            seite_wort = teile[2].lower()
            if seite_wort not in ("links", "rechts"):
                raise KartenFehler(
                    "%s, bein-Zeile %d: Knieseite %r - erlaubt sind "
                    "'links' und 'rechts'" % (karte.name, nummer, teile[2]))

            huefte = pygame.Vector2(hx * K.TILE, hy * K.TILE)
            if len(teile) >= 5:
                ruhe = pygame.Vector2(float(teile[3]) * K.TILE,
                                      float(teile[4]) * K.TILE)
            else:
                ruhe = self._ruhe_rechnen(huefte)
            gefunden.append(dict(
                huefte=huefte, ruhe=ruhe,
                seite=-1.0 if seite_wort == "links" else 1.0))
        return gefunden

    def _ruhe_rechnen(self, huefte: pygame.Vector2) -> pygame.Vector2:
        reichweite = self.bein_masse["ober"] + self.bein_masse["unter"]
        # Ueberwiegend nach aussen, ein Viertel in Laengsrichtung.
        aussen = pygame.Vector2(huefte.x * 0.25, huefte.y)
        if aussen.length_squared() < 1e-6:
            aussen = pygame.Vector2(0.0, 1.0)
        aussen.normalize_ip()
        return huefte + aussen * (reichweite * self.bein_masse["spreizen"])

    def __repr__(self) -> str:
        return ("<Bauplan %s %s %d Decks %d Beine>"
                % (self.name, self.klasse, self.decks, len(self.beine)))


def bauplan(name: str) -> Bauplan:
    """Liest `karten/wandler/<name>.txt`, falls der Pfad kurz angegeben ist."""
    if "/" not in name:
        name = "wandler/" + name
    return Bauplan(lesen(name))


class Wandler:
    """Eine Laufmaschine: Decks zum Begehen, Beine zum Laufen."""

    def __init__(self, plan: Bauplan, pos=(0, 0), kurs: float = 0.0) -> None:
        self.plan = plan
        self.welt = Welt.aus_karte(plan.karte,
                                   hoehen_staffel(plan.decks, mit_boden=False))
        self.welt.name = plan.name

        m = plan.bein_masse
        beine = [Bein(b["huefte"], b["ruhe"], b["seite"], m["ober"], m["unter"])
                 for b in plan.beine]
        self.gangwerk = Gangwerk(beine, pos, kurs,
                                 takt=plan.takt, tempo=plan.tempo,
                                 fuss_breite=m["fuss"],
                                 rumpf_breite=m["rumpf_breite"],
                                 dreh=plan.dreh,
                                 schwerpunkt=plan.schwerpunkt)
        self._versatz_setzen()

    # ---- Was aussen sichtbar ist ----------------------------------------
    @property
    def pos(self) -> pygame.Vector2:
        return self.gangwerk.pos

    @property
    def kurs(self) -> float:
        return self.gangwerk.kurs

    @property
    def tempo(self) -> float:
        """Gemessen, nicht befohlen. Was die Beine wirklich geliefert haben."""
        return self.gangwerk.tempo_ist

    @property
    def beine(self) -> list[Bein]:
        return self.gangwerk.beine

    @property
    def mitte_lokal(self) -> pygame.Vector2:
        """Mitte des Rumpfes in seinen eigenen Kachelkoordinaten."""
        e = self.welt.ebene(0)
        return pygame.Vector2(e.pixel_breite / 2.0, e.pixel_hoehe / 2.0)

    @property
    def rumpf_radius(self) -> float:
        e = self.welt.ebene(0)
        return max(e.pixel_breite, e.pixel_hoehe) / 2.0

    # ---- Umrechnen zwischen Rumpf und Welt -------------------------------
    #
    # Das ist die ganze Kopplung zwischen "an Bord" und "draussen", und sie
    # ist absichtlich so klein: zwei Funktionen, eine Drehung, eine
    # Verschiebung. Mehr braucht es nicht, weil sich an Bord nichts bewegt.

    def nach_welt(self, lokal) -> pygame.Vector2:
        return self.pos + _dreh(pygame.Vector2(lokal) - self.mitte_lokal,
                                self.kurs)

    def nach_rumpf(self, weltpunkt) -> pygame.Vector2:
        return _dreh(pygame.Vector2(weltpunkt) - self.pos, -self.kurs) \
            + self.mitte_lokal

    def _versatz_setzen(self) -> None:
        self.welt.versatz.update(self.pos)

    # ---- Steuern ---------------------------------------------------------
    def steuern(self, schub: float, lenkung: float,
                ueberlast: bool = False) -> None:
        """Was der Steuerstand befiehlt.

        `schub` und `lenkung` sind Wuensche, keine Bewegung: sie bestimmen,
        **wohin die Fuesse greifen**. Ob die Maschine sich daraufhin auch
        bewegt, entscheiden die Beine.
        """
        g = self.gangwerk
        g.schub = max(-1.0, min(1.0, schub))
        g.lenkung = max(-1.0, min(1.0, lenkung))
        g.ueberlast = bool(ueberlast)

    def schritt(self, dt: float, boden=None, klang=None, stoss=None) -> None:
        self.gangwerk.schritt(dt, boden, klang, stoss)
        self._versatz_setzen()
        if self.gangwerk.ueberlast:
            for b in self.beine:
                if b.heil:
                    b.last = min(1.0, b.last + K.WANDLER["ueberlast_last"] * dt)

    # ---- Schaden ----------------------------------------------------------
    def bein_verlieren(self, nummer: int) -> bool:
        """Ein Bein faellt aus.

        Dass die Maschine danach langsamer und schief laeuft, steht nirgends
        geschrieben: ein Bein, das nicht mehr traegt, verschiebt den
        Schwerpunkt der Standfuesse, und der Rumpf folgt dem Schwerpunkt.
        Die Folgen fallen von selbst an.
        """
        if not 0 <= nummer < len(self.beine):
            return False
        b = self.beine[nummer]
        if not b.heil:
            return False
        b.heil = False
        b.t = -1.0
        b.hub = 0.0
        self.gangwerk.ruhe_ausgleichen()
        return True

    def bein_richten(self, nummer: int) -> bool:
        """Reparatur. Der Fuss kommt dort zurueck, wo er hingehoert."""
        if not 0 <= nummer < len(self.beine):
            return False
        b = self.beine[nummer]
        if b.heil:
            return False
        b.heil = True
        b.last = 0.0
        self.gangwerk.ruhe_ausgleichen()
        b.fuss.update(b.ruhe_welt(self.pos, self.kurs))
        return True

    @property
    def beine_heil(self) -> int:
        return sum(1 for b in self.beine if b.heil)

    @property
    def umgekippt(self) -> bool:
        return self.gangwerk.umgekippt

    @property
    def halt(self) -> float:
        """Wie weit der Rumpf innerhalb seiner Stuetzflaeche liegt."""
        return self.gangwerk.halt

    @property
    def fahrbereit(self) -> bool:
        """Faehrt sie noch?

        Zwei Bedingungen, und die zweite ist die interessante: sie muss
        genug Beine haben *und* mit ihnen noch stehen koennen. Vier von
        sechs verloren heisst nicht automatisch fahrbereit - wenn die zwei
        uebrigen hinten sitzen, liegt der Rumpf vor ihrer Stuetzflaeche und
        die Maschine kippt.
        """
        # Nicht der Halt in *diesem* Augenblick - der ist bei einem
        # Zweibeiner mitten im Schritt naturgemaess schlecht, weil er dann
        # auf einem Fuss steht. Ob eine Maschine traegt, entscheidet sich
        # ueber die Zeit, und das tut `_standfestigkeit`: bleibt sie zu
        # lange ohne Halt, kippt sie, und dann steht es hier.
        return self.beine_heil >= 2 and not self.gangwerk.umgekippt

    def aufrichten(self) -> None:
        self.gangwerk.aufrichten()

    # ---- Stationen ---------------------------------------------------------
    def stationen(self) -> dict[str, tuple]:
        """Alle Stationen des Rumpfes: Name -> (Deck, Punkt im Rumpf)."""
        gefunden = {}
        for e in self.welt.ebenen:
            for name, punkt in e.stationen().items():
                gefunden.setdefault(name, (e.index, punkt))
        return gefunden

    def __repr__(self) -> str:
        return ("<Wandler %s %d/%d Beine %.0f px/s>"
                % (self.plan.name, self.beine_heil, len(self.beine),
                   self.tempo))
