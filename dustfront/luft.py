"""
DUSTFRONT - Was in der Luft ist (seit 0.34.113)
===============================================

Gemeldet fuer den Tragschrauber: "wieder das Problem, dass Spieler den nicht
anvisieren koennten ... es soll spaeter mehr Helis geben, und man soll auch
hoch auf andere Etagen schiessen koennen". Die Regel, die das loest:

**Man schiesst auf das, worauf der Mauszeiger liegt - auch in der Luft.**
Alles, was in der Luft ist, wird um seine Hoehe nach oben versetzt gezeichnet.
Liegt der Mauszeiger auf diesem *Bild* (nicht auf seinem Schatten am Boden),
rastet das Ziel des Schuetzen auf den Ort darunter ein, und seine Kugeln
gehen auf das Luftziel: sie fliegen am Boden entlang (Mauern halten sie
auf), alles, was dazwischen steht, laesst sie durch, und sie treffen, wenn
sie unter dem Luftziel ankommen. Liegt der Zeiger daneben, schiesst man wie
immer auf den Boden. Dieselbe Regel gilt fuer jeden Schuetzen - Menschen,
Bots und Fahrzeuge - und fuer jedes Luftziel; fuer Helis und spaeter fuer
Ziele auf anderen Etagen kommt nur ein weiterer Eintrag in `luft_ziele`.

Was heute ein Luftziel ist, steht in `luft_ziele`. Wen alle treffen koennen
(Tragschrauber, Drohnen) und was nur Flak trifft (Abwuerfe am Schirm,
Fallschirmjaeger), sagt `nur_flak`.

Ausserdem hier: der Flug des Tragschraubers im Gefecht (Bomben, Aufklaerung)
und sein Zeichnen ueber allem.
"""

from __future__ import annotations

import math

import pygame

from . import ausruestung as ausruestung_modul
from . import config as K
from . import fahrzeug as fahrzeug_modul

S = K.SCHLACHT


class LuftZiel:
    """Ein Ziel in der Luft, wie die Zielregel es sieht. `pos` ist der Ort
    am Boden darunter, `versatz` wie viele Pixel hoeher sein Bild gezeichnet
    wird, `radius` wie gross es als Ziel ist (um sein Bild)."""

    __slots__ = ("objekt", "art", "fraktion", "pos", "versatz", "radius", "nur_flak", "_treffen")

    def __init__(self, objekt, art: str, fraktion, pos, versatz: float, radius: float,
                 nur_flak: bool, treffen) -> None:
        self.objekt = objekt
        self.art = art
        self.fraktion = fraktion
        self.pos = pygame.Vector2(pos)
        self.versatz = float(versatz)
        self.radius = float(radius)
        self.nur_flak = bool(nur_flak)
        self._treffen = treffen

    @property
    def bild_pos(self) -> pygame.Vector2:
        """Wo man es im Bild sieht (und wohin der Mauszeiger zeigt)."""
        return pygame.Vector2(self.pos.x, self.pos.y - self.versatz)

    @property
    def lebt(self) -> bool:
        return bool(getattr(self.objekt, "lebt", True))

    def treffen(self, menge: float, von) -> None:
        self._treffen(self, float(menge), von)


