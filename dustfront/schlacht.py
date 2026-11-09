"""
DUSTFRONT - SCHLACHT: Dropzonen, Abwuerfe und Belohnungen (seit 0.34.96)
=======================================================================

Gewuenscht nach der ersten Runde SCHLACHT:

* Statt dass Fahrzeuge einfach an der Basis erscheinen, gibt es dort
  markierte **Dropzonen** (Vorbild: die Evakuierungszone aus XCOM 2). Wird
  ein Fahrzeug fuer eine Zone faellig, zaehlt sie herunter und pulsiert,
  und dann sinkt es an einem **Fallschirm** herunter. In der Luft wirft es
  einen Schatten am Boden, der waechst, je tiefer es kommt - so sieht man,
  ob es noch faellt oder schon steht.
* Ein **Belohnungsmenue** auf TAB (die Rangliste ist dort Nebensache):
  mit Punkten kauft man einmalige Dropzonen fuer Fahrzeuge auf freiem
  Gelaende, Abwuerfe mit Munition oder Medkits und den Ueberflug einer
  grossen Aufklaerungsdrohne, die einen Teil der Karte aufdeckt und die
  Gegner dort lange markiert.
* Punkte: 1 je Abschuss, 5 je zerstoertem Fahrzeug, 5 je Kamerad, dem man
  aufhilft (K.SCHLACHT punkte).

Nur der Gastgeber entscheidet; der Gast bekommt Zonen, Abwuerfe,
Ueberfluege und seine Punkte mit der Weltmeldung ("sl") und schickt einen
Kauf als Nachricht ("belohnung").
"""

from __future__ import annotations

import math

import pygame

from . import config as K
from . import fahrzeug as fahrzeug_modul
from .font import SCHRIFT

S = K.SCHLACHT


class Dropzone:
    """Eine markierte Stelle, an der Nachschub landet."""

    _naechste = 0

    def __init__(self, pos, team: int, art: str, winkel: float,
                 einmalig: bool = False) -> None:
        Dropzone._naechste += 1
        self.kennung = Dropzone._naechste
        self.pos = pygame.Vector2(pos)
        self.team = int(team)
        self.art = art               # buggy, panzer, panzerwagen, munition, medkit
        self.winkel = float(winkel)
        self.einmalig = einmalig
        self.rest = -1.0             # Sekunden bis zum Abwurf, -1: nichts faellig
        self.fahrzeug = None         # was hier gelandet ist und noch lebt


class Abwurf:
    """Was gerade am Fallschirm herunterkommt."""

    def __init__(self, zone: Dropzone) -> None:
        self.zone = zone
        self.pos = pygame.Vector2(zone.pos)
        self.art = zone.art
        self.team = zone.team
        self.winkel = zone.winkel
        self.hoehe = S["abwurf"]["hoehe"]
        self.alter = 0.0
        self.kennung = zone.kennung


class Ueberflug:
    """Die grosse Aufklaerungsdrohne: fliegt quer ueber den gewaehlten Punkt
    und markiert, was in ihrem Kreis steht."""

    def __init__(self, ziel, team: int, fraktion: str, breite: float) -> None:
        a = S["aufklaerung"]
        self.ziel = pygame.Vector2(ziel)
        self.team = team
        self.fraktion = fraktion
        richtung = pygame.Vector2(1 if team == 0 else -1, 0)
        self.start = self.ziel - richtung * a["anflug"]
        self.ende = self.ziel + richtung * a["anflug"]
        self.alter = 0.0
        self.dauer = a["dauer"]

    @property
    def pos(self) -> pygame.Vector2:
        return self.start.lerp(self.ende, min(1.0, self.alter / self.dauer))


