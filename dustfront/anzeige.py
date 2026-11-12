"""
DUSTFRONT - Die Anzeige im Gefecht
==================================

Seit 0.27 eine eigene Datei und kein Anhang des Renderers mehr. Die alte
Anzeige war ueber die Versionen gewachsen: jede Neuerung bekam einen
Platz, wo gerade einer frei war. Das Ergebnis lief ineinander - die
Hotbar mit neun Plaetzen ueberdeckte die Lebenszahl und die Medkits, der
Vorrat stand quer ueber den Waffensymbolen, die Adresse des Gastgebers
stand die ganze Runde oben links, und den Dash sah man gar nicht.

Jetzt hat alles einen festen Ort (seit 0.34.92 nach der Skizze des
Besitzers):

    oben links     die Uhr - oder das Abschussziel, in PVE die Welle
    oben Mitte     der Stand der Mannschaften (TEAM: ein geteilter Balken,
                   darunter die Zahlen), in PVE der Boss
    oben rechts    die Ebenen
    unten links    die runde Karte um die eigene Figur, die Panzerung als
                   Bogen darum; daneben der Kreis der Faehigkeit (C), die
                   Dashes als Bogen darum, rechts daneben die Medkits
    unten rechts   Waffe, Magazin, Vorrat
    unten Mitte    die Hotbar - und darueber ein Hinweis, wenn es einen gibt
    TAB gehalten   die Tafel: Spielart, Karte und der ganze Punktestand

Die Raender bleiben frei: dort zeigen die Pfeile auf gefallene Mitspieler.

**Modi.** Die Anzeige richtet sich nach dem, was der Gastgeber
eingestellt hat, statt alles immer zu zeigen:

* Hotbar: mit Loadout (drei Plaetze) grosse Felder und der Name des
  Loadouts darueber; ohne (alle neun) kleine Felder.
* Vorrat: nur bei knapper Munition. Sonst wird nichts abgezogen, und eine
  Zahl, die nie kleiner wird, waere nur Rauschen.
* Medkits: nur, wenn es in dieser Runde welche gibt.
* Oben Mitte: je nach Spielart Uhr, Abschussziel, Welle mit Restzahl und
  Bossbalken, Mannschaftsstand, Versusrunden als Punkte, Kreisbalken.

Gezeichnet wird mit den Mitteln, die es schon gibt: Pixelschrift, die
Kaesten aus ui.py, die Waffensymbole. Neu ist die Ordnung, nicht der
Stil.
"""

from __future__ import annotations

import math

import pygame

from . import config as K
from . import ui
from .font import SCHRIFT
from .minikarte import Minikarte

W, H = K.GAME_W, K.GAME_H
SCHATTEN = (8, 6, 4)
KASTEN = (11, 8, 6, 214)        # Fuellung der Anzeigekaesten, halb deckend


def _c4_hotbar_symbol(ich) -> str:
    """Das Symbol zeigt Sprengsatz, Ladestand oder zuendbereiten Schalter."""
    rest = getattr(ich, "c4_rest", -1.0)
    if rest < 0.0:
        return "waffe_c4"
    if getattr(ich, "c4_bereit", rest <= 0.0):
        return "waffe_detonator_bereit"
    return "waffe_detonator"

# Die festen Orte. Hier und nur hier - wer etwas verschiebt, sieht auf
# einen Blick, was noch in der Naehe liegt.
UNTEN = H - 40                  # Oberkante der unteren Kaesten
# Unten links stehen seit 0.34.92 die runde Karte und der Kreis der
# Faehigkeit (K.HUD); LINKS ist der Platz, den sie zusammen brauchen -
# bis dorthin reicht die Hotbar.
_HUD = K.HUD
LINKS = pygame.Rect(8, UNTEN, _HUD["karte_x"] + _HUD["karte_d"] + _HUD["faeh_luft"]
                    + _HUD["faeh_d"] + 22 - 8, 32)
RECHTS = pygame.Rect(W - 164, UNTEN, 156, 32)
HOTBAR_Y = H - 36
HINWEIS_Y = H - 66
# Die Pfeile am Rand bleiben aus diesen Streifen heraus.
RAND_OBEN = 34
RAND_UNTEN = 50


def _text(ziel, text, x, y, farbe, skala=1, ausrichtung="links"):
    SCHRIFT.zeichnen(ziel, text, int(x), int(y), farbe, skala,
                     ausrichtung=ausrichtung, schatten=SCHATTEN)


def _balken(ziel, rect, anteil, farbe, hinten=(24, 17, 12)):
    r = pygame.Rect(rect)
    pygame.draw.rect(ziel, hinten, r)
    breite = int(r.width * max(0.0, min(1.0, anteil)))
    if breite > 0:
        pygame.draw.rect(ziel, farbe, (r.x, r.y, breite, r.height))


