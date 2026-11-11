"""
DUSTFRONT - Was der Gast selbst rechnet (seit 0.34.103)
========================================================

Der Plan steht in docs/CLIENTSEITE.md. Hier die ersten beiden Stufen:

**Puffer (Stufe B).** Bis 0.34.102 wendete der Gast jede Weltmeldung in dem
Augenblick an, in dem sie ankam. Kommen Meldungen ungleichmaessig - und auf
schlechtem Internet tun sie das -, springt dann das Bild. Jetzt traegt jede
Meldung die Uhr des Gastgebers ("zt"), und der Gast spielt sie in diesem
Takt ab, um eine kleine Verzoegerung versetzt. Die Verzoegerung waechst mit
der gemessenen Schwankung, nie ueber `puffer_hoechstens`. Die Reihenfolge
aller Nachrichten bleibt, wie sie kam: eine Nachricht, die keine
Weltmeldung ist (Ende, Neustart ...), wartet, bis die Weltmeldungen vor ihr
abgespielt sind.

**Vorhersage (Stufe A).** Die eigene Figur bewegt der Gast sofort selbst,
mit derselben Formel wie Spieler.schritt. Jede Eingabe bekommt eine Nummer
("en"). Der Gastgeber sagt in jeder Meldung, welche er zuletzt angewendet
hat und seit wann ("en", "ea"), dazu Tempo ("tv") und Tempofaktor ("lf").
Der Gast sucht in seiner eigenen Spur genau den Punkt, der dazu passt, und
verschiebt die Vorhersage um den Unterschied. Kleine Unterschiede gleicht
die Anzeige weich aus, grosse sofort.

Sicherungen fuer schlechtes Internet (gewuenscht: "es waere gut, wenn
dadurch keine neuen Bugs bei schlechtem Internet entstehen"):

* Kommt laenger keine Antwort (`vorhersage_ohne_antwort`), laeuft die
  Vorhersage nicht weiter - die Figur rennt nicht davon und springt dann
  zurueck.
* Faellt ein Abgleich zu gross aus oder findet sich der Punkt nicht in der
  Spur, gilt der Stand des Gastgebers.
* Wo die Formel nicht reicht - im Fahrzeug, am Boden, im Sturz, am Schirm,
  beim Ziehen und Aufhelfen, auf einer anderen Ebene -, gilt ebenfalls der
  Stand des Gastgebers, wie bisher.
* Staut sich der Puffer doch (mehr als `puffer_hoechstens` hinter dem
  Gastgeber), wird alles sofort abgespielt.

Alles abschaltbar: K.NETZ puffer_an, vorhersage_an.
"""

from __future__ import annotations

import math
from collections import deque

import pygame

from . import config as K
from .entities import naehern


class _Geist:
    """Was welt.bewegen von einer Figur braucht - fuer die Vorhersage, ohne
    die echte Figur anzufassen."""

    faellt = False

    def __init__(self, pos, radius: float, ebene: int) -> None:
        self.pos = pygame.Vector2(pos)
        self.radius = radius
        self.ebene = ebene