class SchlachtTeil:
    """Was das Gefecht in SCHLACHT zusaetzlich tut. Ein Anteil wie BotTeil."""

    # ---- Aufbau ---------------------------------------------------------
    def _schlacht_anlegen(self) -> None:
        self.dropzonen: list = []
        self.abwuerfe: list = []
        self.ueberfluege: list = []
        self.belohnung_offen = False
        self.belohnung_wahl = 0
        self._sl_meldung = ""

    def dropzonen_anlegen(self) -> None:
        """Je Basis eine Zone fuer jedes Fahrzeug aus K.SCHLACHT fahrzeuge -
        dorthin, wo es frei ist und der Weg zur Mitte offen. Zum Rundenstart
        fallen gleich alle (kurzer Vorlauf)."""
        self.dropzonen = []
        self.abwuerfe = []
        self.ueberfluege = []
        for team in range(2):
            for art, anzahl in S["fahrzeuge"]:
                for _ in range(anzahl):
                    platz = self._fahrzeug_platz_bei(art, self.schlacht_basis(team),
                                                     S["fahrzeug_umkreis"],
                                                     abstand_zonen=True)
                    if platz is None:
                        continue
                    pos, winkel = platz
                    zone = Dropzone(pos, team, art, winkel)
                    zone.rest = S["abwurf"]["start"]
                    self.dropzonen.append(zone)

    # ---- Ablauf (Gastgeber) ------------------------------------------------
    def schlacht_schritt(self, dt: float) -> None:
        if not self.schlacht or not self.ist_gastgeber:
            return
        a = S["abwurf"]
        for zone in list(self.dropzonen):
            if zone.fahrzeug is not None:
                b = zone.fahrzeug
                if not b.lebt or b not in self.fahrzeuge:
                    zone.fahrzeug = None
                    if not zone.einmalig:
                        zone.rest = b.werte["neu_nach"]
                continue
            if zone.rest > 0.0:
                zone.rest -= dt
                if zone.rest <= 0.0:
                    zone.rest = 0.0
                    self.abwuerfe.append(Abwurf(zone))
                    self.welt.klang("drohne", 0.6, zone.pos, 0)
        for ab in list(self.abwuerfe):
            ab.alter += dt
            ab.hoehe -= a["sinken"] * dt
            if ab.hoehe <= 0.0:
                self.abwuerfe.remove(ab)
                self._abwurf_landet(ab)
        for ue in list(self.ueberfluege):
            ue.alter += dt
            self._ueberflug_markieren(ue)
            if ue.alter >= ue.dauer:
                self.ueberfluege.remove(ue)

    def _abwurf_landet(self, ab: Abwurf) -> None:
        from .entities import wolke
        w = self.welt
        zone = ab.zone
        wolke(w, ab.pos, 26, 160, 0.9, K.C_SAND_KORN, 0, 2, "bodenstaub", 360, 0)
        w.ruckeln(2.5, "sturz", ab.pos, 0)
        w.klang("buggy_tuer", 0.9, ab.pos, 0)
        if ab.art in ("munition", "medkit"):
            from .mehrspieler import KampfBeute
            for i in range(S["abwurf"]["kisten"]):
                p = ab.pos + pygame.Vector2(14, 0).rotate(i * 360.0 / S["abwurf"]["kisten"])
                w.dazu(KampfBeute(p, ab.art, 0, self.kaempfer))
            if zone in self.dropzonen:
                self.dropzonen.remove(zone)
            return
        b = fahrzeug_modul.neu(ab.art, ab.pos, 0, ab.winkel)
        w.dazu(b)
        if hasattr(b, "aufbau"):
            b.aufbau = b.winkel
        b.start = (pygame.Vector2(ab.pos), 0, ab.winkel)
        b.basis_team = zone.team
        b.dropzone = zone
        self.fahrzeuge.append(b)
        zone.fahrzeug = b
        if zone.einmalig and zone in self.dropzonen:
            # Die gekaufte Zone gilt einmal; danach verschwindet sie.
            self.dropzonen.remove(zone)

    def _ueberflug_markieren(self, ue: Ueberflug) -> None:
        from . import ausruestung
        a = S["aufklaerung"]
        p = ue.pos
        for k in self.kaempfer.values():
            if k.lebt and k.fraktion != ue.fraktion and k.pos.distance_to(p) <= a["radius"]:
                ausruestung.markieren(k, ue.fraktion)
                k.markiert_rest = max(k.markiert_rest, a["markiert"])

    # ---- Punkte -------------------------------------------------------------
    def schlacht_punkte(self, k, wie_viel: int) -> None:
        if self.schlacht and k is not None and not getattr(k, "ist_bot", False):
            k.schlacht_punkte = getattr(k, "schlacht_punkte", 0) + int(wie_viel)

    # ---- Kaufen ------------------------------------------------------------
    @staticmethod
    def belohnungen() -> list:
        return list(S["belohnungen"])

    def belohnung_pruefen(self, k, was: str, punkt) -> str:
        """Leer, wenn der Kauf geht - sonst warum nicht."""
        d = dict((n, (kosten, text)) for n, kosten, text in S["belohnungen"])
        if was not in d:
            return "UNBEKANNT"
        if getattr(k, "schlacht_punkte", 0) < d[was][0]:
            return "ZU WENIG PUNKTE"
        e = self.welt.ebene(0)
        if not (0 <= punkt.x < e.pixel_breite and 0 <= punkt.y < e.pixel_hoehe):
            return "AUSSERHALB DER KARTE"
        if was == "aufklaerung":
            return ""
        feind = self.schlacht_basis(1 - k.team) if k.team in (0, 1) else None
        if feind is not None and punkt.distance_to(feind) < S["abwurf"]["sperre_basis"]:
            return "ZU NAH AN DER FEINDLICHEN BASIS"
        if was in ("buggy", "panzer", "panzerwagen"):
            probe = fahrzeug_modul.neu(was, punkt, 0)
            probe.welt = self.welt
            if not probe.passt(punkt, 0.0):
                return "KEIN FREIES GELÄNDE"
            netz = self.welt.fahrwege
            if netz.gebiet_bei(0, punkt) < 0:
                return "KEIN FREIES GELÄNDE"
        elif not self.welt.frei(punkt, 14.0, 0):
            return "KEIN FREIER BODEN"
        return ""

    def belohnung_kaufen(self, k, was: str, punkt) -> str:
        """Beim Gastgeber: pruefen, Punkte abziehen, ausfuehren."""
        punkt = pygame.Vector2(punkt)
        grund = self.belohnung_pruefen(k, was, punkt)
        if grund:
            return grund
        kosten = next(c for n, c, _t in S["belohnungen"] if n == was)
        k.schlacht_punkte -= kosten
        if was == "aufklaerung":
            self.ueberfluege.append(Ueberflug(punkt, k.team, k.fraktion,
                                              self.welt.ebene(0).pixel_breite))
            self.welt.klang("drohne", 1.0, punkt, 0)
            return ""
        zone = Dropzone(punkt, k.team, was, 0.0, einmalig=True)
        zone.rest = S["abwurf"]["vorlauf_kauf"]
        self.dropzonen.append(zone)
        return ""

    # ---- Netz -----------------------------------------------------------------
    def schlacht_meldung(self) -> dict:
        return {
            "dz": [[round(z.pos.x), round(z.pos.y), z.team, round(z.rest, 1), z.art,
                    1 if z.einmalig else 0, 1 if z.fahrzeug is not None else 0, z.kennung]
                   for z in self.dropzonen],
            "ab": [[round(a.pos.x), round(a.pos.y), round(a.hoehe, 1), a.art, a.team,
                    round(a.winkel), round(a.alter, 2)] for a in self.abwuerfe],
            "ue": [[round(u.pos.x), round(u.pos.y), u.team] for u in self.ueberfluege],
        }

    def schlacht_uebernehmen(self, m) -> None:
        """Beim Gast: Zonen und Abwuerfe nur als Bild."""
        if not isinstance(m, dict):
            return
        zonen = []
        for e in m.get("dz", []):
            try:
                z = Dropzone((float(e[0]), float(e[1])), int(e[2]), str(e[4]), 0.0,
                             bool(e[5]))
                z.rest = float(e[3])
                z.besetzt = bool(e[6])
                z.kennung = int(e[7])
                zonen.append(z)
            except (TypeError, ValueError, IndexError):
                continue
        self.dropzonen = zonen
        abw = []
        for e in m.get("ab", []):
            try:
                z = Dropzone((float(e[0]), float(e[1])), int(e[4]), str(e[3]), float(e[5]))
                a = Abwurf(z)
                a.hoehe = float(e[2])
                a.alter = float(e[6])
                abw.append(a)
            except (TypeError, ValueError, IndexError):
                continue
        self.abwuerfe = abw
        ue = []
        for e in m.get("ue", []):
            try:
                ue.append((pygame.Vector2(float(e[0]), float(e[1])), int(e[2])))
            except (TypeError, ValueError, IndexError):
                continue
        self._ueberfluege_gast = ue

    # ---- Bild: am Boden -------------------------------------------------------
    def dropzonen_zeichnen(self, flaeche, ebene: int, ecke) -> None:
        """Die Zonen auf dem Boden: ein Achteck in der Farbe der Seite mit
        Eckwinkeln, Pfeile, die nach innen laufen, und in der Mitte, was
        kommt. Steht der Abwurf kurz bevor, pulsiert sie und zaehlt."""
        if ebene != 0 or not self.dropzonen:
            return
        zeit = self.welt.zeit if self.ist_gastgeber else self._zeit
        for z in self.dropzonen:
            p = z.pos - ecke
            if not (-80 < p.x < flaeche.get_width() + 80 and -80 < p.y < flaeche.get_height() + 80):
                continue
            besetzt = z.fahrzeug is not None or getattr(z, "besetzt", False)
            self._zone_bild(flaeche, p, z, zeit, besetzt)

    def _zone_bild(self, flaeche, p, z, zeit: float, besetzt: bool) -> None:
        d = S["dropzone"]
        kombi = K.TEAMS["kombi"][z.team] if 0 <= z.team < 2 else None
        farbe = kombi["hud"] if kombi else K.C_AMBER
        dunkel = kombi["hud_dunkel"] if kombi else K.C_MUTED_DK
        r = d["radius"] if z.art in ("buggy", "panzer", "panzerwagen") else d["radius_kiste"]
        bald = 0.0 <= z.rest <= S["abwurf"]["vorlauf"] and not besetzt
        puls = 0.5 + 0.5 * math.sin(zeit * (9.0 if bald else 2.2))
        cx, cy = int(p.x), int(p.y)
        # Grund: ein durchscheinendes Achteck, darauf die Kante.
        punkte = [(cx + r * math.cos(math.radians(22.5 + 45 * i)),
                   cy + r * 0.62 * math.sin(math.radians(22.5 + 45 * i))) for i in range(8)]
        grund = pygame.Surface((r * 2 + 4, int(r * 1.3) + 4), pygame.SRCALPHA)
        verschoben = [(x - cx + r + 2, y - cy + int(r * 0.65) + 2) for x, y in punkte]
        deck = int(d["grund"] + (d["grund_puls"] * puls if bald else 0))
        pygame.draw.polygon(grund, dunkel + (deck,), verschoben)
        flaeche.blit(grund, (cx - r - 2, cy - int(r * 0.65) - 2))
        kante = farbe if (bald and puls > 0.5) or besetzt else dunkel
        pygame.draw.polygon(flaeche, kante, punkte, 1)
        # Eckwinkel aussen, wie Klammern.
        for i in range(0, 8, 2):
            a = math.radians(45 * i + 45)
            ex, ey = cx + (r + 5) * math.cos(a), cy + (r + 5) * 0.62 * math.sin(a)
            sx = 1 if math.cos(a) > 0 else -1
            sy = 1 if math.sin(a) > 0 else -1
            pygame.draw.line(flaeche, farbe, (ex, ey), (ex - sx * 6, ey))
            pygame.draw.line(flaeche, farbe, (ex, ey), (ex, ey - sy * 4))
        # Pfeile, die nach innen wandern.
        if not besetzt:
            lauf = (zeit * (1.6 if bald else 0.6)) % 1.0
            for i in range(4):
                a = math.radians(90 * i)
                for j in range(2):
                    t = (lauf + j * 0.5) % 1.0
                    rr = r * (0.95 - 0.55 * t)
                    hx = cx + rr * math.cos(a)
                    hy = cy + rr * 0.62 * math.sin(a)
                    spitze = pygame.Vector2(-math.cos(a), -math.sin(a) * 0.62) * 4
                    quer = pygame.Vector2(-spitze.y, spitze.x) * 0.8
                    f = tuple(int(c * (1.0 - t * 0.7)) for c in farbe)
                    pygame.draw.lines(flaeche, f, False,
                                      [(hx - spitze.x + quer.x, hy - spitze.y + quer.y),
                                       (hx, hy),
                                       (hx - spitze.x - quer.x, hy - spitze.y - quer.y)])
        # In der Mitte: was hier landet.
        zeichen = S["dropzone"]["zeichen"].get(z.art, "?")
        SCHRIFT.zeichnen(flaeche, zeichen, cx, cy - 3, farbe if not besetzt else dunkel, 1,
                         ausrichtung="mitte")
        if bald and z.rest > 0.0:
            text = "ABWURF %d" % int(math.ceil(z.rest))
            SCHRIFT.zeichnen(flaeche, text, cx, cy - int(r * 0.62) - 12, farbe, 1,
                             ausrichtung="mitte")

    # ---- Bild: in der Luft ---------------------------------------------------
    def abwuerfe_zeichnen(self, ziel, misch: float) -> None:
        """Ueber allem: der Schatten am Boden (je tiefer, desto groesser und
        dunkler), die Last etwas hoeher und groesser, darueber der Schirm."""
        ecke = self.kamera.ecke
        r = self.renderer
        a = S["abwurf"]
        for ab in self.abwuerfe:
            boden = ab.pos - ecke
            hoch = max(0.0, ab.hoehe)
            anteil = 1.0 - min(1.0, hoch / a["hoehe"])
            # Schatten.
            sw = int(16 + 22 * anteil)
            sch = pygame.Surface((sw * 2, sw), pygame.SRCALPHA)
            pygame.draw.ellipse(sch, (12, 9, 6, int(50 + 110 * anteil)), sch.get_rect())
            ziel.blit(sch, (boden.x - sw, boden.y - sw // 2))
            # Die Last: pendelt leicht.
            pendel = math.sin(ab.alter * 2.4) * 6.0 * (1.0 - anteil * 0.5)
            hub = hoch * a["bild_hub"]
            last = boden + pygame.Vector2(pendel, -hub)
            self._fracht_zeichnen(ziel, ab.art, last, ab.winkel + pendel * 0.8)
            # Der Schirm.
            gross = ab.art in ("buggy", "panzer", "panzerwagen")
            schirm = last + pygame.Vector2(pendel * 0.4, -a["schirm_ueber"] * (1.6 if gross else 1.0))
            self._schirm_zeichnen(ziel, schirm, last, ab.team,
                                  a["schirm"] if gross else a["schirm_kiste"])

    def _fracht_zeichnen(self, ziel, art: str, p, winkel: float) -> None:
        bilder = self.renderer.bilder
        if art in ("munition", "medkit"):
            s = bilder.bild("munikiste" if art == "munition" else "medkit")
            s = pygame.transform.scale(s, (s.get_width() * 2, s.get_height() * 2))
            ziel.blit(s, s.get_rect(center=(int(p.x), int(p.y))))
            return
        if art == "buggy":
            s = bilder.gedreht("buggy", winkel)
            ziel.blit(s, s.get_rect(center=(int(p.x), int(p.y))))
            return
        merk = self.__dict__.setdefault("_fracht_probe", {})
        v = merk.get(art)
        if v is None:
            v = merk[art] = fahrzeug_modul.neu(art, (0, 0), 0, 0.0, nur_bild=True)
        v.winkel = winkel
        v.aufbau = winkel
        s = v._wanne_flaeche(bilder)
        ziel.blit(s, s.get_rect(center=(int(p.x), int(p.y))))
        v.zeichnen_oben(self.renderer, ziel, p)

    @staticmethod
    def _schirm_zeichnen(ziel, schirm, last, team: int, groesse) -> None:
        kombi = K.TEAMS["kombi"][team] if 0 <= team < 2 else None
        hell = kombi["rumpf"] if kombi else (200, 190, 170)
        breit, hoch = groesse
        x, y = int(schirm.x), int(schirm.y)
        rect = pygame.Rect(x - breit // 2, y - hoch, breit, hoch * 2)
        # Bahnen: abwechselnd hell und weiss, als Kuppel.
        bahnen = 6
        for i in range(bahnen):
            a0 = math.pi + math.pi * i / bahnen
            a1 = math.pi + math.pi * (i + 1) / bahnen
            pts = [(x, y)]
            for t in range(5):
                a = a0 + (a1 - a0) * t / 4
                pts.append((x + math.cos(a) * breit / 2, y + math.sin(a) * hoch))
            farbe = hell if i % 2 == 0 else (232, 226, 210)
            pygame.draw.polygon(ziel, farbe, pts)
        pygame.draw.arc(ziel, (40, 32, 26), rect, 0.0, math.pi, 1)
        pygame.draw.line(ziel, (40, 32, 26), (x - breit // 2, y), (x + breit // 2, y))
        # Leinen zur Last.
        for dx in (-breit // 2, -breit // 6, breit // 6, breit // 2):
            pygame.draw.line(ziel, (70, 62, 54), (x + dx, y), (int(last.x), int(last.y) - 4))

    def ueberfluege_zeichnen(self, ziel) -> None:
        """Die grosse Drohne, hoch oben, mit ihrem Suchkreis am Boden."""
        ecke = self.kamera.ecke
        liste = ([(u.pos, u.team) for u in self.ueberfluege] if self.ist_gastgeber
                 else getattr(self, "_ueberfluege_gast", []))
        a = S["aufklaerung"]
        for pos, team in liste:
            p = pos - ecke
            kombi = K.TEAMS["kombi"][team] if 0 <= team < 2 else None
            farbe = kombi["hud"] if kombi else K.C_TEAL
            rr = int(a["radius"])
            # Der Kreis ist 1300 Pixel gross - einmal bauen, nicht in jedem
            # Bild (seit 0.34.99).
            schluessel = (rr, tuple(farbe))
            ringe = self.__dict__.setdefault("_sl_ringe", {})
            ring = ringe.get(schluessel)
            if ring is None:
                ring = pygame.Surface((rr * 2 + 2, rr * 2 + 2), pygame.SRCALPHA)
                pygame.draw.circle(ring, tuple(farbe) + (28,), (rr + 1, rr + 1), rr)
                pygame.draw.circle(ring, tuple(farbe) + (120,), (rr + 1, rr + 1), rr, 1)
                ringe[schluessel] = ring
            ziel.blit(ring, (p.x - rr - 1, p.y - rr - 1))
            # Die Drohne: Rumpf und vier Rotoren, gross und hoch.
            x, y = int(p.x), int(p.y) - 40
            pygame.draw.ellipse(ziel, (12, 9, 6), (x - 18, y + 46, 36, 10))
            pygame.draw.rect(ziel, (58, 62, 60), (x - 9, y - 4, 18, 8))
            pygame.draw.rect(ziel, farbe, (x - 3, y - 2, 6, 4))
            for dx, dy in ((-16, -10), (16, -10), (-16, 10), (16, 10)):
                pygame.draw.line(ziel, (40, 42, 40), (x, y), (x + dx, y + dy), 2)
                pygame.draw.circle(ziel, (150, 150, 140), (x + dx, y + dy), 6, 1)

    # ---- Belohnungsmenue -----------------------------------------------------
    def belohnung_karte_rect(self) -> pygame.Rect:
        return pygame.Rect(232, 46, 392, 262)

    def belohnung_ereignis(self, ev) -> bool:
        """Tasten und Maus, solange das Menue offen ist. True: verbraucht."""
        if not self.belohnung_offen:
            return False
        liste = S["belohnungen"]
        if ev.type == pygame.KEYDOWN:
            if ev.key in self.app.opt.codes("inventar") or ev.key == pygame.K_ESCAPE:
                self.belohnung_offen = False
                return True
            if pygame.K_1 <= ev.key <= pygame.K_9 and ev.key - pygame.K_1 < len(liste):
                self.belohnung_wahl = ev.key - pygame.K_1
                return True
            if ev.key in (pygame.K_UP, pygame.K_w):
                self.belohnung_wahl = (self.belohnung_wahl - 1) % len(liste)
                return True
            if ev.key in (pygame.K_DOWN, pygame.K_s):
                self.belohnung_wahl = (self.belohnung_wahl + 1) % len(liste)
                return True
            return True
        if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
            maus = self.app.zu_spiel(ev.pos)
            for i in range(len(liste)):
                if self._belohnung_zeile(i).collidepoint(maus):
                    self.belohnung_wahl = i
                    return True
            karte = self.belohnung_karte_rect()
            if karte.collidepoint(maus):
                self._belohnung_anfordern(self._karte_zu_welt(maus))
            return True
        return ev.type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP, pygame.MOUSEWHEEL)

    @staticmethod
    def _belohnung_zeile(i: int) -> pygame.Rect:
        return pygame.Rect(16, 70 + i * 30, 206, 26)

    def _karte_masse(self):
        e = self.welt.ebene(0)
        r = self.belohnung_karte_rect()
        f = min(r.width / float(e.pixel_breite), r.height / float(e.pixel_hoehe))
        breit, hoch = e.pixel_breite * f, e.pixel_hoehe * f
        x0 = r.x + (r.width - breit) / 2
        y0 = r.y + (r.height - hoch) / 2
        return x0, y0, f

    def _karte_zu_welt(self, punkt) -> pygame.Vector2:
        x0, y0, f = self._karte_masse()
        return pygame.Vector2((punkt[0] - x0) / f, (punkt[1] - y0) / f)

    def _welt_zu_karte(self, pos) -> tuple:
        x0, y0, f = self._karte_masse()
        return int(x0 + pos.x * f), int(y0 + pos.y * f)

    def _belohnung_anfordern(self, punkt) -> None:
        was = S["belohnungen"][self.belohnung_wahl][0]
        ich = self.ich
        if ich is None:
            return
        if self.ist_gastgeber:
            grund = self.belohnung_kaufen(ich, was, punkt)
        else:
            grund = self.belohnung_pruefen(ich, was, punkt)
            if not grund:
                self.gast.senden({"t": "belohnung", "was": was,
                                  "x": round(punkt.x, 1), "y": round(punkt.y, 1)})
        self._sl_meldung = grund or "ANGEFORDERT"
        self._sl_meldung_rest = 2.5
        if not grund:
            self.welt.klang("aufheben", 0.7)

    def belohnung_zeichnen(self, ziel) -> None:
        if not self.belohnung_offen:
            return
        ich = self.ich
        schleier = pygame.Surface((K.GAME_W, K.GAME_H), pygame.SRCALPHA)
        schleier.fill((8, 6, 4, 205))
        ziel.blit(schleier, (0, 0))
        SCHRIFT.zeichnen(ziel, "NACHSCHUB", 16, 12, K.C_AMBER, 2)
        punkte = getattr(ich, "schlacht_punkte", 0) if ich is not None else 0
        SCHRIFT.zeichnen(ziel, "PUNKTE: %d" % punkte, 16, 34, K.C_CREAM, 1)
        SCHRIFT.zeichnen(ziel, "KILL +%d  FAHRZEUG +%d  HELFEN +%d" % (
            S["punkte"]["abschuss"], S["punkte"]["fahrzeug"], S["punkte"]["aufhelfen"]),
            16, 46, K.C_MUTED, 1)
        for i, (name, kosten, text) in enumerate(S["belohnungen"]):
            r = self._belohnung_zeile(i)
            gewaehlt = i == self.belohnung_wahl
            leistbar = punkte >= kosten
            pygame.draw.rect(ziel, (34, 26, 18) if gewaehlt else (20, 15, 11), r)
            pygame.draw.rect(ziel, K.C_AMBER if gewaehlt else (70, 56, 40), r, 1)
            farbe = K.C_CREAM if leistbar else K.C_MUTED_DK
            SCHRIFT.zeichnen(ziel, "%d  %s" % (i + 1, text), r.x + 5, r.y + 4, farbe, 1)
            SCHRIFT.zeichnen(ziel, "%d P" % kosten, r.right - 5, r.y + 4,
                             K.C_AMBER if leistbar else K.C_MUTED_DK, 1, ausrichtung="rechts")
            SCHRIFT.zeichnen(ziel, S["belohnung_hilfe"].get(name, ""), r.x + 5, r.y + 15,
                             K.C_MUTED, 1)
        self._belohnung_karte(ziel, ich)
        # Die Rangliste als Nebensache: der Stand der Seiten.
        if self.mit_teams and len(self.teampunkte) >= 2:
            SCHRIFT.zeichnen(ziel, "STAND  %s %d : %d %s" % (
                K.TEAMS["namen"][0], self.teampunkte[0], self.teampunkte[1],
                K.TEAMS["namen"][1]), 16, K.GAME_H - 40, K.C_MUTED, 1)
        meldung = getattr(self, "_sl_meldung", "")
        if meldung and getattr(self, "_sl_meldung_rest", 0.0) > 0.0:
            SCHRIFT.zeichnen(ziel, meldung, 428, K.GAME_H - 46, K.C_AMBER, 1, ausrichtung="mitte")
        SCHRIFT.zeichnen(ziel, "[1-%d] WÄHLEN  [KLICK AUF DIE KARTE] ANFORDERN  [TAB] ZU" % len(
            S["belohnungen"]), K.GAME_W // 2, K.GAME_H - 18, K.C_MUTED, 1, ausrichtung="mitte")

    def _belohnung_karte(self, ziel, ich) -> None:
        r = self.belohnung_karte_rect()
        e = self.welt.ebene(0)
        x0, y0, f = self._karte_masse()
        groesse = (max(1, int(e.pixel_breite * f)), max(1, int(e.pixel_hoehe * f)))
        riss = self.__dict__.get("_sl_riss")
        if riss is None or riss.get_size() != groesse or getattr(self, "_sl_riss_welt", None) is not self.welt:
            klein = pygame.Surface((e.breite, e.hoehe))
            klein.fill((58, 46, 34))
            for ty in range(e.hoehe):
                for tx in range(e.breite):
                    if e.fest(tx, ty):
                        klein.set_at((tx, ty), (126, 104, 78))
            riss = pygame.transform.scale(klein, groesse)
            self._sl_riss = riss
            self._sl_riss_welt = self.welt
        ziel.blit(riss, (int(x0), int(y0)))
        pygame.draw.rect(ziel, (84, 66, 48), r, 1)
        was = S["belohnungen"][self.belohnung_wahl][0]
        # Gesperrt: um die Basis der anderen (nicht fuer die Aufklaerung).
        if ich is not None and ich.team in (0, 1) and was != "aufklaerung":
            feind = self.schlacht_basis(1 - ich.team)
            if feind is not None:
                rr = int(S["abwurf"]["sperre_basis"] * f)
                sperre = pygame.Surface((rr * 2, rr * 2), pygame.SRCALPHA)
                pygame.draw.circle(sperre, (200, 40, 30, 70), (rr, rr), rr)
                # Nur innerhalb der Karte (seit 0.34.99): die Basis liegt
                # am Rand, und der Kreis lief ueber den Rahmen bis an den
                # Bildschirmrand.
                alt_clip = ziel.get_clip()
                ziel.set_clip(r.clip(alt_clip) if alt_clip else r)
                ziel.blit(sperre, (self._welt_zu_karte(feind)[0] - rr,
                                   self._welt_zu_karte(feind)[1] - rr))
                ziel.set_clip(alt_clip)
        for z in self.dropzonen:
            kombi = K.TEAMS["kombi"][z.team] if 0 <= z.team < 2 else None
            px, py = self._welt_zu_karte(z.pos)
            pygame.draw.rect(ziel, kombi["hud"] if kombi else K.C_AMBER, (px - 2, py - 2, 5, 5), 1)
        for k in self.kaempfer.values():
            if ich is not None and k.lebt and k.fraktion == ich.fraktion:
                px, py = self._welt_zu_karte(k.pos)
                pygame.draw.rect(ziel, self._farbe_fuer(k), (px - 1, py - 1, 2, 2))
        if ich is not None:
            px, py = self._welt_zu_karte(ich.pos)
            pygame.draw.rect(ziel, (230, 255, 248), (px - 1, py - 1, 3, 3))
        # Unter der Maus: wie gross das Ziel ist, und ob es geht.
        maus = self.app.zu_spiel(pygame.mouse.get_pos())
        if r.collidepoint(maus) and ich is not None:
            punkt = self._karte_zu_welt(maus)
            grund = self.belohnung_pruefen(ich, was, punkt)
            weite = (S["aufklaerung"]["radius"] if was == "aufklaerung"
                     else S["dropzone"]["radius"])
            rr = max(3, int(weite * f))
            pygame.draw.circle(ziel, K.C_TEAL if not grund else K.C_RED, maus, rr, 1)
            SCHRIFT.zeichnen(ziel, grund or "HIER ANFORDERN", int(maus.x), int(maus.y) - rr - 10,
                             K.C_TEAL if not grund else K.C_RED, 1, ausrichtung="mitte")