class LuftTeil:
    """Ein Anteil des Gefechts."""

    # ---- Wer ist ein Luftziel ----------------------------------------------
    def luft_ziele(self) -> list:
        """Alle Luftziele (Gastgeber), je Rechenschritt einmal gemerkt."""
        jetzt = self.welt.zeit
        merk = self.__dict__.get("_lz_merk")
        if merk is not None and merk[0] == jetzt:
            return merk[1]
        liste = []
        hub = S["abwurf"]["bild_hub"]
        for ab in getattr(self, "abwuerfe", ()):
            liste.append(LuftZiel(ab, "abwurf", "team%d" % ab.team if ab.team >= 0 else "", ab.pos,
                                  max(0.0, ab.hoehe) * hub, 26.0, True, self._abwurf_treffer))
        for k in self.kaempfer.values():
            hoch = getattr(k, "schirm_hoehe", 0.0)
            if hoch > 0.0 and k.lebt:
                liste.append(LuftZiel(k, "springer", k.fraktion, k.pos,
                                      hoch * S["abwurf"]["bild_hub"], 14.0, True,
                                      self._springer_treffer))
        for w in self.welt.wesen:
            if getattr(w, "hoch_oben", False) and w.lebt and isinstance(w, ausruestung_modul.Drohne):
                liste.append(LuftZiel(w, "drohne", getattr(w, "fraktion", ""), w.pos,
                                      K.HOCH_OBEN["hoehe"], 14.0, False, self._drohne_treffer))
        for b in getattr(self, "fahrzeuge", ()):
            if b.art == "tragschrauber" and b.in_der_luft and not b.nur_bild:
                liste.append(LuftZiel(b, "fahrzeug", fahrzeug_modul.seite_von(b) or "", b.pos, b.hoehe,
                                      b.werte["luft_radius"], False, self._fahrzeug_luft_treffer))
        self._lz_merk = (jetzt, liste)
        return liste

    # ---- Einrasten ----------------------------------------------------------
    def luft_zielen(self, k) -> None:
        """Nach jeder Eingabe (Gastgeber): liegt der Zeiger auf dem Bild eines
        Luftziels, das `k` treffen darf und das nicht zu seiner Seite gehoert,
        rastet sein Ziel auf den Ort darunter ein."""
        k.luft_ziel = None
        if getattr(k, "ebene", 0) != 0:
            return
        ziel = getattr(k, "ziel", None)
        if ziel is None:
            return
        flak = bool(getattr(getattr(k, "fahrzeug", None), "flak", False))
        for lz in self.luft_ziele():
            if lz.nur_flak and not flak:
                continue
            if lz.fraktion and lz.fraktion == k.fraktion or lz.objekt is k:
                continue
            if lz.objekt is getattr(k, "fahrzeug", None):
                continue
            if lz.bild_pos.distance_to(ziel) <= lz.radius:
                k.luft_ziel = lz
                k.ziel = pygame.Vector2(lz.pos)
                return

    # ---- Treffer ------------------------------------------------------------
    def _abwurf_treffer(self, lz, menge: float, von) -> None:
        ab = lz.objekt
        if ab not in self.abwuerfe:
            return
        leben = getattr(ab, "luft_leben", None)
        if leben is None:
            leben = 80.0 if ab.art in ("munition", "medkit") else 260.0
        leben -= menge
        ab.luft_leben = leben
        if leben <= 0.0:
            self.abwuerfe.remove(ab)
            zone = getattr(ab, "zone", None)
            if zone is not None and zone.einmalig and zone in self.dropzonen:
                self.dropzonen.remove(zone)
            self.welt.explosion(ab.pos, 0, 40.0, "spreng", von)

    def _springer_treffer(self, lz, menge: float, von) -> None:
        k = lz.objekt
        k.schaden(menge, None, von)
        if not k.lebt:
            k.schirm_hoehe = 0.0

    def _drohne_treffer(self, lz, menge: float, von) -> None:
        lz.objekt.schaden(menge, None, von)

    def _fahrzeug_luft_treffer(self, lz, menge: float, von) -> None:
        b = lz.objekt
        b.schaden(menge, None, von, art="kugel", herkunft=getattr(von, "pos", None))

    # ---- Flaechenschaden (Bomben, Raketen) -----------------------------------
    def flaechenschaden(self, p, ebene: int, radius: float, schaden: float, fahrzeug: float,
                        von, waffe: str) -> None:
        """Ein Einschlag wirkt im Kreis: nach aussen weniger, durch Deckung
        weniger (wie die Kanone des Panzers)."""
        from .entities import abschuss_buchen, schaden_an
        w = self.welt
        for a in list(w.nahe(p, radius + 70.0, ebene)):
            if not a.lebt or not getattr(a, "trefferbar", True) or getattr(a, "fraktion", "") == "geschoss":
                continue
            if getattr(a, "ist_fahrzeug", False):
                if not a.beruehrt(p, radius):
                    continue
            elif a.pos.distance_to(p) > radius + a.radius:
                continue
            weit = a.pos.distance_to(p)
            anteil = (1.0 - 0.6 * min(1.0, weit / max(1.0, radius))) * w.deckung_anteil(p, a.pos, ebene)
            schub = (a.pos - p).normalize() * 260.0 * anteil if weit > 0.01 else None
            lebte = a.lebt
            schaden_an(a, schaden * anteil, schub, von, "hohlladung", p, fahrzeug * anteil)
            abschuss_buchen(von, a, waffe, lebte)

    # ---- Der Tragschrauber im Gefecht -----------------------------------------
    def tragschrauber_schritt(self, dt: float) -> None:
        f = K.TRAGSCHRAUBER
        bo = f["bombe"]
        for b in self.fahrzeuge:
            if b.art != "tragschrauber" or b.nur_bild or b.kaputt:
                continue
            druck = b.feuer and not b._feuer_alt
            b._feuer_alt = b.feuer
            if (druck and b.in_der_luft and b.bomben > 0 and b.emp_rest <= 0.0
                    and b.fahrer is not None and not b.landen):
                b.bomben -= 1
                b._bomben_rest = f["bomben_nachladen"]
                ort = b.pos + b.vorn * b.flug_v * bo["fall"]
                b.bomben_fall.append([bo["fall"], ort.x, ort.y])
                self.welt.klang("granate", 0.5, b.pos, b.ebene)
            for e in list(b.bomben_fall):
                e[0] -= dt
                if e[0] <= 0.0:
                    b.bomben_fall.remove(e)
                    p = pygame.Vector2(e[1], e[2])
                    self.welt.explosion(p, b.ebene, bo["radius"], "panzer", b.fahrer)
                    self.flaechenschaden(p, b.ebene, bo["radius"], bo["schaden"], bo["fahrzeug"],
                                         b.fahrer, "bombe")
            if b.in_der_luft and b.fahrer is not None and b.emp_rest <= 0.0:
                b._aufkl_rest -= dt
                if b._aufkl_rest <= 0.0:
                    b._aufkl_rest = f["aufklaerung_takt"]
                    self._tragschrauber_aufklaeren(b)

    def _tragschrauber_aufklaeren(self, b) -> None:
        """Alles Gegnerische unter dem Tragschrauber ist fuer die Seite markiert."""
        team = self._team_von_seite(fahrzeug_modul.seite_von(b))
        if team is None:
            return
        eigen, feind = "team%d" % team, "team%d" % (1 - team)
        r = K.TRAGSCHRAUBER["aufklaerung"]
        for z in list(self.welt.nahe(b.pos, r + 60.0, b.ebene)):
            if z is b or not z.lebt or z.pos.distance_to(b.pos) > r:
                continue
            seite = (fahrzeug_modul.seite_von(z) if getattr(z, "ist_fahrzeug", False)
                     else getattr(z, "fraktion", None))
            if seite == feind and getattr(z, "trefferbar", True):
                ausruestung_modul.markieren(z, fuer=eigen)

    # ---- Zeichnen (Gastgeber und Gast) -----------------------------------------
    def _luftfahrzeuge_zeichnen(self, ziel, misch: float) -> None:
        """Tragschrauber: der Rotor immer (auch am Boden, solange er besetzt
        ist), und in der Luft der ganze Wagen ueber allem - mit Schatten."""
        ecke = self.kamera.ecke
        r = self.renderer
        t = self.welt.zeit
        for b in self.fahrzeuge:
            if b.art != "tragschrauber" or b.kaputt or b.ebene != self.blick:
                continue
            p = b.zeichenpos(misch) - ecke
            if not (-120 < p.x < ziel.get_width() + 120 and -200 < p.y < ziel.get_height() + 200):
                continue
            h = max(0.0, b.hoehe)
            besetzt = b.fahrer is not None or getattr(b, "besetzt", False)
            if b.hoch_oben:
                sch = r.bilder.gedreht(b.schatten_bild, b.winkel)
                ziel.blit(sch, sch.get_rect(center=(int(p.x + h * 0.32), int(p.y + h * 0.12 + 2))))
                s = r.bilder.gedreht(b.bild, b.winkel)
                ziel.blit(s, s.get_rect(center=(int(p.x), int(p.y - h))))
            if h > 2.0 or besetzt:
                rotor = r.bilder.bild("rotor_%d" % (int(t * 40.0) % 6))
                m = p + pygame.Vector2(-3.4, 0).rotate(b.winkel) - pygame.Vector2(0, h + 6.0)
                ziel.blit(rotor, rotor.get_rect(center=(int(m.x), int(m.y))))
            for e in b.bomben_fall:
                fall = K.TRAGSCHRAUBER["bombe"]["fall"]
                q = pygame.Vector2(e[1], e[2]) - ecke
                oben = max(0.0, e[0] / fall) * h * 1.4
                pygame.draw.ellipse(ziel, (12, 9, 6), (q.x - 3, q.y - 1, 6, 3))
                pygame.draw.circle(ziel, (30, 28, 26), (int(q.x), int(q.y - oben)), 3)
                pygame.draw.circle(ziel, (196, 172, 72), (int(q.x), int(q.y - oben)), 1)