class GastTeil:
    """Puffer und Vorhersage beim Gast. Ein Anteil des Gefechts."""

    # ---- Anlegen ---------------------------------------------------------
    def _gastseite_anlegen(self) -> None:
        self._eingang: deque = deque()     # angekommen, noch nicht abgespielt
        self._uhr_versatz = None           # Uhr des Gastgebers - eigene Uhr
        self._schwankung = 0.0
        self._zt_zuletzt = None            # Uhrzeit der zuletzt abgespielten Meldung
        self._zt_davor = None
        # Vorhersage
        self._ein_nr = 0
        self._ein_will = pygame.Vector2(0, 0)
        self._ein_seit = 0.0               # so lange gilt die zuletzt gesendete Eingabe
        self._ein_schritte = 0             # so viele Schritte galt sie (fuer den Eingabepuffer)
        self._vh_spur: deque = deque()     # (Nummer, seit, Ort, Tempo, Ebene)
        self._vh_ort = None                # vorhergesagter Ort, None = aus
        self._vh_tempo = pygame.Vector2(0, 0)
        self._vh_ebene = 0
        self._vh_luft = 1.0
        self._vh_anzeige = pygame.Vector2(0, 0)   # noch auszugleichender Versatz
        self._vh_ohne_antwort = 0.0
        self._vh_dash_kommt = False        # mit der letzten Eingabe ging ein Dash hinaus
        self._vh_dash_rest = 0.0
        self._vh_dash_richtung = pygame.Vector2(1, 0)
        self.vh_korrekturen = 0            # nur zum Nachsehen (Tests, Messung)
        self.vh_spruenge = 0
        self.vh_fehler_max = 0.0

    # ---- Puffer ------------------------------------------------------------
    def _puffer_jetzt(self) -> float:
        return float(self._zeit)

    def _puffer_eingang(self, neu: list) -> list:
        """Nimmt die neue Post an und gibt zurueck, was jetzt dran ist."""
        n = K.NETZ
        jetzt = self._puffer_jetzt()
        for nachricht in neu:
            if not isinstance(nachricht, dict):
                continue
            if nachricht.get("t") == "welt":
                self._vorhersage_abgleich(nachricht)
                zt = nachricht.get("zt")
                if isinstance(zt, (int, float)):
                    self._uhr_messen(float(zt), jetzt)
            self._eingang.append(nachricht)
        # Ohne Puffer, ohne Uhr - oder die Leitung ist zu: dann alles jetzt.
        gast = getattr(self, "gast", None)
        if (not n["puffer_an"] or self._uhr_versatz is None
                or (gast is not None and not gast.offen)):
            raus = list(self._eingang)
            self._eingang.clear()
            return raus
        abspielen = jetzt + self._uhr_versatz - self._puffer_verzoegerung()
        welten = [m for m in self._eingang if m.get("t") == "welt"]
        # Zu viel im Puffer (ein langer Haenger, ein Schwall): alles jetzt.
        alt = welten[0].get("zt") if welten else None
        if (len(welten) > n["puffer_meldungen"]
                or (isinstance(alt, (int, float)) and abspielen - float(alt) > n["puffer_hoechstens"] * 2)):
            raus = list(self._eingang)
            self._eingang.clear()
            return raus
        raus = []
        while self._eingang:
            m = self._eingang[0]
            if m.get("t") == "welt":
                zt = m.get("zt")
                if isinstance(zt, (int, float)) and float(zt) > abspielen:
                    break
            raus.append(self._eingang.popleft())
        return raus

    def _uhr_messen(self, zt: float, jetzt: float) -> None:
        """Wie weit die Uhr des Gastgebers vorgeht - gemessen an der Meldung,
        die am schnellsten ankam. Langsam vergessen, damit ein Gastgeber, der
        zurueckfaellt (ruckelt), nicht immer weiter vorausgeschaetzt wird."""
        probe = zt - jetzt
        v = self._uhr_versatz
        if v is None or probe > v or probe < v - 1.0:
            # Erste Meldung, schneller als je zuvor - oder die Uhr ist
            # zurueckgesprungen (neues Gefecht beim Gastgeber).
            self._uhr_versatz = probe
            if v is not None and probe < v - 1.0:
                self._schwankung = 0.0
            return
        spaet = v - probe
        # Schnell lauter, langsam leiser: eine Spitze soll den Puffer gleich
        # vergroessern, eine ruhige Phase ihn nur allmaehlich verkleinern.
        rate = 0.3 if spaet > self._schwankung else 0.02
        self._schwankung += (spaet - self._schwankung) * rate

    def _puffer_verzoegerung(self) -> float:
        n = K.NETZ
        return max(n["puffer_mindest"],
                   min(n["puffer_hoechstens"], n["takt"] + n["puffer_schwankung"] * self._schwankung))

    def _puffer_schritt(self, dt: float) -> None:
        if self._uhr_versatz is not None:
            self._uhr_versatz -= K.NETZ["uhr_drift"] * dt

    def _puffer_abgespielt(self, meldung: dict) -> None:
        """Nach _welt_uebernehmen: die Ueberblendung nach der Uhr des
        Gastgebers, statt nach dem Zeitpunkt der Ankunft."""
        zt = meldung.get("zt")
        if not isinstance(zt, (int, float)) or not K.NETZ["puffer_an"] or self._uhr_versatz is None:
            return
        zt = float(zt)
        if self._zt_zuletzt is not None and zt > self._zt_zuletzt:
            self._paket_takt = max(K.NETZ["takt"] * 0.5, min(0.5, zt - self._zt_zuletzt))
        self._zt_davor, self._zt_zuletzt = self._zt_zuletzt, zt
        abspielen = self._puffer_jetzt() + self._uhr_versatz - self._puffer_verzoegerung()
        self._seit_paket = max(0.0, min(self._paket_takt, abspielen - zt))

    # ---- Vorhersage --------------------------------------------------------
    def _vorhersage_moeglich(self, k) -> bool:
        if not K.NETZ["vorhersage_an"] or k is None or not k.lebt:
            return False
        return not (k.am_boden or k.im_fahrzeug or getattr(k, "mitfahrt", None) is not None
                    or k.flug > 0.0 or k.sturz_rest > 0.0
                    or getattr(k, "schirm_hoehe", 0.0) > 0.0
                    or k.zieht is not None or k.hilft is not None
                    or getattr(k, "raus", False) or self.vorbei)

    def _vorhersage_aus(self) -> None:
        self._vh_ort = None
        self._vh_spur.clear()
        self._vh_anzeige.update(0, 0)

    def _vorhersage_gesendet(self, meldung: dict) -> None:
        """Beim Senden einer Eingabe: Nummer dran, Richtung merken."""
        if not K.NETZ["vorhersage_an"]:
            return
        self._ein_nr += 1
        meldung["en"] = self._ein_nr
        # Wie viele Schritte die vorige Eingabe hier gegolten hat (seit
        # 0.34.104): genau so lange wendet der Gastgeber sie an
        # (_bewegung_fuehren) - dann stimmt die Vorhersage auch bei Schwankung.
        meldung["es"] = self._ein_schritte
        self._ein_schritte = 0
        try:
            will = pygame.Vector2(float(meldung["will"][0]), float(meldung["will"][1]))
        except (KeyError, TypeError, ValueError, IndexError):
            will = pygame.Vector2(0, 0)
        # Wie beim Gastgeber (Gefecht._anwenden): laenger als 1 wird gekuerzt.
        if will.length_squared() > 1.0:
            will.normalize_ip()
        self._ein_will = will
        self._ein_seit = 0.0
        # Ein Dash (seit 0.34.103 vorhergesagt): der Gastgeber loest ihn mit
        # dieser Eingabe aus (Spieler.dashen), wenn er darf - dieselben
        # Bedingungen, soweit der Gast sie kennt. Lag er falsch (die Sperre
        # kennt nur der Gastgeber), holt es der Abgleich.
        k = self.ich
        knoepfe = meldung.get("knoepfe") or ()
        if ("dash" in knoepfe and k is not None and k.dash_ladungen > 0
                and self._vh_dash_rest <= 0.0 and k.heilt_rest <= 0 and not k.gehalten):
            self._vh_dash_kommt = True

    def _vorhersage_abgleich(self, meldung: dict) -> None:
        """Eine Weltmeldung ist angekommen (noch vor dem Puffer): die eigene
        Vorhersage mit dem Stand des Gastgebers abgleichen."""
        k = self.ich
        eintrag = None
        for e in meldung.get("spieler", ()):
            if isinstance(e, dict) and e.get("i") == self.meine_nummer:
                eintrag = e
                break
        if eintrag is None or k is None:
            return
        try:
            en = int(eintrag["en"])
            ea = float(eintrag.get("ea", 0.0))
            ort = pygame.Vector2(float(eintrag["p"][0]), float(eintrag["p"][1]))
            tempo = pygame.Vector2(float(eintrag["tv"][0]), float(eintrag["tv"][1]))
            ebene = int(eintrag.get("e", 0))
            self._vh_luft = max(0.0, min(5.0, float(eintrag.get("lf", self._vh_luft))))
        except (KeyError, TypeError, ValueError, IndexError):
            return
        self._vh_ohne_antwort = 0.0
        if self._vh_ort is None:
            return
        n = K.NETZ
        # Der Punkt der eigenen Spur, der genau dazu passt: dieselbe Eingabe,
        # gleich lange gewirkt.
        while self._vh_spur and self._vh_spur[0][0] < en:
            self._vh_spur.popleft()
        passend = None
        letzter = None
        for eintrag_spur in self._vh_spur:
            if eintrag_spur[0] != en:
                break
            letzter = eintrag_spur
            if abs(eintrag_spur[1] - ea) < K.FIXED_DT * 0.5:
                passend = eintrag_spur
                break
        if passend is None and letzter is not None and ea > letzter[1]:
            # Beim Gastgeber wirkte die Eingabe laenger als hier - die
            # naechste kam dort spaeter an (Schwankung). Die fehlenden
            # Schritte mit derselben Formel weiterrechnen.
            fehlen = int(round((ea - letzter[1]) / K.FIXED_DT))
            if fehlen <= n["vorhersage_nachrechnen"]:
                o, t, dr = pygame.Vector2(letzter[2]), pygame.Vector2(letzter[3]), letzter[6]
                for _ in range(fehlen):
                    o, t, dr = self._modell_schritt(o, t, letzter[5], letzter[4], dr, letzter[7],
                                                    K.FIXED_DT)
                passend = (en, ea, o, t, letzter[4], letzter[5], dr, letzter[7])
        if passend is None or passend[4] != ebene:
            self._vorhersage_setzen(ort, tempo, ebene)
            return
        fehler = ort - passend[2]
        if fehler.length() > n["vorhersage_sprung"]:
            self._vorhersage_setzen(ort, tempo, ebene)
            return
        tempo_fehler = tempo - passend[3]
        # Gezaehlt ab einem Viertelpixel: darunter ist es die Rundung der
        # Meldung (Orte auf 0,1 px).
        if fehler.length_squared() > 0.0625 or tempo_fehler.length_squared() > 1.0:
            self.vh_korrekturen += 1
            self.vh_fehler_max = max(self.vh_fehler_max, fehler.length())
        # Die Uhr des Dashs gleich mit (seit 0.34.103): wirkte eine Eingabe
        # beim Gastgeber laenger, ist sein Stoss schon weiter. Ohne das lief
        # der vorhergesagte am Ende zu lang, und es blieb ein Versatz.
        try:
            dash_gastgeber = float(eintrag.get("dr", 0.0))
        except (TypeError, ValueError):
            dash_gastgeber = passend[6]
        nach = sum(1 for x in self._vh_spur if (x[0], x[1]) > (passend[0], passend[1]))
        # Erst ab anderthalb Schritten: "dr" kommt auf 0,01 s gerundet, und
        # die Rundung allein (bis 5 ms) liess den Stoss sonst einen Schritt
        # zu frueh enden.
        if abs(dash_gastgeber - passend[6]) > K.FIXED_DT * 1.5:
            rest = max(0.0, dash_gastgeber - nach * K.FIXED_DT)
            if rest > 0.0 and self._vh_dash_rest <= 0.0:
                try:
                    d = pygame.Vector2(float(eintrag["dw"][0]), float(eintrag["dw"][1]))
                    if d.length_squared() > 0.01:
                        self._vh_dash_richtung = d.normalize()
                except (KeyError, TypeError, ValueError, IndexError):
                    pass
            self._vh_dash_rest = rest
        # Alles danach um denselben Unterschied verschieben; die Anzeige
        # bleibt, wo sie war, und gleicht den Versatz weich aus.
        self._vh_ort += fehler
        self._vh_tempo += tempo_fehler
        self._vh_anzeige -= fehler
        for i, eintrag_spur in enumerate(self._vh_spur):
            nr, seit, o, t = eintrag_spur[:4]
            self._vh_spur[i] = (nr, seit, o + fehler, t + tempo_fehler) + eintrag_spur[4:]

    def _vorhersage_setzen(self, ort, tempo, ebene: int) -> None:
        """Neu beginnen beim Stand des Gastgebers. Liegt die alte Anzeige
        nah dabei, gleitet sie hin; sonst springt sie."""
        if self._vh_ort is not None:
            alt = self._vh_ort + self._vh_anzeige
            weg = alt - ort
            if weg.length() <= K.NETZ["vorhersage_sprung"] and ebene == self._vh_ebene:
                self._vh_anzeige = weg
            else:
                self._vh_anzeige = pygame.Vector2(0, 0)
                self.vh_spruenge += 1
        self._vh_ort = pygame.Vector2(ort)
        self._vh_tempo = pygame.Vector2(tempo)
        self._vh_ebene = ebene
        self._vh_spur.clear()

    def _vorhersage_schritt(self, dt: float) -> None:
        """Einen Schritt der eigenen Figur vorausrechnen - mit der Eingabe,
        die zuletzt hinausging (der Gastgeber wendet sie genauso an)."""
        k = self.ich
        self._ein_seit += dt
        self._ein_schritte += 1
        self._vh_ohne_antwort += dt
        if not self._vorhersage_moeglich(k):
            self._vorhersage_aus()
            return
        if self._vh_ort is None:
            self._vorhersage_setzen(k.pos, getattr(k, "tempo", pygame.Vector2()), k.ebene)
        if k.ebene != self._vh_ebene:
            self._vorhersage_setzen(k.pos, getattr(k, "tempo", pygame.Vector2()), k.ebene)
        n = K.NETZ
        will = pygame.Vector2(0, 0) if k.gehalten else pygame.Vector2(self._ein_will)
        if self._vh_dash_kommt:
            self._vh_dash_kommt = False
            richtung = pygame.Vector2(will)
            if richtung.length_squared() < 0.01:
                r = math.radians(k.winkel)
                richtung = pygame.Vector2(math.cos(r), math.sin(r))
            self._vh_dash_richtung = richtung.normalize()
            self._vh_dash_rest = K.DASH["dauer"]
        if self._vh_ohne_antwort <= n["vorhersage_ohne_antwort"]:
            self._vh_ort, self._vh_tempo, self._vh_dash_rest = self._modell_schritt(
                self._vh_ort, self._vh_tempo, will, self._vh_ebene,
                self._vh_dash_rest, self._vh_dash_richtung, dt)
        self._vh_spur.append((self._ein_nr, round(self._ein_seit, 6), pygame.Vector2(self._vh_ort),
                              pygame.Vector2(self._vh_tempo), self._vh_ebene, will,
                              self._vh_dash_rest, pygame.Vector2(self._vh_dash_richtung)))
        while len(self._vh_spur) > n["vorhersage_spur"]:
            self._vh_spur.popleft()
        # Den Versatz der Anzeige weich abbauen.
        self._vh_anzeige *= math.exp(-n["vorhersage_glaetten"] * dt)
        if self._vh_anzeige.length_squared() < 0.0004:
            self._vh_anzeige.update(0, 0)

    def _modell_schritt(self, ort, tempo, will, ebene: int, dash_rest: float,
                        dash_richtung, dt: float):
        """Ein Schritt der Bewegung wie in Spieler.schritt: das Tempo naehert
        sich dem gewuenschten - waehrend eines Dashs zaehlt nur der Stoss, am
        Ende auf knapp Lauftempo abgefangen -, dann achsenweise schieben
        (welt.bewegen). Gibt (Ort, Tempo, Rest des Dashs) zurueck."""
        s = K.SPIELER
        luft = self._vh_luft
        if dash_rest > 0.0:
            dash_rest -= dt
            tempo = dash_richtung * K.DASH["tempo"]
            if dash_rest <= 0.0:
                deckel = s["tempo"] * K.DASH["auslauf"]
                if tempo.length() > deckel:
                    tempo.scale_to_length(deckel)
        else:
            ziel = will * s["tempo"] * luft
            rate = (s["beschleunigung"] if will.length_squared() > 0 else s["bremsung"]) * luft
            tempo = pygame.Vector2(naehern(tempo.x, ziel.x, rate * dt),
                                   naehern(tempo.y, ziel.y, rate * dt))
        k = self.ich
        geist = _Geist(ort, getattr(k, "radius", 8.0), ebene)
        self.welt.bewegen(geist, tempo.x * dt, tempo.y * dt)
        return geist.pos, tempo, max(0.0, dash_rest)

    def _vorhersage_zeigen(self) -> None:
        """Die eigene Figur dorthin, wo die Vorhersage sie sieht (nach dem
        Uebernehmen einer Meldung, die sie sonst zurueckgesetzt haette)."""
        k = self.ich
        if self._vh_ort is None or k is None:
            return
        ort = self._vh_ort + self._vh_anzeige
        k.vorher.update(ort)
        k.pos.update(ort)


