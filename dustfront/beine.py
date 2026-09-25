"""
DUSTFRONT - Das Beinwerk
========================

Wie eine Maschine auf Beinen laeuft, und warum sie das hier wirklich tut.

Der uebliche Weg und warum er falsch ist
----------------------------------------

Fast jedes Spiel mit Laufmaschinen macht es so: der Rumpf bekommt eine
Geschwindigkeit und faehrt los, und die Beine bekommen hinterher eine
Animation, die ungefaehr dazu passt. Das sieht man sofort. Der Rumpf
gleitet, die Fuesse schlittern ueber den Boden, und nichts an der Bewegung
hat eine Ursache.

Hier ist es umgekehrt, und das ist die eine Entscheidung, an der dieses
Modul haengt:

    **Der Rumpf hat keine eigene Geschwindigkeit.**
    Er wird von den Fuessen getragen, die gerade am Boden stehen.

Ein stehender Fuss ist in der *Welt* verankert und bewegt sich nicht. Was
den Rumpf vorwaerts bringt, ist allein der Umstand, dass ein Fuss beim
Schritt **vor** seiner Ruhelage aufsetzt. Danach zieht der Rumpf zu seinen
Fuessen hin - und steht damit ein Stueck weiter vorn als vorher.

Daraus folgt alles Weitere von selbst, ohne eine einzige Sonderregel:

* **Tempo ist ein Ergebnis, keine Eingabe.** Der Rumpf kommt je Gangzyklus
  genau eine Schrittweite voran. Wer schneller will, braucht laengere
  Schritte oder mehr Takt - und beides hat eine Obergrenze.
* **Ein zerstoertes Bein wirkt sofort.** Es traegt nicht mehr, also
  verschiebt sich der Schwerpunkt der Standfuesse, und die Maschine geht
  schief und langsamer. Dafuer steht keine Zeile Sondercode hier.
* **Auf der Stelle stehen ist wirklich stehen.** Kein Zittern, kein
  Nachgleiten: die Fuesse sind verankert, also ist der Rumpf es auch.
* **Wer stoesst, verschiebt nichts.** Ein Rueckstoss bewegt Fuesse, nicht
  den Rumpf - und der Rumpf folgt nach.

Wie der Rumpf aus den Fuessen gerechnet wird
--------------------------------------------

Jedes Bein hat eine **Ruhelage** im Rumpfkoordinatensystem: dort steht sein
Fuss, wenn die Maschine haelt. Stehen die Fuesse woanders, suchen wir die
Lage und Drehung des Rumpfes, die am besten dazu passt - das ist eine
kleine Ausgleichsrechnung, in zwei Dimensionen ein Dreizeiler:

    theta = atan2( Summe(r_i kreuz f_i), Summe(r_i mal f_i) )
    mitte = Mittel(f_i) - dreh(Mittel(r_i), theta)

`r_i` ist die Ruhelage des Beins i (um den Mittelwert bereinigt), `f_i` die
wirkliche Fussstellung. Heraus kommt genau eine Lage und genau ein Kurs.
Beides zieht der Rumpf dann weich nach, damit es mechanisch wirkt statt
mathematisch.

Gangart
-------

Die Beine treten in Gruppen. Welches Bein in welche Gruppe gehoert, wird
nicht je Bauklasse aufgeschrieben, sondern aus der Bauart abgeleitet: je
Seite von vorn nach hinten durchgezaehlt, abwechselnd, und die rechte Seite
um eins versetzt. Das ergibt

    2 Beine   abwechselnd links, rechts
    4 Beine   Kreuzgang - vorn links mit hinten rechts
    6 Beine   Dreifuss - vorn links, mitte rechts, hinten links

also genau die Gangarten, die echte Laeufer benutzen, und zwar fuer jede
Beinzahl ohne eine eigene Tabelle.

Alle Zahlen stehen in `K.GANG` und `K.BEIN`, die Bauart in der
Kartendatei des Wandlers. Hier steht nur, wie daraus Bewegung wird.
"""

