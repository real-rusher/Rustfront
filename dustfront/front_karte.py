"""
DUSTFRONT - Die Front im Bild (seit 0.34.131)
============================================

Was man von der Front sieht (die Logik steht in front.py):

* **am Boden**: jeder Eroberungspunkt als Kreis in der Farbe seines
  Besitzers, der Bogen zeigt den Stand, in der Mitte eine Fahne; die Basen
  haben ihre Fahne auch,
* **oben in der Anzeige**: eine Leiste mit allen Punkten (A, B, C ...), und
  wer in einem Kreis steht, sieht, wie weit er ist,
* **auf den Karten** (Minikarte, Nachschub, Einstieg): die Punkte mit
  Buchstaben und Farbe,
* **nach dem Tod** die Einstiegskarte wie in Battlefield: links alle
  Einstiege der Seite (Basen immer, Punkte, die ganz der Seite gehoeren und
  nicht umkaempft sind), rechts die Karte zum Anklicken. Wenn die Zeit um
  ist, steigt man am gewaehlten ein; die Wahl gilt, bis man eine andere
  trifft.
"""

from __future__ import annotations

import math

import pygame

from . import config as K
from .font import SCHRIFT

F = K.FRONT
NEUTRAL = (196, 186, 160)


def seiten_farbe(team: int):
    if 0 <= team < 2:
        return K.TEAMS["kombi"][team]["hud"]
    return NEUTRAL


def punkt_farbe(p):
    """Farbe des Punktes: die des Besitzers; neutral hell."""
    return seiten_farbe(p.besitzer)


def zeichen_malen(ziel, p, mitte, gross: float, mit_name: bool = False, m: float = 1.0) -> None:
    """Ein Punkt auf einer Karte: Kreis in der Besitzerfarbe, der Stand als
    Bogen in der Farbe, zu der er zieht, der Buchstabe darin."""
    r = max(3, int(gross))
    farbe = punkt_farbe(p)
    pygame.draw.circle(ziel, (16, 11, 8), mitte, r + max(1, int(m)))
    pygame.draw.circle(ziel, farbe if p.besitzer >= 0 else (60, 54, 44), mitte, r)
    if p.anteil > 0.01 and not p.gehoert(p.zieht):
        kasten = pygame.Rect(mitte[0] - r - 1, mitte[1] - r - 1, 2 * r + 3, 2 * r + 3)
        pygame.draw.arc(ziel, seiten_farbe(p.zieht), kasten, math.pi / 2 - math.tau * p.anteil,
                        math.pi / 2, max(1, int(2 * m)))
    groesse = max(1, int(round(m)))
    SCHRIFT.zeichnen(ziel, p.buchstabe, mitte[0], mitte[1] - 3 * groesse,
                     (16, 11, 8) if p.besitzer >= 0 else K.C_CREAM, groesse, ausrichtung="mitte")
    if mit_name:
        SCHRIFT.zeichnen(ziel, p.name, mitte[0], mitte[1] + r + 2 * groesse, K.C_CREAM, groesse,
                         ausrichtung="mitte")


def fahne_malen(ziel, mitte, farbe, gross: float) -> None:
    """Eine kleine Fahne am Mast (Basen auf der Karte)."""
    x, y = int(mitte[0]), int(mitte[1])
    h = max(5, int(gross * 2.2))
    pygame.draw.line(ziel, (16, 11, 8), (x, y), (x, y - h), max(1, int(gross / 3)))
    pygame.draw.polygon(ziel, farbe, [(x + 1, y - h), (x + 1 + int(gross * 1.6), y - h + int(gross * 0.6)),
                                      (x + 1, y - h + int(gross * 1.2))])