# ══════════════════════════════════════════════════════════════════
# Beim Gastgeber: der Eingabepuffer fuer die Bewegung (seit 0.34.104)
# ══════════════════════════════════════════════════════════════════
#
# Wie lange der Gastgeber eine Eingabe anwendet, hing davon ab, wann die
# naechste ankam - bei schwankender Leitung also nicht davon, wie lange der
# Gast sie gemeint hatte. Die Vorhersage lag dann daneben (beim Dash bis
# 30 px). Jetzt sagt jede Eingabe, wie viele Schritte die vorige beim Gast
# galt ("es"), und der Gastgeber wendet die **Bewegung** (Laufrichtung und
# Dash) genau so viele Schritte an.
#
# Nur die Bewegung: Zielen, Schiessen, Nachladen, Waffe, Medkit, E und alle
# anderen Tasten wirken weiter sofort, wenn die Eingabe ankommt - sonst
# trafe man auf schlechtem Internet noch schlechter.
#
# Kommt die naechste Eingabe zu spaet, laeuft die alte weiter (wie bisher);
# der Vorlauf, der so entsteht, faengt die naechste Schwankung ab. Ist eine
# Sekunde lang mehr Vorlauf da als noetig, wird ein Schritt davon abgebaut;
# ueber `eingabe_vorlauf_hoechstens` Schritte sofort. Im Fahrzeug, am Boden
# und wo die Vorhersage ohnehin nicht rechnet, wirkt alles sofort wie
# bisher.