from __future__ import annotations

import math

import pygame

from . import config as K


def _dreh(v: pygame.Vector2, grad: float) -> pygame.Vector2:
    """Dreht einen Vektor. Eigene Fassung, weil pygame.rotate neu anlegt und
    das hier je Bild und Bein passiert."""
    r = math.radians(grad)
    c, s = math.cos(r), math.sin(r)
    return pygame.Vector2(v.x * c - v.y * s, v.x * s + v.y * c)


def _winkel_diff(ziel: float, ist: float) -> float:
    """Kuerzester Weg von ist nach ziel, in Grad, im Bereich -180..180."""
    return (ziel - ist + 180.0) % 360.0 - 180.0


def _weich(t: float) -> float:
    """Weiche Schwungkurve: langsam los, schnell durch, sauber gesetzt.

    Kein lineares Hin: ein Bein, das mit gleichbleibender Geschwindigkeit
    umsetzt, sieht aus, als wuerde es geschoben. Ein echter Schritt
    beschleunigt und bremst wieder.
    """
    t = max(0.0, min(1.0, t))
    return t * t * (3.0 - 2.0 * t)


def knie_punkt(huefte: pygame.Vector2, fuss: pygame.Vector2,
               ober: float, unter: float, seite: float) -> pygame.Vector2:
    """Wo das Knie steht, wenn Huefte und Fuss feststehen.

    Zwei Kreise schneiden sich in zwei Punkten; `seite` waehlt welchen, und
    das entscheidet, ob das Knie nach aussen oder nach innen ausbricht. Bei
    einer Laufmaschine bricht es nach aussen - das ist die Bauform, die
    Gewicht traegt.
    """
    d = fuss - huefte
    laenge = d.length()
    if laenge < 1e-6:
        d = pygame.Vector2(1.0, 0.0)
        laenge = 1.0
    # Nie ganz durchgestreckt und nie ganz zusammengelegt: sonst springt das
    # Knie zwischen den beiden Loesungen hin und her.
    rest = K.BEIN["knie_mindest"] * (ober + unter)
    laenge = max(abs(ober - unter) + rest, min(ober + unter - rest, laenge))
    richtung = d / d.length()
    a = (ober * ober - unter * unter + laenge * laenge) / (2.0 * laenge)
    h = math.sqrt(max(0.0, ober * ober - a * a))
    mitte = huefte + richtung * a
    quer = pygame.Vector2(-richtung.y, richtung.x)
    return mitte + quer * (h * seite)