class Anzeige:
    """Die Anzeige eines Gefechts. Liest nur, aendert nichts."""

    def __init__(self, gefecht) -> None:
        self.g = gefecht
        self.minikarte = Minikarte()
        self._karte_unten = 0          # Unterkante der Minikarte, 0: keine

    # ---- Ganz ----------------------------------------------------------
    def zeichnen(self, ziel) -> None:
        """Seit 0.34.92 nach der Skizze: oben links die Uhr (oder die Welle),
        oben in der Mitte der Stand der Mannschaften, oben rechts die
        Ebenen; unten links die runde Karte mit der Panzerung als Bogen,
        daneben die Faehigkeit mit den Dashes als Bogen, in der Mitte die
        Hotbar, rechts die Waffe. Der Punktestand steht auf TAB."""
        g = self.g
        self._karte_unten = 0          # die Karte steht nicht mehr oben links
        self._kopf_links(ziel)
        self._kopf_mitte(ziel)
        self._ebenen(ziel)
        ich = g.ich
        if ich is not None:
            mitte, radius = self._karte_rund(ziel, ich)
            if ich.am_boden:
                self._am_boden(ziel, ich)
            elif not ich.lebt and not g.vorbei:
                self._gefallen(ziel, ich)
            else:
                self._panzerung(ziel, ich, mitte, radius)
                self._faehigkeit_rund(ziel, ich)
                self._hotbar(ziel, ich)
                self._extra_felder(ziel, ich)
                self._munition(ziel, ich)
        if self.tafel_zeigen():
            self._tafel(ziel)
        if g.hinweis:
            self.hinweis(ziel, g.hinweis)

    def tafel_zeigen(self) -> bool:
        """Die Tafel mit dem Punktestand, solange TAB gehalten wird (die
        Taste INVENTAR - im Gefecht gibt es kein Inventar). Nicht, waehrend
        im Testmodus der Spawner offen ist: dort wechselt TAB die Spalte."""
        g = self.g
        if getattr(g, "tafel_fest", False):
            return True
        if getattr(g, "spawner_offen", False) or g.in_lobby:
            return False
        if getattr(g, "schlacht", False):
            return False          # in SCHLACHT gehoert TAB dem Nachschub (seit 0.34.96)
        eingabe = getattr(getattr(g, "app", None), "eingabe", None)
        return bool(eingabe is not None and eingabe.gehalten("inventar"))

    # ---- Oben links ------------------------------------------------
    def _kopf_links(self, ziel) -> None:
        """Oben links: in der Lobby Spielart und Code, im Gefecht die Uhr
        oder das Abschussziel und in PVE die Welle (seit 0.34.92 hier statt
        in der Mitte). Spielart und Karte stehen auf der Tafel (TAB)."""
        g = self.g
        y = 8
        if g.in_lobby:
            _text(ziel, K.MODI[g.modus]["name"], 10, y, K.C_AMBER)
            # Die Adresse braucht man, um sie weiterzusagen - also in der
            # Lobby, und nicht die ganze Runde lang.
            if g.ist_gastgeber:
                # Seit 0.34.13 der Online-Code - mit ihm kommt man von
                # ueberall herein. Die Adresse im LAN nur, wenn die Lobby
                # dort ueberhaupt zu sehen ist.
                code = g.gastgeber.code
                if code:
                    _text(ziel, "CODE: " + code.upper(), 10, y + 9, K.C_AMBER)
                elif g.gastgeber.tunnel is not None:
                    _text(ziel, "CODE: " + g.gastgeber.tunnel.beschreibung()[:30],
                          10, y + 9, K.C_MUTED_DK)
                if not g.gastgeber.nur_lokal:
                    _text(ziel, "LAN: " + g.gastgeber.adresse, 10, y + 18,
                          K.C_MUTED_DK)
            return
        if self._mit_uhr:
            minuten, sekunden = divmod(int(max(0.0, g.rest)), 60)
            farbe = K.C_CREAM
            if g.rest <= 30 and not g.vorbei:
                # Die letzten dreissig Sekunden: die Uhr wird rot. Wer
                # vorn liegt, soll es merken, wer hinten liegt, erst recht.
                farbe = K.C_RED if int(g.rest * 2) % 2 == 0 else K.C_CREAM
            _text(ziel, "%d:%02d" % (minuten, sekunden), 10, y, farbe, 2)
            y += 18
        elif self._mit_abschussziel:
            text = ("BIS %d TEAMABSCHÜSSE" if g.mit_teams
                    else "BIS %d ABSCHÜSSE")
            _text(ziel, text % int(g.ende_wert or K.GEFECHT["team_abschuesse"]),
                  10, y, K.C_MUTED)
            y += 11
        if g.mit_gegnern:
            _text(ziel, "WELLE %d" % max(1, g.welle), 10, y, K.C_CREAM, 2)
            y += 17
            rest = g.gegner_rest
            if rest <= 0 and g.pause_rest > 0 and g.welle > 0:
                _text(ziel, "NÄCHSTE IN %d" % max(1, int(g.pause_rest + 0.99)),
                      10, y, K.C_AMBER)
            elif rest > 0:
                _text(ziel, "NOCH %d" % rest, 10, y, K.C_MUTED)

    # ---- Oben Mitte ------------------------------------------------
    def _kopf_mitte(self, ziel) -> None:
        """Oben in der Mitte: der Stand der Mannschaften - in TEAM als ein
        Balken, der sich nach dem Stand teilt, darunter die Zahlen (seit
        0.34.92) -, und in PVE der Boss."""
        g = self.g
        if g.in_lobby:
            g._lobby_kopf(ziel)
            return
        mitte = W // 2
        y = 8
        if g.mit_gegnern:
            y = self._boss(ziel, mitte, y)
        if g.mit_teams:
            if g.regeln["runden"] or g.regeln["zone"]:
                self._mannschaften(ziel, mitte, y)
            else:
                self._mannschaftsbalken(ziel, mitte, y)

    def _mannschaftsbalken(self, ziel, mitte, y) -> int:
        """Zwei Farben in einem Balken, geteilt nach dem Stand - bei 0:0
        halb und halb. Darunter die Zahlen in ihren Farben."""
        g = self.g
        farben = [k["hud"] for k in K.TEAMS["kombi"]]
        werte = list(g.teampunkte)[:2]
        breite = 150
        summe = werte[0] + werte[1]
        links = int(round(breite * (werte[0] / summe if summe > 0 else 0.5)))
        x0 = mitte - breite // 2
        pygame.draw.rect(ziel, SCHATTEN, (x0 - 1, y - 1, breite + 2, 5))
        if links > 0:
            pygame.draw.rect(ziel, farben[0], (x0, y, links, 3))
        if breite - links > 0:
            pygame.draw.rect(ziel, farben[1], (x0 + links, y, breite - links, 3))
        _text(ziel, "%d" % werte[0], mitte - breite // 4, y + 7, farben[0], 2, "mitte")
        _text(ziel, "%d" % werte[1], mitte + breite // 4, y + 7, farben[1], 2, "mitte")
        return y + 24

    def _boss(self, ziel, mitte, y) -> int:
        """Der Boss, wenn einer da ist: Name ueber dem Balken."""
        boss = self.g.boss_stand()
        if boss is None:
            return y
        name, anteil = boss
        # Name ueber dem Balken, beides in Bernstein - dieselbe Farbe
        # wie der Balken ueber dem Boss selbst.
        _text(ziel, name, mitte, y, K.C_AMBER, 1, "mitte")
        y += 9
        breite = 160
        pygame.draw.rect(ziel, SCHATTEN, (mitte - breite // 2 - 1, y - 1,
                                          breite + 2, 6))
        _balken(ziel, (mitte - breite // 2, y, breite, 4), anteil, K.C_AMBER)
        return y + 9

    @property
    def _mit_uhr(self) -> bool:
        """Die Uhr laeuft ueberall ausser in pve: dort endet die Runde, wenn
        alle liegen, und eine Uhr waere eine Zahl ohne Bedeutung."""
        g = self.g
        return (g.ende_art == "zeit"
                and (g.mit_teams or not g.regeln["revive"]))

    @property
    def _mit_abschussziel(self) -> bool:
        g = self.g
        return (g.ende_art != "zeit" and not g.regeln["zone"]
                and not g.regeln["runden"]
                and (g.mit_teams or not g.regeln["revive"]))

    def _mannschaften(self, ziel, mitte, y) -> int:
        """Der Stand der Mannschaften, je nach Spielart.

        Team: Abschuesse. Versus: gewonnene Runden als Punkte, darunter
        welche Runde laeuft oder dass es Matchpoint ist. Huegel: zwei
        Balken, die von der Mitte aus laufen, und wer den Kreis haelt.
        """
        g = self.g
        kombis = K.TEAMS["kombi"]
        farben = [k["hud"] for k in kombis]
        namen = [k["name"] for k in kombis]
        if g.regeln["runden"]:
            noetig = g.runden_anzahl // 2 + 1
            punkte = max([noetig] + list(g.teampunkte))
            for seite in range(2):
                for i in range(punkte):
                    an = i < g.teampunkte[seite]
                    x = (mitte - 16 - (i + 1) * 9 if seite == 0
                         else mitte + 16 + i * 9)
                    r = pygame.Rect(x, y + 1, 7, 7)
                    pygame.draw.rect(ziel, farben[seite] if an else (24, 17, 12), r)
                    pygame.draw.rect(ziel, farben[seite] if an else K.C_MUTED_DK,
                                     r, 1)
            _text(ziel, namen[0], mitte - 20 - punkte * 9, y, farben[0], 1,
                  "rechts")
            _text(ziel, namen[1], mitte + 20 + punkte * 9, y, farben[1], 1)
            _text(ziel, ":", mitte, y, K.C_MUTED_DK, 1, "mitte")
            y += 11
            if not g._beide_besetzt():
                _text(ziel, "WARTET AUF MITSPIELER", mitte, y, K.C_MUTED, 1,
                      "mitte")
            elif g.runden_pause > 0:
                _text(ziel, "NÄCHSTE RUNDE IN %d"
                      % max(1, int(g.runden_pause + 0.99)), mitte, y,
                      K.C_AMBER, 1, "mitte")
            else:
                _text(ziel, g.runden_text(), mitte, y,
                      K.C_RED if g.matchpoint else K.C_MUTED, 1, "mitte")
            return y + 10

        if g.regeln["zone"]:
            werte = [int(s) for s in g.zone_stand]
        else:
            werte = list(g.teampunkte)
        links_text = "%s %d" % (namen[0], werte[0])
        rechts_text = "%d %s" % (werte[1], namen[1])
        _text(ziel, links_text, mitte - 8, y, farben[0], 1, "rechts")
        _text(ziel, ":", mitte, y, K.C_MUTED_DK, 1, "mitte")
        _text(ziel, rechts_text, mitte + 8, y, farben[1], 1)
        g._teamzeichen(ziel, mitte - 12 - SCHRIFT.breite(links_text, 1) - 9,
                       y - 1, kombis[0])
        g._teamzeichen(ziel, mitte + 12 + SCHRIFT.breite(rechts_text, 1) + 2,
                       y - 1, kombis[1])
        y += 10
        if not g.regeln["zone"]:
            return y
        breite = 80
        for i, stand in enumerate(g.zone_stand[:2]):
            links = mitte - breite - 4 if i == 0 else mitte + 4
            anteil = max(0.0, min(1.0, stand / K.ZONE["bis"]))
            pygame.draw.rect(ziel, SCHATTEN, (links - 1, y - 1, breite + 2, 6))
            pygame.draw.rect(ziel, (24, 17, 12), (links, y, breite, 4))
            fuellung = int(breite * anteil)
            if i == 0:
                # Beide laufen von der Mitte nach aussen: man vergleicht
                # zwei Laengen, die am selben Punkt anfangen.
                pygame.draw.rect(ziel, farben[0],
                                 (links + breite - fuellung, y, fuellung, 4))
            else:
                pygame.draw.rect(ziel, farben[1], (links, y, fuellung, 4))
        y += 8
        if g.zone_halter >= 0:
            _text(ziel, "%s HÄLT DEN KREIS" % namen[g.zone_halter], mitte, y,
                  farben[g.zone_halter], 1, "mitte")
        elif g.ich is not None and g.in_der_zone(g.ich):
            _text(ziel, "UMKÄMPFT", mitte, y, K.C_CREAM, 1, "mitte")
        elif g.zone_name:
            _text(ziel, g.zone_name, mitte, y, K.C_MUTED, 1, "mitte")
        return y + 10

    # ---- Oben rechts -----------------------------------------------
    def _ebenen(self, ziel) -> None:
        """Welche Ebene man anschaut und wo man steht.

        Sind die oberen Ebenen ausgeblendet (Q), stehen ihre Felder
        gedimmt da - sonst fragt man sich, warum ueber einem nichts zu
        sehen ist. (Ein Strich hindurch sah aus wie ein Fehler in der
        Schrift.)
        """
        g = self.g
        if len(g.welt.ebenen) < 2:
            return
        ich = g.ich
        blick = g.blick
        ex = W - 26
        for i in range(len(g.welt.ebenen) - 1, -1, -1):
            ey = 8 + (len(g.welt.ebenen) - 1 - i) * 13
            angeschaut = (i == blick)
            aus = not g.obere_zeigen and i > blick
            r = pygame.Rect(ex, ey, 18, 11)
            pygame.draw.rect(ziel, K.C_AMBER if angeschaut else (18, 12, 9), r)
            pygame.draw.rect(ziel, K.C_AMBER if angeschaut else
                             ((40, 30, 22) if aus else K.C_MUTED_DK), r, 1)
            SCHRIFT.zeichnen(ziel, "E%d" % i, r.centerx, ey + 2,
                             (18, 12, 8) if angeschaut else
                             (K.C_MUTED_DK if aus else K.C_MUTED), 1,
                             ausrichtung="mitte")
            if ich is not None and i == ich.ebene:
                pygame.draw.rect(ziel, K.C_TEAL, (ex - 5, ey + 3, 3, 5))

    def _tafel(self, ziel) -> None:
        """Die Tafel auf TAB (seit 0.34.92, vorher stand oben rechts eine
        gekuerzte Liste): Spielart und Karte, darunter alle - Platz, Name,
        Abschuesse und Tode -, man selbst hervorgehoben."""
        g = self.g
        if not g.kaempfer:
            return
        from . import bestenliste
        reihe = bestenliste.sortiert(
            [{"name": k.name, "abschuesse": k.abschuesse, "tode": k.tode,
              "mvp_punkte": self._mvp(k), "k": k} for k in g.kaempfer.values()])
        breite = K.HUD["tafel_breite"]
        hoehe = 34 + len(reihe) * 10 + 6
        r = pygame.Rect((W - breite) // 2, max(34, (H - hoehe) // 2 - 20), breite, hoehe)
        ui.kasten(ziel, r, K.C_MUTED_DK, (11, 8, 6, 232), 4)
        karte = (g.karte_kopf.get("name") or g.karte or "TESTKARTE").upper()
        _text(ziel, "%s - %s" % (K.MODI[g.modus]["name"], karte), r.centerx, r.y + 6,
              K.C_AMBER, 1, "mitte")
        _text(ziel, "NAME", r.x + 30, r.y + 20, K.C_MUTED_DK)
        _text(ziel, "ABSCHÜSSE / TODE", r.right - 10, r.y + 20, K.C_MUTED_DK, 1, "rechts")
        for i, e in enumerate(reihe):
            wer = e["k"]
            y = r.y + 32 + i * 10
            if wer is g.ich:
                pygame.draw.rect(ziel, (34, 26, 18), (r.x + 4, y - 2, r.width - 8, 10))
            if g.mit_teams:
                farbe = g._farbe_fuer(wer, wer is g.ich)
            elif wer is g.ich:
                farbe = K.C_TEAL
            elif wer.am_boden:
                farbe = K.C_RED
            else:
                farbe = K.C_MUTED
            _text(ziel, "%d" % (i + 1), r.x + 22, y, farbe, 1, "rechts")
            _text(ziel, ui.kuerzen(wer.name, 160), r.x + 30, y, farbe)
            _text(ziel, "%d / %d" % (e["abschuesse"], e["tode"]), r.right - 10, y,
                  farbe, 1, "rechts")

    def _mvp(self, k) -> float:
        """bestenliste.mvp_punkte(k.werte_runde()), gemerkt, solange sich
        die Zahlen der Figur nicht aendern (seit 0.34.75) - die Rechnung
        haengt nur an den Zaehlern in bestenliste.MVP_NAMEN, Abschuessen und
        Toden (nicht etwa an der Strecke, die jeden Schritt waechst)."""
        from . import bestenliste
        merk = self.__dict__.setdefault("_mvp_merk", {})
        z = k.zaehler
        schluessel = (tuple([z.get(n) for n in bestenliste.MVP_NAMEN]),
                      getattr(k, "abschuesse", None), getattr(k, "tode", None))
        hit = merk.get(id(k))
        if hit is not None and hit[0] is k and hit[1] == schluessel:
            return hit[2]
        wert = bestenliste.mvp_punkte(k.werte_runde())
        if len(merk) > 200:
            merk.clear()
        merk[id(k)] = (k, schluessel, wert)
        return wert

    # ---- Unten links: runde Karte, Panzerung, Faehigkeit, Dash -------
    def _karte_rund(self, ziel, ich):
        """Die Karte als Kreis um die eigene Figur (seit 0.34.92), etwas
        groesser als die alte oben links. Gibt (Mitte, Radius) zurueck."""
        g = self.g
        h = K.HUD
        d = h["karte_d"]
        radius = d // 2
        mitte = (h["karte_x"] + radius, H - h["unten"] - radius)
        if not K.MINIKARTE["an"] or not g.welt.ebenen:
            return mitte, radius
        flaeche = self.__dict__.get("_karte_flaeche")
        if flaeche is None or flaeche.get_size() != (d, d):
            flaeche = self._karte_flaeche = pygame.Surface((d, d), pygame.SRCALPHA)
            maske = pygame.Surface((d, d), pygame.SRCALPHA)
            maske.fill((0, 0, 0, 0))
            pygame.draw.circle(maske, (255, 255, 255, 255), (radius, radius), radius)
            self._karte_maske = maske
        flaeche.fill((11, 8, 6, 200))
        nr = max(0, min(len(g.welt.ebenen) - 1, int(ich.ebene)))
        e = g.welt.ebenen[nr]
        # Seit 0.34.96 wieder die ganze Karte (gewuenscht: "wie die alte,
        # nur rund") - die laengere Seite fuellt den Kreis, die Ecken
        # schneidet er ein wenig an. Um die Figur gelegt lag auf grossen
        # Karten oft die Haelfte des Kreises im Leeren.
        f = d * h["karte_ganz"] / float(max(e.pixel_breite, e.pixel_hoehe))
        breite = max(8, int(e.pixel_breite * f))
        hoehe = max(8, int(e.pixel_hoehe * f))
        rahmen = pygame.Rect(0, 0, breite, hoehe)
        rahmen.center = (radius, radius)
        self.minikarte.zeichnen(flaeche, g, rahmen=rahmen, rund=True)
        # Was ausserhalb des Kreises liegt, wird ganz durchsichtig.
        flaeche.blit(self._karte_maske, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        ziel.blit(flaeche, (mitte[0] - radius, mitte[1] - radius))
        pygame.draw.circle(ziel, (84, 66, 48), mitte, radius, 1)
        # Seit 0.34.100 noch einmal in Fensteraufloesung darueber (gewuenscht:
        # "deutlich hoehere Resolution fuer die Minimap"). Nur, wenn nichts
        # davor liegt - ein Menue oder eine andere Szene darueber deckte sie
        # sonst nicht mehr zu.
        if self._karte_frei(g):
            kasten = pygame.Rect(mitte[0] - radius, mitte[1] - radius, d, d)
            g.app.hoch_auflegen(kasten, lambda f, mass: self._karte_hoch(f, mass, rahmen, d))
        return mitte, radius

    @staticmethod
    def _karte_frei(g) -> bool:
        app = getattr(g, "app", None)
        if app is None or not hasattr(app, "hoch_auflegen"):
            return False
        if not app.stapel or app.stapel[-1] is not g:
            return False
        return not (getattr(g, "menue", None) is not None or getattr(g, "pausiert", False)
                    or getattr(g, "belohnung_offen", False)
                    or getattr(g, "_admin_zeile", None) is not None)

    def _karte_hoch(self, f, mass: float, rahmen, d: int) -> None:
        """Die runde Karte in Fenstergroesse (siehe App.hoch_auflegen)."""
        groesse = f.get_size()
        merk = self.__dict__.get("_karte_hoch_merk")
        if merk is None or merk[0] != groesse:
            flaeche = pygame.Surface(groesse, pygame.SRCALPHA)
            maske = pygame.Surface(groesse, pygame.SRCALPHA)
            maske.fill((0, 0, 0, 0))
            rr = min(groesse) // 2
            pygame.draw.circle(maske, (255, 255, 255, 255), (groesse[0] // 2, groesse[1] // 2), rr)
            merk = self._karte_hoch_merk = (groesse, flaeche, maske)
        _g, flaeche, maske = merk
        flaeche.fill((11, 8, 6, 255))
        fx, fy = groesse[0] / float(d), groesse[1] / float(d)
        gross = pygame.Rect(int(rahmen.x * fx), int(rahmen.y * fy),
                            max(8, int(rahmen.width * fx)), max(8, int(rahmen.height * fy)))
        self.minikarte.zeichnen(flaeche, self.g, rahmen=gross, rund=True, mass=mass)
        flaeche.blit(maske, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        f.blit(flaeche, (0, 0))
        rr = min(groesse) // 2
        pygame.draw.circle(f, (84, 66, 48), (groesse[0] // 2, groesse[1] // 2), rr,
                           max(1, int(mass)))

    @staticmethod
    def _bogen(ziel, mitte, radius, teile, farbe_fuer, dicke) -> None:
        """Ein Ring aus `teile` Stuecken, der aussen am Kreis anliegt (seit
        0.34.93: ohne Abstand, ohne Luecken - die Teile trennt nur ein
        dunkler Strich, wie auf der Skizze), von K.HUD bogen_von ueber oben
        bis bogen_bis. farbe_fuer(i) -> (Farbe, Anteil 0..1): so viel des
        Stuecks ist gefuellt, der Rest dunkel."""
        h = K.HUD
        von, bis = h["bogen_von"], h["bogen_bis"]
        je = (von - bis) / float(teile)
        innen, aussen = radius + 0.5, radius + dicke + 0.5
        dunkel = (26, 19, 14)
        cx, cy = mitte

        def flaeche(a0, a1, farbe):
            n = max(2, int(abs(a1 - a0) / 3.0) + 2)
            winkel = [math.radians(a0 + (a1 - a0) * t / (n - 1)) for t in range(n)]
            punkte = ([(cx + aussen * math.cos(w), cy - aussen * math.sin(w)) for w in winkel]
                      + [(cx + innen * math.cos(w), cy - innen * math.sin(w))
                         for w in reversed(winkel)])
            pygame.draw.polygon(ziel, farbe, punkte)

        for i in range(teile):
            a0 = von - i * je
            a1 = von - (i + 1) * je
            farbe, anteil = farbe_fuer(i)
            flaeche(a0, a1, dunkel)
            if farbe is not None and anteil > 0.0:
                flaeche(a0, a0 + (a1 - a0) * min(1.0, anteil), farbe)
        # Die Striche zwischen den Teilen und an beiden Enden.
        for i in range(teile + 1):
            w = math.radians(von - i * je)
            pygame.draw.line(ziel, (10, 7, 5),
                             (cx + (innen - 0.5) * math.cos(w), cy - (innen - 0.5) * math.sin(w)),
                             (cx + (aussen + 0.5) * math.cos(w), cy - (aussen + 0.5) * math.sin(w)), 1)

    def _panzerung(self, ziel, ich, mitte, radius) -> None:
        """Die Panzerung als Bogen um die Karte - in Platten wie vorher
        (K.HUD segmente), rot, wenn es eng wird."""
        anteil = max(0.0, ich.leben / ich.max_leben)
        farbe = K.C_TEAL if anteil > 0.35 else K.C_RED
        teile = K.HUD["segmente"]
        self._bogen(ziel, mitte, radius + K.HUD["bogen_abstand"], teile,
                    lambda i: (farbe, 1.0 if i / float(teile) < anteil else 0.0),
                    K.HUD["bogen_dicke"])

    def _faehigkeit_rund(self, ziel, ich) -> None:
        """Der Kreis der Faehigkeit (Taste C) neben der Karte, die Dashes
        als Ring darum - die naechste Ladung fuellt sich sichtbar. Ueber
        dem Ring der Name. Das Medkit hat seit 0.34.93 ein Feld neben der
        Hotbar."""
        g = self.g
        h = K.HUD
        r = h["faeh_d"] // 2
        mitte = (h["karte_x"] + h["karte_d"] + h["faeh_luft"] + r, H - h["unten"] - r)
        pygame.draw.circle(ziel, (18, 13, 9), mitte, r)
        pygame.draw.circle(ziel, K.C_MUTED_DK, mitte, r, 1)
        from . import klassen as klassen_modul
        arten = (klassen_modul.faehigkeiten_von(ich)
                 if getattr(g, "faehigkeiten_an", False) else ())
        if arten:
            rest = getattr(ich, "faehigkeit_rest", {}) or {}
            r0 = min(rest.get(a, 0.0) for a, _p in arten)
            taste = g._tastenname("faehigkeit")[:1] if hasattr(g, "_tastenname") else "C"
            if r0 <= 0.0:
                _text(ziel, taste, mitte[0], mitte[1] - 3, K.C_TEAL, 1, "mitte")
            else:
                # Nach dem Benutzen der Countdown, in Grau (seit 0.34.93).
                _text(ziel, "%d" % math.ceil(r0), mitte[0], mitte[1] - 3, (150, 146, 140), 1, "mitte")
            namen = ", ".join(klassen_modul.FAEHIGKEIT_NAMEN.get(a, a.upper()) for a, _p in arten)
            if getattr(ich, "alle_werkzeuge", False) and not getattr(ich, "klasse", ""):
                # Jeder hat alles: welches Werkzeug, und wie man wechselt.
                namen += " [%s]" % (g._tastenname("werkzeug")[:1]
                                    if hasattr(g, "_tastenname") else "X")
            # Links buendig ueber dem Kreis: so liegt er nie auf der Karte.
            # Seit 0.34.94 in Bernstein (wie die Hotbar) und ein Stueck nach
            # rechts oben - gewuenscht.
            _text(ziel, ui.kuerzen(namen, W // 2 - 60 - (mitte[0] - r)), mitte[0] - r + 4,
                  mitte[1] - r - h["bogen_abstand"] - h["bogen_dicke"] - 12,
                  K.C_AMBER if r0 <= 0.0 else K.C_MUTED_DK)
        else:
            _text(ziel, "-", mitte[0], mitte[1] - 3, K.C_MUTED_DK, 1, "mitte")
        # Dash: die Ladungen als Bogen, die naechste fuellt sich.
        voll = K.DASH["ladungen"]
        laden = ich.dash_laden

        def dash(i):
            if i < ich.dash_ladungen:
                return K.C_AMBER, 1.0
            if i == ich.dash_ladungen:
                return K.C_MUTED_DK, laden
            return None, 0.0
        self._bogen(ziel, mitte, r + h["bogen_abstand"], voll, dash, h["bogen_dicke"])

    # ---- Neben der Hotbar: Brecheisen und Medkit (seit 0.34.93) ----------
    def extra_rechtecke(self, ich) -> list:
        """(Art, Rechteck) der beiden Felder rechts neben der Hotbar, mit
        etwas Abstand: das Brecheisen (F) und das Medkit (H) - das nur,
        wenn es in dieser Runde Medkits gibt."""
        g = self.g
        if getattr(g, "gruppen_hotbar", False):
            n = len(K.ALLES_GRUPPEN)
        else:
            n = len(ich.waffen)
        r = self.hotbar_rechteck(n)
        groesse = K.HUD["extra_feld"]
        x = r.right + K.HUD["extra_abstand"]
        y = r.bottom - groesse + 2
        raus = [("nahkampf", pygame.Rect(x, y, groesse, groesse))]
        if g.start_medkits > 0 or g.medkits_spawnen or ich.medkits > 0:
            raus.append(("medkit", pygame.Rect(x + groesse + 3, y, groesse, groesse)))
        return raus

    def _passend(self, bild, r):
        """Das Symbol so klein, dass es mit Rand ins Feld passt - nie groesser
        als es ist (seit 0.34.94)."""
        rand = K.HUD["extra_rand"]
        platz_b, platz_h = r.width - 2 * rand, r.height - 2 * rand
        if bild.get_width() <= platz_b and bild.get_height() <= platz_h:
            return bild
        return self._klein(bild, min(platz_b / float(bild.get_width()),
                                     platz_h / float(bild.get_height())))

    def _extra_felder(self, ziel, ich) -> None:
        g = self.g
        for art, r in self.extra_rechtecke(ich):
            if art == "nahkampf":
                bereit = ich.nahkampf_rest <= 0.0
                ui.kasten(ziel, r, K.C_MUTED_DK, KASTEN, 3)
                # Seit 0.34.96 die Waffe auf F, nicht immer das Brecheisen.
                nk = getattr(ich, "nahkampf_name", K.NAHKAMPF["waffe"])
                sym = self._passend(g.renderer.bilder.bild("waffe_" + nk), r)
                ziel.blit(sym, (r.centerx - sym.get_width() // 2, r.centery - sym.get_height() // 2))
                SCHRIFT.zeichnen(ziel, g._tastenname("nahkampf")[:1], r.x + 2, r.y + 2,
                                 K.C_AMBER if bereit else K.C_MUTED_DK, 1)
            else:
                da = ich.medkits > 0
                ui.kasten(ziel, r, K.C_TEAL_DK if da else K.C_MUTED_DK,
                          KASTEN if da else (20, 14, 10, 200), 3)
                if ich.heilt_rest > 0:
                    fertig = 1.0 - ich.heilt_rest / K.MEDKIT["dauer"]
                    _balken(ziel, (r.x + 2, r.bottom - 4, r.width - 4, 2), fertig, K.C_TEAL)
                sym = self._passend(g.renderer.bilder.bild("medkit"), r)
                if not da:
                    sym = self._blass(sym)
                ziel.blit(sym, (r.centerx - sym.get_width() // 2, r.centery - sym.get_height() // 2))
                SCHRIFT.zeichnen(ziel, g._tastenname("heilen")[:1], r.x + 2, r.y + 2,
                                 K.C_TEAL if da else K.C_MUTED_DK, 1)
                _text(ziel, "%d" % ich.medkits, r.right - 2, r.bottom - 8,
                      K.C_CREAM if da else K.C_MUTED_DK, 1, "rechts")

    def _klein(self, bild, faktor):
        merk = self.__dict__.setdefault("_klein_merk", {})
        schluessel = (id(bild), round(faktor, 3))
        hit = merk.get(schluessel)
        if hit is None or hit[0] is not bild:
            neu = pygame.transform.scale(bild, (max(1, int(bild.get_width() * faktor)),
                                                max(1, int(bild.get_height() * faktor))))
            hit = merk[schluessel] = (bild, neu)
        return hit[1]

    def _blass(self, bild):
        merk = self.__dict__.setdefault("_blass_merk", {})
        hit = merk.get(id(bild))
        if hit is None or hit[0] is not bild:
            neu = bild.copy()
            neu.fill((110, 110, 110, 160), special_flags=pygame.BLEND_RGBA_MULT)
            hit = merk[id(bild)] = (bild, neu)
        return hit[1]

    # ---- Am Zeiger: das Magazin (seit 0.34.93) ----------------------------
    def _munition(self, ziel, ich) -> None:
        """Die Patronen im Magazin dort, wo man hinschaut: gross rechts unter
        dem Zeiger. Gelb, wenn es knapp wird, rot blinkend, wenn es leer ist;
        beim Nachladen ein Balken. Nach einem Wechsel steht kurz der Name der
        Waffe darueber. (Vorher ein grosser Kasten unten rechts.) Mit
        Touch-Steuerung, wo es keinen Zeiger gibt, ueber der Hotbar."""
        g = self.g
        d = ich.waffe_daten
        name = ich.waffe_name
        jetzt = g.welt.zeit
        if self.__dict__.get("_waffe_vorher") != name:
            self._waffe_vorher = name
            self._waffe_seit = jetzt
        touch = getattr(getattr(g, "app", None), "touch", None) is not None
        eingabe = getattr(getattr(g, "app", None), "eingabe", None)
        if touch or eingabe is None:
            x, y = W // 2 + 60, HOTBAR_Y - 30
        else:
            x, y = int(eingabe.maus.x) + 11, int(eingabe.maus.y) + 7
            x = max(4, min(W - 60, x))
            y = max(16, min(H - 30, y))
        if jetzt - self._waffe_seit < K.HUD["waffe_zeigen"]:
            _text(ziel, d["name"], x, y - 10, K.C_AMBER)
        kurz = d.get("kurz")
        if getattr(ich, "anlauf", 0.0) > 0.02:
            _balken(ziel, (x, y - 2, 24, 2), ich.anlauf, K.C_TEAL)
        if d.get("kuehlt"):
            # Chor-Waffen (seit 0.34.130): Hitze statt Munition. Ueberhitzt
            # fuellt sich der Balken rot, bis sie wieder geht.
            voll = max(1, int(d["magazin"]))
            rest = getattr(ich, "ueberhitzt", {}).get(name, 0.0)
            pygame.draw.rect(ziel, SCHATTEN, (x - 1, y + 3, 30, 5))
            if rest > 0.0:
                gesamt = d.get("ueberhitzt", d["nachladen"]) * getattr(ich, "kuehl_faktor", 1.0)
                _balken(ziel, (x, y + 4, 28, 3), 1.0 - rest / max(0.1, gesamt), K.C_RED)
                _text(ziel, "KÜHLT", x + 32, y + 1, K.C_RED if (jetzt * 3.0) % 1.0 < 0.6 else (150, 50, 36))
            else:
                hitze = 1.0 - ich.magazin.get(name, 0) / float(voll)
                _balken(ziel, (x, y + 4, 28, 3), hitze, K.C_AMBER if hitze < 0.75 else K.C_RED)
            return
        if ich.nachlade_rest > 0 and d.get("nachladen"):
            fertig = 1.0 - ich.nachlade_rest / d["nachladen"]
            pygame.draw.rect(ziel, SCHATTEN, (x - 1, y + 3, 30, 5))
            _balken(ziel, (x, y + 4, 28, 3), fertig, K.C_AMBER)
            return
        if not d.get("magazin"):
            return
        munition = ich.magazin.get(name, 0)
        voll = max(1, int(d["magazin"]))
        if not munition:
            farbe = K.C_RED if (jetzt * 4.0) % 1.0 < 0.6 else (90, 26, 20)
        elif munition <= max(1, voll // 4):
            farbe = K.C_AMBER
        else:
            farbe = K.C_CREAM
        _text(ziel, "%d" % munition, x, y, farbe, 2)
        breite = SCHRIFT.breite("%d" % munition, 2)
        if g.knapp:
            vorrat = ich.vorrat.get(name, 0)
            _text(ziel, "/%d" % vorrat, x + breite + 3, y + 7,
                  K.C_RED if not vorrat else K.C_MUTED)
        if kurz:
            # Die Betriebsart (MG, Revolver): was gleich passiert.
            _text(ziel, kurz, x + breite + 3, y, K.C_TEAL)

    # ---- Unten Mitte: die Hotbar --------------------------------------
    def _hotbar(self, ziel, ich) -> None:
        """Zwei Modi: Loadout (wenige grosse Felder) oder alles (neun kleine).

        Mit Loadout traegt man drei Dinge, und die sollen gross und
        eindeutig dastehen, dazu der Name des Loadouts. Ohne Loadout hat
        man alles, und dann muessen neun Felder zwischen die beiden Kaesten
        passen. Der Vorrat steht unter dem Feld, nicht darin - im Feld
        ueberdeckte er das Symbol.
        """
        g = self.g
        if getattr(g, "gruppen_hotbar", False):
            self._gruppen_hotbar(ziel, ich)
            return
        n = len(ich.waffen)
        gross = self.hotbar_gross(n)
        bw, bh, luecke = self._hotbar_mass(n)
        rahmen_ganz = self.hotbar_rechteck(n)
        hx, hy = rahmen_ganz.x, rahmen_ganz.y
        titel = self._hotbar_titel(ich)
        if titel:
            # 12 statt 10 ueber der Hotbar (seit 0.34.94, gewuenscht).
            _text(ziel, titel, W // 2, hy - 12, K.C_MUTED_DK, 1, "mitte")
        for i, name in enumerate(ich.waffen):
            aktiv = (i == ich.waffe)
            r = pygame.Rect(hx + i * (bw + luecke), hy - (2 if aktiv else 0),
                            bw, bh)
            wd = K.WAFFEN[name]
            leer = bool(wd.get("magazin")) and not ich.magazin.get(name, 0) \
                and (not g.knapp or not ich.vorrat.get(name, 0))
            c4_bereit = (name == "c4" and _c4_hotbar_symbol(ich)
                         == "waffe_detonator_bereit")
            rahmen = (K.C_TEAL if c4_bereit else
                      K.C_RED if leer and aktiv else
                      K.C_AMBER if aktiv else K.C_MUTED_DK)
            ui.kasten(ziel, r, rahmen, (34, 10, 8, 230) if leer else KASTEN, 3)
            symbol = (_c4_hotbar_symbol(ich) if name == "c4" else
                      "waffe_" + name)
            sym = g.renderer.bilder.bild(symbol)
            ziel.blit(sym, (r.centerx - sym.get_width() // 2,
                            r.centery - sym.get_height() // 2))
            SCHRIFT.zeichnen(ziel, "%d" % ((i + 1) % 10), r.x + 3, r.y + 2,
                             K.C_AMBER if aktiv else K.C_MUTED_DK, 1)
            if (g.knapp or wd.get("art") == "wurf") and wd.get("magazin"):
                vorrat = ich.vorrat.get(name, 0) + ich.magazin.get(name, 0)
                _text(ziel, "%d" % vorrat, r.centerx, r.bottom + 2,
                      K.C_RED if not vorrat else
                      (K.C_AMBER if aktiv else K.C_MUTED), 1, "mitte")

    def _gruppen_hotbar(self, ziel, ich) -> None:
        """JEDER HAT ALLES (seit 0.34.85): neun Felder, eines je Gruppe aus
        K.ALLES_GRUPPEN. Im Feld die Waffe, die man dort zuletzt hatte (die
        gehaltene, wenn sie in der Gruppe ist), darunter so viele Punkte,
        wie die Gruppe Waffen hat - der helle ist die gezeigte."""
        g = self.g
        n = len(K.ALLES_GRUPPEN)
        bw, bh, luecke = self._hotbar_mass(n)
        rahmen_ganz = self.hotbar_rechteck(n)
        hx, hy = rahmen_ganz.x, rahmen_ganz.y
        jetzt = ich.waffe_name
        merk = getattr(g, "_gruppe_zuletzt", {})
        name_aktiv = ""
        # Welche Plaetze zu welcher Gruppe gehoeren, je Waffenliste einmal
        # (seit 0.34.89) - dieselben Listen wie vorher je Bild und Gruppe.
        schluessel = tuple(ich.waffen)
        merk_gr = self.__dict__.get("_gruppen_plaetze")
        if merk_gr is None or merk_gr[0] != schluessel:
            gruppe_von = K.ALLES_GRUPPE_VON.get
            je = [[] for _ in K.ALLES_GRUPPEN]
            for j, w in enumerate(ich.waffen):
                gi = gruppe_von(w, -1)
                if gi >= 0:
                    je[gi].append(j)
            merk_gr = self._gruppen_plaetze = (schluessel, je)
        for i, (gname, _w) in enumerate(K.ALLES_GRUPPEN):
            drin = merk_gr[1][i]
            if not drin:
                continue
            aktiv = jetzt in [ich.waffen[j] for j in drin]
            zeige = ich.waffe if aktiv else merk.get(i, drin[0])
            if zeige not in drin:
                zeige = drin[0]
            name = ich.waffen[zeige]
            if aktiv:
                name_aktiv = gname
            r = pygame.Rect(hx + i * (bw + luecke), hy - (2 if aktiv else 0), bw, bh)
            wd = K.WAFFEN[name]
            leer = bool(wd.get("magazin")) and not ich.magazin.get(name, 0) \
                and (not g.knapp or not ich.vorrat.get(name, 0))
            rahmen = (K.C_RED if leer and aktiv else K.C_AMBER if aktiv else K.C_MUTED_DK)
            ui.kasten(ziel, r, rahmen, (34, 10, 8, 230) if leer else KASTEN, 3)
            symbol = _c4_hotbar_symbol(ich) if name == "c4" else "waffe_" + name
            sym = g.renderer.bilder.bild(symbol)
            ziel.blit(sym, (r.centerx - sym.get_width() // 2, r.centery - sym.get_height() // 2))
            SCHRIFT.zeichnen(ziel, "%d" % (i + 1), r.x + 3, r.y + 2,
                             K.C_AMBER if aktiv else K.C_MUTED_DK, 1)
            # Punkte: wie viele Waffen die Gruppe hat, welche gezeigt ist.
            x0 = r.centerx - (len(drin) * 3 - 1) // 2
            for p_, j in enumerate(drin):
                pygame.draw.rect(ziel, K.C_AMBER if j == zeige and aktiv else
                                 (K.C_MUTED if j == zeige else K.C_MUTED_DK),
                                 (x0 + p_ * 3, r.bottom + 2, 2, 2))
        titel = "%s - NOCHMAL DRÜCKEN: NÄCHSTE" % name_aktiv if name_aktiv else "JEDER HAT ALLES"
        _text(ziel, titel, W // 2, hy - 10, K.C_MUTED_DK, 1, "mitte")

    @staticmethod
    def hotbar_gross(anzahl: int) -> bool:
        """Loadout-Modus: so wenige Plaetze, dass sie gross sein duerfen."""
        return anzahl <= 4

    def _hotbar_mass(self, anzahl: int):
        if self.hotbar_gross(anzahl):
            return 52, 22, 4
        # Die Felder werden schmaler, wenn mehr Waffen dazukommen. Mit 30
        # festen Pixeln passten neun Felder zwischen die beiden Kaesten;
        # mit C4 (0.32.27) sind es zehn, und die Hotbar ragte drei Pixel
        # in den Waffenkasten rechts. Die Waffenbilder sind 26 breit.
        luecke = 2
        # Die Hotbar steht in der Bildmitte; seit 0.34.92 ist links mehr
        # belegt als rechts - zaehlt also die schmalere Seite, doppelt.
        platz = 2 * min(W // 2 - LINKS.right, RECHTS.left - W // 2) - 8
        breite = min(30, (platz - (anzahl - 1) * luecke) // max(1, anzahl))
        return max(26, breite), 20, luecke

    def hotbar_rechteck(self, anzahl: int) -> pygame.Rect:
        """Wo die Hotbar steht, ohne das Anheben des gewaehlten Platzes."""
        bw, bh, luecke = self._hotbar_mass(anzahl)
        gesamt = anzahl * bw + (anzahl - 1) * luecke
        y = HOTBAR_Y + (0 if self.hotbar_gross(anzahl) else 2)
        return pygame.Rect((W - gesamt) // 2, y, gesamt, bh)

    def hotbar_plaetze(self, anzahl: int) -> list:
        """Die Rechtecke der einzelnen Plaetze - zum Antippen (touch.py)."""
        bw, bh, luecke = self._hotbar_mass(anzahl)
        r = self.hotbar_rechteck(anzahl)
        return [pygame.Rect(r.x + i * (bw + luecke), r.y, bw, bh) for i in range(anzahl)]

    def _hotbar_titel(self, ich) -> str:
        """Was ueber der Hotbar steht: welches Loadout, oder der Werfer."""
        g = self.g
        if getattr(ich, "rpg", False):
            return "RAKETENWERFER - EIN SCHUSS"
        if g.loadout_regel == "gleich":
            lo = g._fest_loadout() if g.ist_gastgeber else None
            return ("FÜR ALLE: %s" % lo["name"].upper() if lo
                    else "LOADOUT VOM GASTGEBER")
        if g.loadout_regel == "eigenes":
            lo = g.mein_loadout()
            return "LOADOUT %s" % lo["name"].upper() if lo else ""
        return ""

    # ---- Mitte: am Boden, gefallen, Hinweis --------------------------
    def _am_boden(self, ziel, ich) -> None:
        g = self.g
        # Unten, wo sonst Waffe und Hotbar stehen - die braucht man jetzt
        # nicht, und die Mitte des Bildes bleibt frei: man will sehen, wer
        # kommt, zum Helfen oder zum Erledigen.
        r = pygame.Rect(W // 2 - 90, H - 64, 180, 52)
        ui.kasten(ziel, r, K.C_RED, KASTEN, 4)
        _text(ziel, "AM BODEN  %d" % max(0, int(ich.boden_rest + 0.99)),
              r.centerx, r.y + 5, K.C_RED, 1, "mitte")
        _balken(ziel, (r.x + 10, r.y + 15, r.width - 20, 3),
                ich.boden_rest / max(0.1, ich.boden_zeit), K.C_RED)
        if ich.revive_stand > 0:
            _balken(ziel, (r.x + 10, r.y + 15, r.width - 20, 3),
                    ich.revive_stand, K.C_TEAL)
            _text(ziel, "WIRD AUFGEHOLFEN", r.centerx, r.y + 23, K.C_TEAL, 1,
                  "mitte")
        elif ich.ruf_sperre > 0:
            _text(ziel, "GERUFEN", r.centerx, r.y + 23, K.C_MUTED, 1, "mitte")
        else:
            _text(ziel, "[%s] RUFEN" % g._tastenname("nutzen"), r.centerx,
                  r.y + 23, K.C_AMBER, 1, "mitte")
        # Aufgeben (seit 0.34.129): R halten, der Balken fuellt sich.
        ab = g.__dict__.get("_aufgeben_ab")
        if ab is not None:
            anteil = min(1.0, (g._zeit - ab) / K.REVIVE["aufgeben"])
            _balken(ziel, (r.x + 10, r.y + 34, r.width - 20, 3), anteil, K.C_AMBER)
            _text(ziel, "AUFGEBEN ...", r.centerx, r.y + 40, K.C_AMBER, 1, "mitte")
        else:
            _text(ziel, "[%s] HALTEN: AUFGEBEN" % g._tastenname("nachladen"), r.centerx,
                  r.y + 37, K.C_MUTED, 1, "mitte")

    def _gefallen(self, ziel, ich) -> None:
        g = self.g
        if getattr(g, "einstieg_offen", False):
            return            # die Einstiegskarte sagt es (seit 0.34.131)
        _text(ziel, "GEFALLEN", W // 2, H // 2 - 10, K.C_RED, 2, "mitte")
        if g.regeln["runden"]:
            _text(ziel, "RAUS BIS ZUR NÄCHSTEN RUNDE", W // 2, H // 2 + 8,
                  K.C_MUTED, 1, "mitte")
        elif not g.regeln["revive"]:
            _text(ziel, "WIEDER IN %.0f" % max(0.0, ich.wieder_in), W // 2,
                  H // 2 + 8, K.C_MUTED, 1, "mitte")

    def hinweis(self, ziel, text) -> None:
        breite = SCHRIFT.breite(text, 1) + 14
        r = pygame.Rect((W - breite) // 2, HINWEIS_Y, breite, 15)
        ui.kasten(ziel, r, K.C_AMBER, KASTEN, 3)
        SCHRIFT.zeichnen(ziel, text, r.centerx, r.y + 4, K.C_CREAM, 1,
                         ausrichtung="mitte")