class _Bewegung:
    __slots__ = ("nr", "will", "dash", "dauer")

    def __init__(self, nr: int, will, dash: bool) -> None:
        self.nr = nr
        self.will = will
        self.dash = dash
        self.dauer = None          # Schritte - bekannt, sobald die naechste Eingabe da ist


class WirtTeil:
    """Der Eingabepuffer beim Gastgeber. Ein Anteil des Gefechts."""

    @staticmethod
    def _bewegung_puffern_moeglich(k) -> bool:
        return (K.NETZ["eingabe_puffer"] and k.lebt and not k.am_boden
                and k.fahrzeug is None and getattr(k, "mitfahrt", None) is None)

    def _eingabe_vom_gast(self, k, nachricht: dict) -> None:
        """Eine Eingabe eines Gasts ist angekommen."""
        if "en" not in nachricht or "es" not in nachricht or not self._bewegung_puffern_moeglich(k):
            # Wie bis 0.34.103: alles sofort - und was noch im Puffer lag, gilt
            # nicht mehr (im Wagen lenkt die Richtung den Wagen).
            k.__dict__.pop("_bew_schlange", None)
            k._bew_aktuell = None
            self._anwenden(k, nachricht)
            if "en" in nachricht:
                try:
                    k.ein_nr = int(nachricht["en"])
                    k.ein_seit = 0.0
                except (TypeError, ValueError):
                    pass
            return
        try:
            nr = int(nachricht["en"])
            es = max(1, int(nachricht["es"]))
            will = pygame.Vector2(float(nachricht["will"][0]), float(nachricht["will"][1]))
        except (KeyError, TypeError, ValueError, IndexError):
            self._anwenden(k, nachricht)
            return
        if will.length_squared() > 1.0:
            will.normalize_ip()
        knoepfe = nachricht.get("knoepfe") or []
        dash = isinstance(knoepfe, list) and "dash" in knoepfe
        # Alles ausser der Bewegung: sofort.
        sofort = dict(nachricht)
        sofort["will"] = [k.will.x, k.will.y]
        if dash:
            sofort["knoepfe"] = [x for x in knoepfe if x != "dash"]
        self._anwenden(k, sofort)
        schlange = k.__dict__.setdefault("_bew_schlange", deque())
        aktuell = k.__dict__.get("_bew_aktuell")
        # "es" ist die Dauer der vorigen Eingabe.
        if schlange:
            if schlange[-1].dauer is None:
                schlange[-1].dauer = es
        elif aktuell is not None and aktuell.dauer is None:
            aktuell.dauer = es
        schlange.append(_Bewegung(nr, will, dash))

    def _bewegung_fuehren(self) -> None:
        """Vor jedem Schritt der Welt: welche Bewegung jetzt gilt."""
        n = K.NETZ
        for k in self.kaempfer.values():
            schlange = k.__dict__.get("_bew_schlange")
            if schlange is None:
                continue
            if not self._bewegung_puffern_moeglich(k):
                # Inzwischen im Wagen, am Boden ...: die letzte Richtung gilt
                # gleich, der Puffer ist vorbei.
                if schlange:
                    letzte = schlange[-1]
                    k.ein_nr, k.ein_seit = letzte.nr, 0.0
                del k.__dict__["_bew_schlange"]
                k._bew_aktuell = None
                continue
            aktuell = k.__dict__.get("_bew_aktuell")
            schritte = k.__dict__.get("_bew_schritte", 0)
            vorlauf = sum(b.dauer for b in schlange if b.dauer is not None)
            if aktuell is not None and aktuell.dauer is not None:
                vorlauf += max(0, aktuell.dauer - schritte)
            # Wie viel Vorlauf es mindestens gab - eine Sekunde lang gemerkt.
            k._bew_min = min(k.__dict__.get("_bew_min", 999), vorlauf)
            k._bew_fenster = k.__dict__.get("_bew_fenster", 0) + 1
            abbauen = False
            if k._bew_fenster >= n["eingabe_fenster"]:
                abbauen = k._bew_min > n["eingabe_vorlauf_ruhig"]
                k._bew_fenster = 0
                k._bew_min = 999
            wechseln = False
            if aktuell is None:
                wechseln = bool(schlange)
            elif schlange:
                fertig = aktuell.dauer is not None and schritte >= aktuell.dauer
                zu_viel = vorlauf > n["eingabe_vorlauf_hoechstens"]
                kuerzer = abbauen and aktuell.dauer is not None and schritte >= aktuell.dauer - 1
                wechseln = fertig or zu_viel or kuerzer
            if wechseln and vorlauf > n["eingabe_vorlauf_hoechstens"]:
                # Ein Schwall nach einem Haenger: gleich auf das erlaubte Mass
                # zurueck, statt Schritt fuer Schritt hinterherzulaufen. Was
                # uebersprungen wird, verliert nur seine Richtung - ein Dash
                # darin kommt mit der naechsten.
                dash = False
                while len(schlange) > 1 and vorlauf > n["eingabe_vorlauf_hoechstens"]:
                    weg = schlange.popleft()
                    dash = dash or weg.dash
                    vorlauf -= weg.dauer or 0
                if dash:
                    schlange[0].dash = True
            if wechseln:
                b = schlange.popleft()
                k._bew_aktuell = b
                k._bew_schritte = 0
                if not k.gehalten:
                    k.will = pygame.Vector2(b.will)
                if b.dash:
                    k.dashen()
                k.ein_nr = b.nr
                k.ein_seit = 0.0

    def _bewegung_gezaehlt(self) -> None:
        """Nach jedem Schritt der Welt."""
        for k in self.kaempfer.values():
            if k.__dict__.get("_bew_aktuell") is not None:
                k._bew_schritte = k.__dict__.get("_bew_schritte", 0) + 1