class Bein:
    """Ein Bein: zwei Glieder, ein Fuss, ein Anker in der Welt."""

    def __init__(self, huefte_lokal, ruhe_lokal, seite: float,
                 ober: float, unter: float) -> None:
        self.huefte_lokal = pygame.Vector2(huefte_lokal)
        self.ruhe_lokal = pygame.Vector2(ruhe_lokal)
        self.seite = seite                  # +1 oder -1, wohin das Knie geht
        self.ober, self.unter = float(ober), float(unter)

        # Der Anker. Solange das Bein steht, aendert sich das hier nicht -
        # und genau deshalb bewegt sich der Rumpf.
        self.fuss = pygame.Vector2()
        self.von = pygame.Vector2()         # Schwung: woher
        self.nach = pygame.Vector2()        # Schwung: wohin
        self.t = -1.0                       # <0 steht, 0..1 schwingt
        self.dauer = 1.0
        self.hub = 0.0                      # aktuelle Hoehe ueber Grund
        self.hub_max = 0.0

        self.heil = True                    # ein zerstoertes Bein traegt nicht
        self.last = 0.0                     # Belastung durch Ueberlast
        self.gruppe = 0

    # ---- Zustand ------------------------------------------------------
    @property
    def steht(self) -> bool:
        return self.t < 0.0 and self.heil

    @property
    def reichweite(self) -> float:
        return self.ober + self.unter

    def ruhe_welt(self, mitte: pygame.Vector2, kurs: float) -> pygame.Vector2:
        return mitte + _dreh(self.ruhe_lokal, kurs)

    def huefte_welt(self, mitte: pygame.Vector2, kurs: float) -> pygame.Vector2:
        return mitte + _dreh(self.huefte_lokal, kurs)

    def schleppe(self, mitte: pygame.Vector2, kurs: float) -> float:
        """Wie weit der Fuss von seiner Ruhelage abgekommen ist."""
        return self.fuss.distance_to(self.ruhe_welt(mitte, kurs))

    # ---- Schritt ------------------------------------------------------
    def treten(self, ziel: pygame.Vector2, dauer: float, hub: float) -> None:
        self.von = pygame.Vector2(self.fuss)
        self.nach = pygame.Vector2(ziel)
        self.t = 0.0
        self.dauer = max(0.02, dauer)
        self.hub_max = hub

    def schritt(self, dt: float) -> bool:
        """Bringt einen Schwung voran. True, wenn der Fuss jetzt aufsetzt."""
        if self.t < 0.0:
            return False
        self.t += dt / self.dauer
        if self.t >= 1.0:
            self.fuss.update(self.nach)
            self.t = -1.0
            self.hub = 0.0
            return True
        f = _weich(self.t)
        self.fuss.update(self.von.lerp(self.nach, f))
        self.hub = math.sin(math.pi * self.t) * self.hub_max
        return False

    # ---- Darstellung --------------------------------------------------
    def glieder(self, mitte: pygame.Vector2, kurs: float):
        """Huefte, Knie und Fuss in Weltkoordinaten, fuer den Renderer.

        Der Hub wird hier aufgeschlagen: von oben gesehen ist "angehoben"
        eine kleine Verschiebung nach oben im Bild. Der Schatten bleibt
        unten - erst beides zusammen liest sich als angehobener Fuss.
        """
        h = self.huefte_welt(mitte, kurs)
        f = pygame.Vector2(self.fuss.x, self.fuss.y - self.hub)
        k = knie_punkt(h, f, self.ober, self.unter, self.seite)
        return h, k, f