class FrontKarteTeil:
    """Was das Gefecht von der Front zeigt. Ein Anteil wie SchlachtTeil."""

    # ---- Am Boden -----------------------------------------------------------
    def front_boden_zeichnen(self, flaeche, ebene: int, ecke) -> None:
        if not self.front_an or ebene != 0:
            return
        w, h = flaeche.get_size()
        rad = F["radius"]
        z = K.ZONE
        for p in self.front_punkte():
            m = p.pos - ecke
            if not (-rad < m.x < w + rad and -rad < m.y < h + rad):
                continue
            farbe = punkt_farbe(p)
            # Der Bogen: wie weit die Seite ist, zu der er gerade zieht.
            bogen_farbe = seiten_farbe(p.zieht) if not p.gehoert(p.zieht) else farbe
            self.renderer.kreis_zone(flaeche, m, rad, bogen_farbe if p.besitzer < 0 else farbe,
                                     0.0 if p.gehoert(p.besitzer) else p.anteil,
                                     self._zeit / z["puls"], 2, 18)
            self._fahne_boden(flaeche, m, farbe, p.buchstabe)
        for b in self.front_basen():
            m = b.pos - ecke
            if -60 < m.x < w + 60 and -60 < m.y < h + 60:
                self._fahne_boden(flaeche, m, seiten_farbe(b.team), "")

    def _fahne_boden(self, flaeche, m, farbe, buchstabe: str) -> None:
        """Ein Fahnenmast mit wehender Fahne (am Boden, ohne Perspektive)."""
        x, y = int(m.x), int(m.y)
        pygame.draw.ellipse(flaeche, (20, 16, 12), (x - 6, y - 2, 12, 5))
        pygame.draw.line(flaeche, (30, 26, 22), (x, y), (x, y - 30), 2)
        pygame.draw.line(flaeche, (150, 144, 130), (x - 1, y), (x - 1, y - 30), 1)
        welle = math.sin(self._zeit * 4.0 + x * 0.01) * 2.0
        fahne = [(x + 1, y - 30), (x + 17, y - 26 + welle), (x + 1, y - 21)]
        pygame.draw.polygon(flaeche, farbe, fahne)
        pygame.draw.polygon(flaeche, (16, 11, 8), fahne, 1)
        if buchstabe:
            SCHRIFT.zeichnen(flaeche, buchstabe, x + 7, y - 28, (16, 11, 8), 1, ausrichtung="mitte")

    # ---- Leiste oben ----------------------------------------------------------
    def front_leiste(self, ziel) -> None:
        """Alle Punkte oben in der Mitte; darunter, wenn man in einem steht,
        wie weit er ist; und die letzten Meldungen (Punkt genommen)."""
        if not self.front_an or self.vorbei:
            return
        punkte = sorted(self.front_punkte(), key=lambda p: p.buchstabe)
        if not punkte:
            return
        breite = 15
        x0 = K.GAME_W // 2 - len(punkte) * breite // 2
        y = 32                    # unter dem Stand der Mannschaften (Balken und Zahlen)
        for i, p in enumerate(punkte):
            r = pygame.Rect(x0 + i * breite, y, breite - 2, 12)
            pygame.draw.rect(ziel, (16, 11, 8), r.inflate(2, 2))
            pygame.draw.rect(ziel, (44, 38, 30), r)
            if p.besitzer >= 0:
                pygame.draw.rect(ziel, seiten_farbe(p.besitzer), r)
            elif p.anteil > 0.01:
                teil = r.copy()
                teil.height = max(1, int(r.height * p.anteil))
                teil.bottom = r.bottom
                pygame.draw.rect(ziel, seiten_farbe(p.zieht), teil)
            if p.besitzer >= 0 and not p.gehoert(p.besitzer):
                teil = r.copy()
                teil.height = max(1, int(r.height * (1.0 - p.anteil)))
                pygame.draw.rect(ziel, (44, 38, 30), teil)
            umkaempft = p.da[0] > 0 and p.da[1] > 0
            if umkaempft and int(self._zeit * 3) % 2 == 0:
                pygame.draw.rect(ziel, K.C_CREAM, r.inflate(2, 2), 1)
            SCHRIFT.zeichnen(ziel, p.buchstabe, r.centerx, r.y + 3,
                             (16, 11, 8) if p.besitzer >= 0 else K.C_CREAM, 1, ausrichtung="mitte")
        ich = self.ich
        if ich is not None and ich.lebt and int(ich.ebene) == 0:
            for p in punkte:
                if ich.pos.distance_to(p.pos) <= F["radius"]:
                    self._fortschritt(ziel, p, ich.team, y + 16)
                    break
        jetzt = self.welt.zeit
        meldungen = [m for m in self.__dict__.get("_front_meldungen", ()) if jetzt - m[0] < 4.0]
        for j, (_t, text, team) in enumerate(meldungen[-2:]):
            SCHRIFT.zeichnen(ziel, text, K.GAME_W // 2, y + 38 + j * 10, seiten_farbe(team), 1,
                             ausrichtung="mitte")

    def _fortschritt(self, ziel, p, team: int, y: int) -> None:
        r = pygame.Rect(K.GAME_W // 2 - 80, y, 160, 6)
        pygame.draw.rect(ziel, (16, 11, 8), r.inflate(2, 2))
        pygame.draw.rect(ziel, (44, 38, 30), r)
        # Von der Mitte aus: links ROT, rechts BLAU.
        mitte = r.centerx
        breit = int(r.width / 2 * p.anteil)
        if p.zieht == 0:
            pygame.draw.rect(ziel, seiten_farbe(0), (mitte - breit, r.y, breit, r.height))
        elif p.zieht == 1:
            pygame.draw.rect(ziel, seiten_farbe(1), (mitte, r.y, breit, r.height))
        pygame.draw.line(ziel, K.C_CREAM, (mitte, r.y - 1), (mitte, r.bottom), 1)
        if p.da[0] > 0 and p.da[1] > 0:
            text = "%s %s - UMKÄMPFT" % (p.buchstabe, p.name)
        elif p.gehoert(team):
            text = "%s %s - GEHALTEN" % (p.buchstabe, p.name)
        elif p.da[team] > 0:
            text = "%s %s - WIRD EINGENOMMEN" % (p.buchstabe, p.name)
        else:
            text = "%s %s" % (p.buchstabe, p.name)
        SCHRIFT.zeichnen(ziel, text, mitte, r.bottom + 3, K.C_CREAM, 1, ausrichtung="mitte")

    # ---- Auf den Karten -------------------------------------------------------
    def front_auf_karte(self, ziel, punkt, mass_px: float, m: float = 1.0, namen: bool = False) -> None:
        """Punkte und Basen auf eine Karte: `punkt(pos)` rechnet in deren
        Pixel um, `mass_px` ist ein Welt-Pixel dort."""
        if not self.front_an:
            return
        for b in self.front_basen():
            fahne_malen(ziel, punkt(b.pos), seiten_farbe(b.team), 3.0 * m)
        for p in self.front_punkte():
            gross = max(4.0 * m, F["radius"] * mass_px * 0.55)
            zeichen_malen(ziel, p, punkt(p.pos), gross, namen, m)

    # ---- Einstiegskarte nach dem Tod ----------------------------------------------
    @property
    def einstieg_offen(self) -> bool:
        ich = self.ich
        return bool(self.front_an and ich is not None and not ich.lebt
                    and not getattr(ich, "am_boden", False) and not self.vorbei
                    and not self.regeln.get("runden") and not self.regeln.get("revive")
                    and 0 <= getattr(ich, "team", -1) < 2)

    def _einstieg_liste(self) -> list:
        ich = self.ich
        return self.einstiege(ich.team) if ich is not None else []

    def _einstieg_gewaehlt(self) -> str:
        ich = self.ich
        wahl = str(getattr(ich, "einstieg_wahl", "") or "")
        frei = [kenn for kenn, _o, _n, ok, _g in self._einstieg_liste() if ok]
        return wahl if wahl in frei else self.einstieg_vorgabe(ich.team)

    def einstieg_waehlen(self, kennung: str) -> None:
        """Waehlen und - beim Gast - dem Gastgeber sagen."""
        ich = self.ich
        if ich is None:
            return
        ich.einstieg_wahl = kennung
        if not self.ist_gastgeber and getattr(self, "gast", None) is not None:
            self.gast.senden({"t": "einstieg", "wahl": kennung})
        self.welt.klang("aufheben", 0.4)

    @staticmethod
    def _einstieg_zeile(i: int) -> pygame.Rect:
        return pygame.Rect(16, 62 + i * 17, 206, 15)

    def einstieg_ereignis(self, ev) -> bool:
        """Tasten und Maus auf der Einstiegskarte. True: verbraucht."""
        if not self.einstieg_offen or getattr(self, "belohnung_offen", False):
            return False
        liste = self._einstieg_liste()
        frei = [i for i, e in enumerate(liste) if e[3]]
        if ev.type == pygame.KEYDOWN:
            if pygame.K_1 <= ev.key <= pygame.K_9 and ev.key - pygame.K_1 < len(liste):
                e = liste[ev.key - pygame.K_1]
                if e[3]:
                    self.einstieg_waehlen(e[0])
                return True
            if ev.key in (pygame.K_UP, pygame.K_w, pygame.K_DOWN, pygame.K_s) and frei:
                jetzt = self._einstieg_gewaehlt()
                stellen = [liste[i][0] for i in frei]
                j = stellen.index(jetzt) if jetzt in stellen else 0
                j = (j + (-1 if ev.key in (pygame.K_UP, pygame.K_w) else 1)) % len(stellen)
                self.einstieg_waehlen(stellen[j])
                return True
            return False
        if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
            maus = self.app.zu_spiel(ev.pos)
            for i, e in enumerate(liste):
                if self._einstieg_zeile(i).collidepoint(maus) and e[3]:
                    self.einstieg_waehlen(e[0])
                    return True
            feld = self._karte_feld()
            if feld.collidepoint(maus):
                welt = self._karte_zu_welt(maus)
                beste = min((e for e in liste if e[3]), key=lambda e: e[1].distance_to(welt), default=None)
                if beste is not None and beste[1].distance_to(welt) < 900.0:
                    self.einstieg_waehlen(beste[0])
                return True
            return False
        return False

    def einstieg_zeichnen(self, ziel) -> None:
        if not self.einstieg_offen or getattr(self, "belohnung_offen", False):
            return
        ich = self.ich
        schleier = self.__dict__.get("_ein_schleier")
        if schleier is None:
            schleier = self._ein_schleier = pygame.Surface((K.GAME_W, K.GAME_H), pygame.SRCALPHA)
            schleier.fill((8, 6, 4, 222))
        ziel.blit(schleier, (0, 0))
        SCHRIFT.zeichnen(ziel, "EINSTIEG WÄHLEN", 16, 12, K.C_AMBER, 2)
        rest = max(0.0, getattr(ich, "wieder_in", 0.0))
        SCHRIFT.zeichnen(ziel, "GEFALLEN - EINSTIEG IN %d" % int(rest + 0.99), 16, 34,
                         K.C_RED if rest > 0.5 else K.C_TEAL, 1)
        SCHRIFT.zeichnen(ziel, "BASIS: IMMER   PUNKT: WENN GANZ EUER", 16, 46, K.C_MUTED, 1)
        gewaehlt = self._einstieg_gewaehlt()
        liste = self._einstieg_liste()
        punkte = {"p%d" % p.nr: p for p in self.front_punkte()}
        for i, (kenn, _ort, name, frei, grund) in enumerate(liste):
            r = self._einstieg_zeile(i)
            aktiv = kenn == gewaehlt
            pygame.draw.rect(ziel, (40, 30, 20) if aktiv else (20, 15, 11), r)
            pygame.draw.rect(ziel, K.C_AMBER if aktiv else (70, 56, 40), r, 1)
            farbe = K.C_CREAM if frei else K.C_MUTED_DK
            art = "BASIS" if kenn[0] == "b" else ("PUNKT " + punkte[kenn].buchstabe if kenn in punkte else "")
            SCHRIFT.zeichnen(ziel, "%d  %s" % (i + 1, name), r.x + 5, r.y + 4, farbe, 1)
            SCHRIFT.zeichnen(ziel, grund or art, r.right - 5, r.y + 4,
                             K.C_RED if grund else (K.C_TEAL if aktiv else K.C_MUTED), 1,
                             ausrichtung="rechts")
        r = self.belohnung_karte_rect()
        pygame.draw.rect(ziel, (84, 66, 48), r, 1)
        feld = self._karte_feld()
        maus = self.app.zu_spiel(pygame.mouse.get_pos())
        self._einstieg_karte(ziel, feld, 1.0, maus, ich, gewaehlt, liste)
        if hasattr(self.app, "hoch_auflegen") and self.app.stapel and self.app.stapel[-1] is self:
            self.app.hoch_auflegen(feld, lambda f, mass: self._einstieg_karte(
                f, f.get_rect(), mass,
                ((maus[0] - feld.x) * f.get_width() / float(max(1, feld.width)),
                 (maus[1] - feld.y) * f.get_height() / float(max(1, feld.height))),
                ich, gewaehlt, liste))
        SCHRIFT.zeichnen(ziel, "[1-9] ODER KLICK: EINSTIEG WÄHLEN - WENN DIE ZEIT UM IST, GEHT ES LOS",
                         K.GAME_W // 2, K.GAME_H - 18, K.C_MUTED, 1, ausrichtung="mitte")

    def _einstieg_karte(self, ziel, r, m: float, maus, ich, gewaehlt: str, liste) -> None:
        """Die Karte der Nachschubtafel, darauf die Einstiege: frei mit
        Ring, der gewaehlte pulsierend, unter der Maus hervorgehoben."""
        # Ohne Wahl im Nachschub: die Karte ist nur Karte (keine Abwurfsperre).
        wahl, self.belohnung_wahl = self.belohnung_wahl, -1
        try:
            self._karte_malen(ziel, r, m, (-999, -999), ich)
        finally:
            self.belohnung_wahl = wahl
        e = self.welt.ebene(0)
        f = r.width / float(e.pixel_breite)
        mm = max(1.0, float(m))

        def punkt(pos):
            return (int(r.x + pos.x * f), int(r.y + pos.y * f))

        alt_clip = ziel.get_clip()
        ziel.set_clip(r.clip(alt_clip) if alt_clip else r)
        unter = None
        if r.collidepoint(maus):
            welt = pygame.Vector2((maus[0] - r.x) / f, (maus[1] - r.y) / f)
            frei = [x for x in liste if x[3]]
            if frei:
                unter = min(frei, key=lambda x: x[1].distance_to(welt))
                if unter[1].distance_to(welt) > 900.0:
                    unter = None
        puls = 0.5 + 0.5 * math.sin(self._zeit * 6.0)
        for kenn, ort, name, frei, _grund in liste:
            q = punkt(ort)
            gross = int((9 + (3 * puls if kenn == gewaehlt else 0)) * mm)
            if kenn == gewaehlt:
                pygame.draw.circle(ziel, K.C_AMBER, q, gross, max(2, int(2 * mm)))
            elif frei:
                pygame.draw.circle(ziel, K.C_TEAL if unter and unter[0] == kenn else K.C_CREAM,
                                   q, gross, max(1, int(mm)))
            groesse = max(1, int(round(mm)))
            if kenn == gewaehlt or (unter is not None and unter[0] == kenn):
                SCHRIFT.zeichnen(ziel, name, q[0], q[1] + gross + 2 * groesse,
                                 K.C_AMBER if kenn == gewaehlt else K.C_TEAL, groesse, ausrichtung="mitte")
        ziel.set_clip(alt_clip)


class WerferKarteTeil:
    """Der aufgebaute Werfer (seit 0.34.134, gewuenscht): man sieht eine
    Karte wie im Nachschub (TAB) und schiesst ueber die halbe Karte - der
    Kreis zeigt, wie weit er reicht, der Zeiger, wo die Salve fallen soll und
    ob es dort ein Ziel gibt. Ein Klick feuert."""

    def _werfer_eigen(self):
        ich = self.ich
        b = getattr(ich, "fahrzeug", None) if ich is not None else None
        if b is None and ich is not None and not self.ist_gastgeber:
            # Beim Gast kennt nur das Fahrzeug seinen Fahrer (fahrer_nummer) -
            # bis 0.34.135 kam die Karte darum nur beim Gastgeber.
            b = next((x for x in getattr(self, "fahrzeuge", ())
                      if getattr(x, "fahrer_nummer", -1) == ich.nummer), None)
        if (b is None or b.art != "werfer" or not ich.lebt or b.kaputt or b.phase != 2):
            return None
        if getattr(self, "belohnung_offen", False) or self.menue is not None or self.vorbei:
            return None
        return b

    @staticmethod
    def werfer_karte_rect() -> pygame.Rect:
        return pygame.Rect(150, 40, 474, 292)

    def _werfer_masse(self):
        e = self.welt.ebene(0)
        r = self.werfer_karte_rect()
        f = min(r.width / float(e.pixel_breite), r.height / float(e.pixel_hoehe))
        breit, hoch = e.pixel_breite * f, e.pixel_hoehe * f
        return pygame.Rect(int(r.x + (r.width - breit) / 2), int(r.y + (r.height - hoch) / 2),
                           int(breit), int(hoch)), f

    def werfer_karte_ziel(self):
        """Wohin der Zeiger auf der Karte zeigt (Welt), oder None."""
        if self._werfer_eigen() is None:
            return None
        feld, f = self._werfer_masse()
        maus = self.app.zu_spiel(pygame.mouse.get_pos())
        if not feld.collidepoint(maus):
            return None
        return pygame.Vector2((maus[0] - feld.x) / f, (maus[1] - feld.y) / f)

    def _werfer_zonen_bild(self, zonen: list, feld, f: float):
        """Die Zielzonen als eine Flaeche (seit 0.34.135): tuerkis gefuellt,
        mit hellem Rand nur aussen - Kreise, die sich ueberlappen, verschmelzen
        zu einem Gebiet. Tuerkis, damit sie neben dem orangen Reichweitenkreis
        nicht verwechselt wird. Neu gemalt nur, wenn die Zonen neu sind."""
        alt = self.__dict__.get("_wzn_bild")
        if alt is not None and alt[0] is zonen and alt[1] == feld.size:
            return alt[2]
        kreise = [((int(o.x * f), int(o.y * f)), max(3, int(r * f))) for o, r, _a in zonen]
        flaeche = pygame.Surface(feld.size)
        flaeche.fill((0, 0, 0))
        for m, r in kreise:
            pygame.draw.circle(flaeche, (30, 120, 112), m, r)
        flaeche.set_colorkey((0, 0, 0))
        flaeche.set_alpha(80)
        rand = pygame.Surface(feld.size)
        rand.fill((0, 0, 0))
        for m, r in kreise:
            pygame.draw.circle(rand, (120, 240, 220), m, r)
        for m, r in kreise:
            pygame.draw.circle(rand, (0, 0, 0), m, max(1, r - 2))
        rand.set_colorkey((0, 0, 0))
        rand.set_alpha(220)
        fertig = pygame.Surface(feld.size, pygame.SRCALPHA)
        fertig.blit(flaeche, (0, 0))
        fertig.blit(rand, (0, 0))
        self._wzn_bild = (zonen, feld.size, fertig)
        return fertig

    def werfer_karte_zeichnen(self, ziel) -> None:
        b = self._werfer_eigen()
        if b is None:
            return
        feld, f = self._werfer_masse()
        pygame.draw.rect(ziel, (8, 6, 4), feld.inflate(6, 6))
        pygame.draw.rect(ziel, (84, 66, 48), feld.inflate(6, 6), 1)
        wahl, self.belohnung_wahl = getattr(self, "belohnung_wahl", -1), -1
        try:
            self._karte_malen(ziel, feld, 1.0, (-999, -999), self.ich)
        finally:
            self.belohnung_wahl = wahl
        alt_clip = ziel.get_clip()
        ziel.set_clip(feld)

        def punkt(pos):
            return (int(feld.x + pos.x * f), int(feld.y + pos.y * f))
        s = K.WERFER["salve"]
        mitte = punkt(b.rohr_mitte())
        weit = int(self.werfer_weite() * f)
        nah = int(s["nah"] * f)
        kreis = pygame.Surface(feld.size, pygame.SRCALPHA)
        m_ = (mitte[0] - feld.x, mitte[1] - feld.y)
        pygame.draw.circle(kreis, (236, 128, 40, 26), m_, weit)
        pygame.draw.circle(kreis, (236, 128, 40, 200), m_, weit, 2)
        pygame.draw.circle(kreis, (200, 60, 40, 160), m_, max(2, nah), 1)
        ziel.blit(kreis, feld.topleft)
        team = getattr(self.ich, "team", -1)
        zonen = self.werfer_zonen(team) if team in (0, 1) else []
        ziel.blit(self._werfer_zonen_bild(zonen, feld, f), feld.topleft)
        for ort, _r, art in zonen:
            if art == "feind":
                q = punkt(ort)
                pygame.draw.circle(ziel, K.C_RED, q, 3)
                pygame.draw.circle(ziel, (16, 11, 8), q, 3, 1)
        maus = self.app.zu_spiel(pygame.mouse.get_pos())
        if feld.collidepoint(maus):
            # Beim Gast selbst geprueft (seit 0.34.135): sein Zeiger kommt beim
            # Gastgeber spaeter an, die Anzeige soll trotzdem sofort stimmen.
            wpunkt = pygame.Vector2((maus[0] - feld.x) / f, (maus[1] - feld.y) / f)
            grund = self.werfer_pruefen(b, team, wpunkt) if team in (0, 1) else b.ziel_grund
            gut = grund == 0
            farbe = K.C_TEAL if gut else K.C_RED
            pygame.draw.circle(ziel, farbe, maus, max(3, int(s["streu"] * f)), 1)
            pygame.draw.line(ziel, farbe, (maus[0] - 5, maus[1]), (maus[0] + 5, maus[1]))
            pygame.draw.line(ziel, farbe, (maus[0], maus[1] - 5), (maus[0], maus[1] + 5))
            text = ("FEUER: KLICK" if b.bereit else "LÄDT ...") if gut else \
                {1: "ZU NAH", 2: "ZU WEIT", 3: "AUSSERHALB DER ZONEN"}.get(grund, "")
            SCHRIFT.zeichnen(ziel, text, maus[0], maus[1] - 16, farbe, 1, ausrichtung="mitte")
        ziel.set_clip(alt_clip)
        SCHRIFT.zeichnen(ziel, "WERFER - AUFGEBAUT", feld.x, feld.y - 12, K.C_AMBER, 1)
        SCHRIFT.zeichnen(ziel, "TÜRKIS: ZIELZONEN   ORANGE: REICHWEITE   ROT: ENTDECKTE GEGNER   RECHTS: ABBAUEN",
                         feld.right, feld.bottom + 6, K.C_MUTED, 1, ausrichtung="rechts")
