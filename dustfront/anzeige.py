"""
DUSTFRONT - Die Anzeige im Gefecht
==================================

Seit 0.27 eine eigene Datei und kein Anhang des Renderers mehr. Die alte
Anzeige war ueber die Versionen gewachsen: jede Neuerung bekam einen
Platz, wo gerade einer frei war. Das Ergebnis lief ineinander - die
Hotbar mit neun Plaetzen ueberdeckte die Lebenszahl und die Medkits, der
Vorrat stand quer ueber den Waffensymbolen, die Adresse des Gastgebers
stand die ganze Runde oben links, und den Dash sah man gar nicht.

Jetzt hat alles einen festen Ort:

    oben links     die Minikarte, darunter Spielart und Karte
    oben Mitte     worum es gerade geht: Uhr, Welle, Mannschaften, Boss
    oben rechts    Ebenen, darunter der Punktestand (nur die ersten fuenf)
    unten links    Panzerung, Dash, Medkits
    unten rechts   Waffe, Magazin, Vorrat
    unten Mitte    die Hotbar - und darueber ein Hinweis, wenn es einen gibt

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

# Die festen Orte. Hier und nur hier - wer etwas verschiebt, sieht auf
# einen Blick, was noch in der Naehe liegt.
UNTEN = H - 40                  # Oberkante der unteren Kaesten
LINKS = pygame.Rect(8, UNTEN, 156, 32)
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
        g = self.g
        r = self.minikarte.zeichnen(ziel, g) if K.MINIKARTE["an"] else None
        self._karte_unten = r.bottom + 2 if r is not None else 0
        self._kopf_links(ziel)
        self._kopf_mitte(ziel)
        self._ebenen(ziel)
        self._punkte(ziel)
        ich = g.ich
        if ich is not None:
            if ich.am_boden:
                self._am_boden(ziel, ich)
            elif not ich.lebt and not g.vorbei:
                self._gefallen(ziel, ich)
            else:
                self._vital(ziel, ich)
                self._waffe(ziel, ich)
                self._hotbar(ziel, ich)
        if g.hinweis:
            self.hinweis(ziel, g.hinweis)

    # ---- Oben links ------------------------------------------------
    def _kopf_links(self, ziel) -> None:
        g = self.g
        # Unter der Minikarte, wenn es eine gibt.
        y = self._karte_unten + 4 if self._karte_unten else 8
        _text(ziel, K.MODI[g.modus]["name"], 10, y, K.C_AMBER)
        if g.in_lobby:
            # Die Adresse braucht man, um sie weiterzusagen - also in der
            # Lobby, und nicht die ganze Runde lang. Die Karte heisst hier
            # wie die Spielart; zweimal LOBBY sagt nichts.
            if g.ist_gastgeber:
                _text(ziel, g.gastgeber.adresse, 10, y + 9, K.C_MUTED_DK)
            return
        karte = (g.karte_kopf.get("name") or g.karte or "TESTKARTE").upper()
        _text(ziel, karte, 10, y + 9, K.C_MUTED)

    # ---- Oben Mitte ------------------------------------------------
    def _kopf_mitte(self, ziel) -> None:
        g = self.g
        if g.in_lobby:
            g._lobby_kopf(ziel)
            return
        mitte = W // 2
        y = 6
        if g.mit_gegnern:
            y = self._welle(ziel, mitte, y)
        if self._mit_uhr:
            minuten, sekunden = divmod(int(max(0.0, g.rest)), 60)
            gross = not g.mit_gegnern
            farbe = K.C_CREAM
            if g.rest <= 30 and not g.vorbei:
                # Die letzten dreissig Sekunden: die Uhr wird rot. Wer
                # vorn liegt, soll es merken, wer hinten liegt, erst recht.
                farbe = K.C_RED if int(g.rest * 2) % 2 == 0 else K.C_CREAM
            _text(ziel, "%d:%02d" % (minuten, sekunden), mitte, y, farbe,
                  2 if gross else 1, "mitte")
            y += 17 if gross else 10
        elif self._mit_abschussziel:
            text = ("BIS %d TEAMABSCHUESSE" if g.mit_teams
                    else "BIS %d ABSCHUESSE")
            _text(ziel, text % int(g.ende_wert or K.GEFECHT["team_abschuesse"]),
                  mitte, y + 2, K.C_MUTED, 1, "mitte")
            y += 12
        if g.mit_teams:
            self._mannschaften(ziel, mitte, y)

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

    def _welle(self, ziel, mitte, y) -> int:
        """Welle, wie viele noch, und der Boss, wenn einer da ist."""
        g = self.g
        _text(ziel, "WELLE %d" % max(1, g.welle), mitte, y, K.C_CREAM, 2,
              "mitte")
        y += 17
        rest = g.gegner_rest
        if rest <= 0 and g.pause_rest > 0 and g.welle > 0:
            _text(ziel, "NAECHSTE IN %d" % max(1, int(g.pause_rest + 0.99)),
                  mitte, y, K.C_AMBER, 1, "mitte")
        elif rest > 0:
            _text(ziel, "NOCH %d" % rest, mitte, y, K.C_MUTED, 1, "mitte")
        y += 10
        boss = g.boss_stand()
        if boss is not None:
            name, anteil = boss
            # Name ueber dem Balken, beides in Bernstein - dieselbe Farbe
            # wie der Balken ueber dem Boss selbst. Wer die Mitte des
            # Bildes nicht sieht, sieht hier, wie weit er ist.
            _text(ziel, name, mitte, y, K.C_AMBER, 1, "mitte")
            y += 9
            breite = 160
            pygame.draw.rect(ziel, SCHATTEN, (mitte - breite // 2 - 1, y - 1,
                                              breite + 2, 6))
            _balken(ziel, (mitte - breite // 2, y, breite, 4), anteil,
                    K.C_AMBER)
            y += 9
        return y

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
                _text(ziel, "NAECHSTE RUNDE IN %d"
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
            _text(ziel, "%s HAELT DEN KREIS" % namen[g.zone_halter], mitte, y,
                  farben[g.zone_halter], 1, "mitte")
        elif g.ich is not None and g.in_der_zone(g.ich):
            _text(ziel, "UMKAEMPFT", mitte, y, K.C_CREAM, 1, "mitte")
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

    def _punkte(self, ziel) -> None:
        """Der Punktestand: die ersten fuenf, und man selbst immer.

        Vorher standen alle untereinander. Bei acht Leuten war das ein
        Block bis zur Bildmitte, den niemand liest - wer wissen will, wie
        es steht, will die Spitze sehen und wo er selbst ist.
        """
        g = self.g
        if g.in_lobby or not g.kaempfer:
            return
        from . import bestenliste
        reihe = bestenliste.sortiert(
            [{"name": k.name, "abschuesse": k.abschuesse, "tode": k.tode,
              "k": k} for k in g.kaempfer.values()])
        zeigen = reihe[:5]
        if g.ich is not None and not any(e["k"] is g.ich for e in zeigen):
            zeigen = reihe[:4] + [e for e in reihe if e["k"] is g.ich]
        oben = 8 + len(g.welt.ebenen) * 13 + 6
        rechts = W - 10
        for i, e in enumerate(zeigen):
            wer = e["k"]
            platz = reihe.index(e) + 1
            if g.mit_teams:
                farbe = g._farbe_fuer(wer, wer is g.ich)
            elif wer is g.ich:
                farbe = K.C_TEAL
            elif wer.am_boden:
                farbe = K.C_RED
            else:
                farbe = K.C_MUTED
            y = oben + i * 9
            _text(ziel, "%d %-9s" % (platz, wer.name[:9]), rechts - 42, y,
                  farbe, 1, "rechts")
            _text(ziel, "%d/%d" % (e["abschuesse"], e["tode"]), rechts, y,
                  farbe, 1, "rechts")

    # ---- Unten links: Panzerung, Dash, Medkits ------------------------
    def _vital(self, ziel, ich) -> None:
        g = self.g
        r = LINKS
        ui.kasten(ziel, r, K.C_MUTED_DK, KASTEN, 4)
        anteil = max(0.0, ich.leben / ich.max_leben)
        farbe = K.C_TEAL if anteil > 0.35 else K.C_RED
        _text(ziel, "PANZERUNG", r.x + 6, r.y + 4, K.C_MUTED)
        _text(ziel, "%d" % max(0, round(ich.leben)), r.right - 6, r.y + 4,
              farbe if anteil <= 0.35 else K.C_CREAM, 1, "rechts")
        # Segmente wie bisher - die Panzerung ist ein Satz Platten, kein
        # weicher Balken.
        segmente = 18
        sw = (r.width - 12) // segmente
        for i in range(segmente):
            an = i / segmente < anteil
            pygame.draw.rect(ziel, farbe if an else (26, 19, 14),
                             (r.x + 6 + i * sw, r.y + 13, sw - 2, 6))
        y = r.y + 23
        if ich.heilt_rest > 0:
            # Waehrend das Medkit angelegt wird, zeigt die Zeile nur das:
            # wie lange es noch dauert. Man kann gerade nichts anderes tun.
            fertig = 1.0 - ich.heilt_rest / K.MEDKIT["dauer"]
            _text(ziel, "MEDKIT", r.x + 6, y, K.C_TEAL)
            _balken(ziel, (r.x + 46, y + 2, r.width - 52, 3), fertig, K.C_TEAL)
            return
        # Dash: die Ladungen, die naechste fuellt sich sichtbar. Die
        # Breite teilt sich der Platz bis zu den Medkits (x + 74).
        _text(ziel, "DASH", r.x + 6, y, K.C_MUTED)
        voll = K.DASH["ladungen"]
        schritt = max(6, min(14, 40 // max(1, voll)))
        breit = schritt - 2
        for i in range(voll):
            x = r.x + 32 + i * schritt
            pygame.draw.rect(ziel, (26, 19, 14), (x, y + 1, breit, 4))
            if i < ich.dash_ladungen:
                pygame.draw.rect(ziel, K.C_AMBER, (x, y + 1, breit, 4))
            elif i == ich.dash_ladungen:
                pygame.draw.rect(ziel, K.C_MUTED_DK,
                                 (x, y + 1, int(breit * ich.dash_laden), 4))
        # Medkits nur, wenn es in dieser Runde welche gibt.
        if g.start_medkits <= 0 and not g.medkits_spawnen and ich.medkits <= 0:
            return
        x = r.x + 74
        _text(ziel, "[%s]" % g._tastenname("heilen")[:1], x, y, K.C_MUTED)
        for i in range(K.MEDKIT["hoechstens"]):
            mr = pygame.Rect(x + 20 + i * 9, y, 7, 6)
            pygame.draw.rect(ziel, K.C_TEAL if i < ich.medkits else (24, 18, 13), mr)
            pygame.draw.rect(ziel, K.C_TEAL_DK, mr, 1)

    # ---- Unten rechts: die Waffe ----------------------------------
    def _waffe(self, ziel, ich) -> None:
        g = self.g
        r = RECHTS
        ui.kasten(ziel, r, K.C_MUTED_DK, KASTEN, 4)
        d = ich.waffe_daten
        name = ich.waffe_name
        _text(ziel, d["name"], r.x + 6, r.y + 4, K.C_AMBER)
        kurz = d.get("kurz")
        if kurz:
            # Die Betriebsart (MG): was gleich passiert, wenn man drueckt.
            _text(ziel, kurz, r.right - 6, r.y + 4, K.C_TEAL, 1, "rechts")
        if getattr(ich, "anlauf", 0.0) > 0.02:
            _balken(ziel, (r.x + 6, r.y + 12, 50, 2), ich.anlauf, K.C_TEAL)
        if ich.nachlade_rest > 0 and d.get("nachladen"):
            fertig = 1.0 - ich.nachlade_rest / d["nachladen"]
            _text(ziel, "NACHLADEN", r.x + 6, r.y + 20, K.C_MUTED)
            _balken(ziel, (r.x + 66, r.y + 21, r.width - 72, 5), fertig,
                    K.C_AMBER)
            return
        if not d.get("magazin"):
            _text(ziel, "--", r.right - 6, r.y + 15, K.C_MUTED, 2, "rechts")
            return
        munition = ich.magazin.get(name, 0)
        farbe = K.C_CREAM
        if not munition:
            # Ein leeres Magazin blinkt. Rot allein reicht nicht: rot ist
            # auch die Panzerung, wenn es eng wird.
            farbe = K.C_RED if (g.welt.zeit * 4.0) % 1.0 < 0.6 else (90, 26, 20)
        if g.knapp:
            vorrat = ich.vorrat.get(name, 0)
            text = "/ %d" % vorrat
            _text(ziel, text, r.right - 6, r.y + 22,
                  K.C_RED if not vorrat else K.C_MUTED, 1, "rechts")
            rechts = r.right - 10 - SCHRIFT.breite(text, 1)
            if not vorrat and not munition:
                _text(ziel, "KEIN VORRAT", r.x + 6, r.y + 22, K.C_RED)
        else:
            rechts = r.right - 6
        _text(ziel, "%d" % munition, rechts, r.y + 15, farbe, 2, "rechts")

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
        n = len(ich.waffen)
        gross = self.hotbar_gross(n)
        bw, bh, luecke = self._hotbar_mass(n)
        rahmen_ganz = self.hotbar_rechteck(n)
        hx, hy = rahmen_ganz.x, rahmen_ganz.y
        titel = self._hotbar_titel(ich)
        if titel:
            _text(ziel, titel, W // 2, hy - 10, K.C_MUTED_DK, 1, "mitte")
        for i, name in enumerate(ich.waffen):
            aktiv = (i == ich.waffe)
            r = pygame.Rect(hx + i * (bw + luecke), hy - (2 if aktiv else 0),
                            bw, bh)
            wd = K.WAFFEN[name]
            leer = bool(wd.get("magazin")) and not ich.magazin.get(name, 0) \
                and (not g.knapp or not ich.vorrat.get(name, 0))
            rahmen = (K.C_RED if leer and aktiv else
                      K.C_AMBER if aktiv else K.C_MUTED_DK)
            ui.kasten(ziel, r, rahmen, (34, 10, 8, 230) if leer else KASTEN, 3)
            sym = g.renderer.bilder.bild("waffe_" + name)
            ziel.blit(sym, (r.centerx - sym.get_width() // 2,
                            r.centery - sym.get_height() // 2))
            SCHRIFT.zeichnen(ziel, "%d" % (i + 1), r.x + 3, r.y + 2,
                             K.C_AMBER if aktiv else K.C_MUTED_DK, 1)
            if g.knapp and wd.get("magazin"):
                vorrat = ich.vorrat.get(name, 0) + ich.magazin.get(name, 0)
                _text(ziel, "%d" % vorrat, r.centerx, r.bottom + 2,
                      K.C_RED if not vorrat else
                      (K.C_AMBER if aktiv else K.C_MUTED), 1, "mitte")

    @staticmethod
    def hotbar_gross(anzahl: int) -> bool:
        """Loadout-Modus: so wenige Plaetze, dass sie gross sein duerfen."""
        return anzahl <= 4

    def _hotbar_mass(self, anzahl: int):
        return (52, 22, 4) if self.hotbar_gross(anzahl) else (30, 20, 2)

    def hotbar_rechteck(self, anzahl: int) -> pygame.Rect:
        """Wo die Hotbar steht, ohne das Anheben des gewaehlten Platzes."""
        bw, bh, luecke = self._hotbar_mass(anzahl)
        gesamt = anzahl * bw + (anzahl - 1) * luecke
        y = HOTBAR_Y + (0 if self.hotbar_gross(anzahl) else 2)
        return pygame.Rect((W - gesamt) // 2, y, gesamt, bh)

    def _hotbar_titel(self, ich) -> str:
        """Was ueber der Hotbar steht: welches Loadout, oder der Werfer."""
        g = self.g
        if getattr(ich, "rpg", False):
            return "RAKETENWERFER - EIN SCHUSS"
        if g.loadout_regel == "gleich":
            lo = g._fest_loadout() if g.ist_gastgeber else None
            return ("FUER ALLE: %s" % lo["name"].upper() if lo
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
        r = pygame.Rect(W // 2 - 90, H - 48, 180, 36)
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

    def _gefallen(self, ziel, ich) -> None:
        g = self.g
        _text(ziel, "GEFALLEN", W // 2, H // 2 - 10, K.C_RED, 2, "mitte")
        if g.regeln["runden"]:
            _text(ziel, "RAUS BIS ZUR NAECHSTEN RUNDE", W // 2, H // 2 + 8,
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