class Gangwerk:
    """Alle Beine einer Maschine, und der Rumpf, den sie tragen."""

    def __init__(self, beine: list[Bein], pos, kurs: float = 0.0,
                 takt: float = 1.0, tempo: float = 0.0) -> None:
        self.beine = beine
        self.pos = pygame.Vector2(pos)
        self.kurs = float(kurs)
        self.takt_faktor = float(takt)
        self.tempo_max = float(tempo) or K.WANDLER["tempo"]

        # Alles, was sich nach der Beinlaenge richtet, einmal hier. Kurze
        # Beine machen kurze Schritte, lange machen lange - das ist der
        # Unterschied zwischen einem Warhound und einem Imperator, und er
        # steht an genau einer Stelle.
        self.reichweite = (sum(b.reichweite for b in beine) / len(beine)
                           if beine else 1.0)
        self.schritt_max = self.reichweite * K.GANG["schritt_anteil"]

        # Regelgroesse fuer die Schrittweite, siehe K.GANG["regelung"].
        self.korrektur = K.GANG["regel_start"]

        self.uhr = 0.0
        self.gruppe_dran = 0
        self.schub = 0.0            # was die Beine leisten sollen, -1..1
        self.lenkung = 0.0          # -1..1
        self.kurs_soll = float(kurs)
        self.ueberlast = False

        self.wank = 0.0             # Schraeglage aus ungleichem Stand
        self.atem = 0.0             # das leichte Heben und Senken im Gang
        self.tempo_ist = 0.0        # gemessen, nicht befohlen
        self._vorher = pygame.Vector2(self.pos)

        self._gruppen_bilden()
        self.setzen(pos, kurs)

    # ---- Aufbau --------------------------------------------------------
    def _gruppen_bilden(self) -> None:
        """Teilt die Beine in zwei Gruppen, die abwechselnd treten.

        Je Seite von vorn nach hinten abwechselnd, die rechte Seite um eins
        versetzt. Das ergibt fuer zwei Beine den Wechselschritt, fuer vier
        den Kreuzgang und fuer sechs den Dreifuss - ohne dass irgendwo eine
        Tabelle je Beinzahl steht.
        """
        links = sorted([b for b in self.beine if b.huefte_lokal.y < 0],
                       key=lambda b: -b.huefte_lokal.x)
        rechts = sorted([b for b in self.beine if b.huefte_lokal.y >= 0],
                        key=lambda b: -b.huefte_lokal.x)
        for rang, b in enumerate(links):
            b.gruppe = rang % 2
        for rang, b in enumerate(rechts):
            b.gruppe = (rang + 1) % 2
        self.gruppen = sorted({b.gruppe for b in self.beine}) or [0]

    def setzen(self, pos, kurs: float) -> None:
        """Stellt die Maschine hin: alle Fuesse in ihre Ruhelage."""
        self.pos.update(pos)
        self.kurs = float(kurs)
        self.kurs_soll = float(kurs)
        self._vorher.update(self.pos)
        for b in self.beine:
            b.fuss.update(b.ruhe_welt(self.pos, self.kurs))
            b.t = -1.0
            b.hub = 0.0

    # ---- Abfragen -------------------------------------------------------
    @property
    def stehende(self) -> list[Bein]:
        return [b for b in self.beine if b.steht]

    @property
    def heile(self) -> list[Bein]:
        return [b for b in self.beine if b.heil]

    @property
    def vorwaerts(self) -> pygame.Vector2:
        r = math.radians(self.kurs)
        return pygame.Vector2(math.cos(r), math.sin(r))

    def zyklus(self, tempo_anteil: float) -> tuple[float, float]:
        """Taktfrequenz und Zyklusdauer beim gegebenen Schub."""
        g = K.GANG
        hz = (g["takt_ruhe"] + (g["takt_voll"] - g["takt_ruhe"])
              * min(1.0, abs(tempo_anteil))) * self.takt_faktor
        if self.ueberlast:
            hz *= K.WANDLER["ueberlast"]
        hz = max(0.05, hz)
        return hz, len(self.gruppen) / hz

    # ---- Der Gang --------------------------------------------------------
    def schritt(self, dt: float, welt=None, klang=None, stoss=None) -> None:
        if dt <= 0.0:
            return
        g = K.GANG
        w = K.WANDLER

        # 1. Kurswunsch. Die Lenkung dreht nur den *Wunsch*; wie der Rumpf
        #    wirklich steht, ergibt sich weiter unten aus den Fuessen.
        dreh_max = w["dreh"] * (K.WANDLER["ueberlast"] if self.ueberlast else 1.0)
        self.kurs_soll += self.lenkung * dreh_max * dt

        # 2. Gangtakt. Er laeuft nur, wenn auch Schub anliegt - eine
        #    stehende Maschine tritt nicht auf der Stelle.
        anteil = abs(self.schub)
        hz, zyklus = self.zyklus(anteil)
        tempo_soll = self.tempo_max * anteil
        if self.ueberlast:
            tempo_soll *= w["ueberlast"]

        laeuft = anteil > 0.02 or abs(self.lenkung) > 0.02
        if laeuft:
            self.uhr += dt * hz
            while self.uhr >= 1.0:
                self.uhr -= 1.0
                self.gruppe_dran = (self.gruppe_dran + 1) % len(self.gruppen)
                self._gruppe_treten(self.gruppen[self.gruppe_dran],
                                    tempo_soll, zyklus)
        else:
            self.uhr = 0.0
            self._heimkehren(tempo_soll, zyklus)

        # 3. Notschritt: ein Bein, das zu weit schleppt, tritt ausser der
        #    Reihe. Ohne das reisst beim Drehen auf der Stelle irgendwann
        #    ein Bein von seinem Fuss ab.
        self._notschritte(tempo_soll, zyklus)

        # 4. Schwuenge vorantreiben, Aufsetzen melden.
        for b in self.beine:
            if b.schritt(dt):
                self._aufgesetzt(b, welt, klang, stoss)

        # 5. Und jetzt der Kern: der Rumpf folgt den Fuessen.
        self._rumpf_aus_fuessen(dt)

        # 6. Was sich daraus ergibt: gemessenes Tempo, Wanken, Atem.
        self._nachwirkungen(dt)
        self._regeln(dt, tempo_soll, laeuft)

    # ---- Schritte auswaehlen ---------------------------------------------
    def _laufrichtung(self, vorausschau: float) -> pygame.Vector2:
        """Wohin ein Schritt zielt. Nimmt die Drehung ein Stueck vorweg,
        damit die Fuesse in die Kurve greifen statt ihr nachzulaufen."""
        kurs = self.kurs_soll + (self.lenkung * K.WANDLER["dreh"]
                                 * vorausschau * K.GANG["dreh_greifen"])
        r = math.radians(kurs)
        richtung = pygame.Vector2(math.cos(r), math.sin(r))
        return richtung * (1.0 if self.schub >= 0 else -1.0)

    def _schrittweite(self, tempo_soll: float, zyklus: float) -> float:
        """Wie weit ein Fuss greift.

        Grundgedanke: der Rumpf kommt je Zyklus rund eine Schrittweite
        voran, also ist `tempo * zyklus` der richtige Ansatz. Genau stimmt
        das aber nicht - wie viel davon ankommt, haengt daran, wie viele
        Fuesse gerade tragen und wie alt ihre Standpunkte sind. Deshalb
        steht ein gemessener Faktor davor, den die Maschine selbst
        nachregelt (siehe `_regeln`).

        Und wenn die Weite nicht mehr in die Beine passt, wird die Maschine
        eben langsamer. Das ist keine Strafe, die jemand eingebaut hat,
        sondern die Folge davon, dass Beine eine Laenge haben.
        """
        return min(self.schritt_max, max(0.0, tempo_soll * zyklus * self.korrektur))

    def _ziel_fuer(self, b: Bein, tempo_soll: float, zyklus: float) -> pygame.Vector2:
        dauer = self._schwungdauer(tempo_soll)
        richtung = self._laufrichtung(dauer)
        weite = self._schrittweite(tempo_soll, zyklus)
        ruhe = b.ruhe_welt(self.pos, self.kurs_soll)
        # Waehrend der Fuss in der Luft ist, laeuft der Rumpf weiter. Wer
        # genau auf die Ruhelage zielt, setzt deshalb immer zu kurz auf.
        ausgleich = richtung * (tempo_soll * dauer * K.GANG["nachgreifen"])
        return ruhe + richtung * weite + ausgleich

    def _schwungdauer(self, tempo_soll: float) -> float:
        g = K.GANG
        anteil = min(1.0, tempo_soll / max(1.0, self.tempo_max))
        return g["schritt_dauer"] + (g["schritt_dauer_voll"]
                                     - g["schritt_dauer"]) * anteil

    def _hub(self, tempo_soll: float) -> float:
        g = K.GANG
        anteil = min(1.0, tempo_soll / max(1.0, self.tempo_max))
        klein, gross = g["hub_anteil"], g["hub_voll_anteil"]
        return self.reichweite * (klein + (gross - klein) * anteil)

    def _darf_treten(self, b: Bein) -> bool:
        """Es bleiben immer genug Fuesse am Boden.

        Die Bedingung ist hart und hat keine Ausnahme: wenn dieses Bein
        abhebt, muessen noch `stand_mindest` Fuesse stehen. Sonst traegt
        nichts mehr, und eine Maschine, die nichts traegt, hat auch keinen
        Grund, sich zu bewegen.

        Daraus folgt der Grenzfall von selbst: **mit einem einzigen heilen
        Bein geht gar nichts mehr.** Es kann nicht zugleich tragen und
        treten. Ohne diese Zeile huepft die Maschine auf ihrem letzten Bein
        davon - und zwar schneller als mit vieren, weil jeder Hupfer den
        ganzen Rumpf mitnimmt.
        """
        if not b.heil or not b.steht:
            return False
        return len(self.stehende) - 1 >= K.GANG["stand_mindest"]

    def _gruppe_treten(self, gruppe: int, tempo_soll: float,
                       zyklus: float) -> None:
        dauer = self._schwungdauer(tempo_soll)
        hub = self._hub(tempo_soll)
        for b in self.beine:
            if b.gruppe != gruppe or not self._darf_treten(b):
                continue
            ziel = self._ziel_fuer(b, tempo_soll, zyklus)
            if b.fuss.distance_to(ziel) < K.GANG["schritt_min"]:
                continue          # so kurz lohnt kein Schritt
            b.treten(ziel, dauer, hub)

    def _notschritte(self, tempo_soll: float, zyklus: float) -> None:
        grenze = self.schritt_max * K.GANG["zwang"]
        for b in self.beine:
            if not self._darf_treten(b):
                continue
            schleppe = b.schleppe(self.pos, self.kurs_soll)
            # Ein Bein darf nie ueber seine Reichweite hinaus gezerrt werden.
            reisst = b.fuss.distance_to(b.huefte_welt(self.pos, self.kurs)) \
                > b.reichweite * (1.0 - K.BEIN["knie_mindest"] * 2.0)
            if schleppe > grenze or reisst:
                b.treten(self._ziel_fuer(b, tempo_soll, zyklus),
                         self._schwungdauer(tempo_soll), self._hub(tempo_soll))

    def _heimkehren(self, tempo_soll: float, zyklus: float) -> None:
        """Im Stand kehren abgekommene Fuesse einzeln in die Ruhelage zurueck.

        Ohne das bliebe die Maschine nach dem Anhalten in der Spreizstellung
        stehen, in der der letzte Schritt sie hinterlassen hat.
        """
        schlimmstes, weiteste = None, K.GANG["schritt_min"] * 1.5
        for b in self.beine:
            if not self._darf_treten(b):
                continue
            s = b.schleppe(self.pos, self.kurs_soll)
            if s > weiteste:
                schlimmstes, weiteste = b, s
        if schlimmstes is not None:
            ruhe = schlimmstes.ruhe_welt(self.pos, self.kurs_soll)
            schlimmstes.treten(ruhe, self._schwungdauer(0.0), self._hub(0.0))

    # ---- Der Rumpf folgt --------------------------------------------------
    def _rumpf_aus_fuessen(self, dt: float) -> None:
        """Lage und Kurs des Rumpfes aus den stehenden Fuessen.

        Eine Ausgleichsrechnung: gesucht ist die Drehung und Verschiebung,
        die die Ruhelagen der stehenden Beine am besten auf ihre
        tatsaechlichen Fussstellungen abbildet. Bei einem einzigen Standbein
        ist die Drehung unbestimmt - dann bleibt der Kurs, wie er ist, und
        nur die Lage folgt.
        """
        stand = self.stehende
        if not stand:
            return                       # alles in der Luft: nichts traegt

        ruhe_mittel = pygame.Vector2()
        fuss_mittel = pygame.Vector2()
        for b in stand:
            ruhe_mittel += b.ruhe_lokal
            fuss_mittel += b.fuss
        ruhe_mittel /= len(stand)
        fuss_mittel /= len(stand)

        kurs_ziel = self.kurs
        if len(stand) >= 2:
            kreuz = summe = 0.0
            for b in stand:
                r = b.ruhe_lokal - ruhe_mittel
                f = b.fuss - fuss_mittel
                kreuz += r.x * f.y - r.y * f.x
                summe += r.x * f.x + r.y * f.y
            if abs(kreuz) > 1e-9 or abs(summe) > 1e-9:
                kurs_ziel = math.degrees(math.atan2(kreuz, summe))

        pos_ziel = fuss_mittel - _dreh(ruhe_mittel, kurs_ziel)

        zug = 1.0 - math.exp(-K.WANDLER["koerper_zug"] * dt)
        kurs_zug = 1.0 - math.exp(-K.WANDLER["kurs_zug"] * dt)
        self.pos += (pos_ziel - self.pos) * zug
        self.kurs += _winkel_diff(kurs_ziel, self.kurs) * kurs_zug

    def _nachwirkungen(self, dt: float) -> None:
        w = K.WANDLER
        # Gemessenes Tempo - nicht das befohlene. Das ist der Wert, den das
        # HUD zeigen soll, weil er die Wahrheit ueber die Maschine sagt.
        gefahren = self.pos.distance_to(self._vorher) / dt
        self.tempo_ist += (gefahren - self.tempo_ist) * min(1.0, dt * 6.0)
        self._vorher.update(self.pos)

        # Wanken: je mehr Beine fehlen oder in der Luft sind, desto schiefer
        # haengt der Rumpf. Faellt ohne Sonderregel an.
        heil = len(self.heile)
        fehlend = max(0, heil - len(self.stehende)) + (len(self.beine) - heil)
        ziel = fehlend * w["wanken"]
        self.wank += (ziel - self.wank) * min(1.0, dt * w["wanken_zug"])

        # Atem: der Rumpf senkt sich, wenn viele Fuesse tragen, und hebt
        # sich im Durchschwingen.
        traegt = len(self.stehende) / max(1, heil)
        ziel_h = (1.0 - traegt) * w["heben"]
        self.atem += (ziel_h - self.atem) * min(1.0, dt * w["heben_zug"])

    def _regeln(self, dt: float, tempo_soll: float, laeuft: bool) -> None:
        """Greift weiter, wenn die Maschine zu langsam ist, und kuerzer,
        wenn sie zu schnell ist.

        Der ganze Grund, warum es diese Regelung gibt und keine Formel:
        faellt ein Bein aus, tragen weniger Fuesse, und der Rumpf kommt je
        Zyklus weniger weit. Die Maschine greift dann von selbst weiter -
        bis die Beine nicht mehr hergeben, und dann ist sie eben langsam.
        Kein Sonderfall, keine Tabelle, ein Regelkreis.
        """
        g = K.GANG
        if not laeuft or tempo_soll < 1.0:
            return
        fehler = (tempo_soll - self.tempo_ist) / tempo_soll
        fehler = max(-0.5, min(0.5, fehler))
        self.korrektur *= 1.0 + fehler * g["regelung"] * dt
        self.korrektur = max(g["regel_min"], min(g["regel_max"], self.korrektur))

    # ---- Wenn ein Fuss aufsetzt --------------------------------------------
    def _aufgesetzt(self, b: Bein, welt, klang, stoss) -> None:
        """Ein Fuss ist unten. Das ist der Moment, den man hoeren und
        spueren soll - sonst wirkt der Gang wie eine Folie."""
        anteil = min(1.0, self.tempo_ist / max(1.0, self.tempo_max))
        kraft = K.WANDLER["stoss"] * (0.55 + 0.45 * anteil)
        if stoss is not None:
            stoss(kraft)
        if klang is not None:
            klang("schritt", 0.55 + 0.45 * anteil)
        if welt is not None:
            from .entities import wolke
            wolke(welt, b.fuss, int(4 + 5 * anteil), 60 + 40 * anteil,
                  0.42, K.C_MUTED_DK, 0, 1, "staub")
