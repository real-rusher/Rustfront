"""Loser Klangpruefer fuer DUSTFRONT: `python tools/soundboard.py`."""

from __future__ import annotations

import sys
from pathlib import Path

import pygame

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dustfront import config as K
from dustfront.audio import Klaenge

BREITE, HOEHE = 900, 680
RAND, KNOPF_H, ABSTAND = 14, 38, 7
HINTERGRUND = (22, 25, 29)
KNOPF = (54, 61, 68)
AKTIV = (105, 133, 148)
TEXT = (232, 235, 232)
GEDAEMMT = (150, 158, 162)


class Klangpruefer:
    """Spielt einzelne Ereignisse oder haelt automatische Waffen im Takt."""

    def __init__(self):
        pygame.init()
        pygame.display.set_caption("DUSTFRONT – Klangpruefer")
        self.flaeche = pygame.display.set_mode((BREITE, HOEHE), pygame.RESIZABLE)
        self.uhr = pygame.time.Clock()
        self.schriften = pygame.font.Font(None, 23), pygame.font.Font(None, 18)
        self.klaenge = Klaenge(ROOT)
        if not self.klaenge.ok:
            raise RuntimeError("Kein Audioausgabegeraet verfuegbar.")
        self.klaenge.gesamt = 1.0
        self.klaenge.effekte = 1.0
        self.knopfe = []
        self.gehalten = None
        self.naechster_schuss = 0
        self.laufzeit = 0.0
        self.modus = "dauer"
        self.salve_rest = 0
        self.salve_takt = 0.032
        self.salve_naechster = 0
        self.melden = "Klick: einmal abspielen. Gedrueckt halten: automatische Waffe."

    def _knopf(self, rechteck, titel, aktion, untertitel=""):
        self.knopfe.append((pygame.Rect(rechteck), titel, aktion, untertitel))

    def _anordnen(self):
        self.knopfe.clear()
        y = 56
        breite = (self.flaeche.get_width() - RAND * 2 - ABSTAND * 3) // 4
        for i, name in enumerate(K.KLANG_NAMEN):
            x = RAND + (i % 4) * (breite + ABSTAND)
            zeile = i // 4
            y = 56 + zeile * (KNOPF_H + ABSTAND)
            self._knopf((x, y, breite, KNOPF_H), name,
                        ("einmal", name), "Einzelklang")
        y = 56 + ((len(K.KLANG_NAMEN) + 3) // 4) * (KNOPF_H + ABSTAND) + 8
        self._knopf((RAND, y, 230, KNOPF_H), "MG – Dauerfeuer",
                    ("halten", "lmg_dauer"), "Gedrueckt halten")
        self._knopf((RAND + 237, y, 230, KNOPF_H), "MG – Salve",
                    ("halten", "lmg_salve"), "Halten fuer Spieltakt")
        self._knopf((RAND + 474, y, 180, KNOPF_H), "Sturmgewehr",
                    ("halten", "sturm"), "Gedrueckt halten")

    def _feuern(self, art):
        jetzt = pygame.time.get_ticks()
        if art == "lmg_salve":
            if jetzt < self.naechster_schuss:
                return
            daten = K.WAFFEN["lmg"]["modus_daten"]["salve"]
            schuesse = int(K.WAFFEN["lmg"]["modus_daten"].get("salve", {}).get("salve", 3))
            self.klaenge.spielen("schuss_lmg", 1.0)
            self.salve_rest = max(0, schuesse - 1)
            self.salve_takt = daten.get("salve_takt", 0.032)
            self.salve_naechster = jetzt + int(self.salve_takt * 1000)
            self.melden = "MG-Salve: %d Schuesse; Halten spielt alle %.1f s eine Salve" % (
                schuesse, daten["takt"])
            self.naechster_schuss = jetzt + int(daten["takt"] * 1000)
            return
        if art == "lmg_dauer":
            d = K.WAFFEN["lmg"]["modus_daten"]["dauer"]
            self.laufzeit += self.uhr.get_time() / 1000.0
            takt = d["anlauf_takt"] + (d["takt"] - d["anlauf_takt"]) * min(
                1.0, self.laufzeit / d["anlauf"])
            name = "schuss_lmg"
        else:
            d = K.WAFFEN["sturm"]
            takt, name = d["takt"], "schuss_sturm"
        if jetzt >= self.naechster_schuss:
            self.klaenge.spielen(name, 1.0)
            self.naechster_schuss = jetzt + max(1, int(takt * 1000))

    def laufen(self):
        while True:
            self._anordnen()
            for ereignis in pygame.event.get():
                if ereignis.type == pygame.QUIT:
                    return
                if ereignis.type == pygame.MOUSEBUTTONDOWN and ereignis.button == 1:
                    for r, titel, aktion, _ in self.knopfe:
                        if r.collidepoint(ereignis.pos):
                            art, wert = aktion
                            if art == "einmal":
                                self.klaenge.spielen(wert, 1.0)
                                self.melden = "Abgespielt: " + wert
                            else:
                                self.gehalten = wert
                                self.laufzeit = 0.0
                                if wert != "lmg_salve":
                                    self.naechster_schuss = 0
                                self._feuern(wert)
                            break
                if ereignis.type == pygame.MOUSEBUTTONUP and ereignis.button == 1:
                    self.gehalten = None
                    self.laufzeit = 0.0
            if self.gehalten:
                self._feuern(self.gehalten)
            jetzt = pygame.time.get_ticks()
            if self.salve_rest and jetzt >= self.salve_naechster:
                self.klaenge.spielen("schuss_lmg", 1.0)
                self.salve_rest -= 1
                self.salve_naechster += max(1, int(self.salve_takt * 1000))
            self.flaeche.fill(HINTERGRUND)
            kopf, klein = self.schriften
            self.flaeche.blit(kopf.render("DUSTFRONT  /  KLANGPRUEFER", True, TEXT), (RAND, 12))
            self.flaeche.blit(klein.render(self.melden, True, GEDAEMMT), (RAND, 35))
            for r, titel, aktion, untertitel in self.knopfe:
                farbe = AKTIV if aktion[1] == self.gehalten else KNOPF
                pygame.draw.rect(self.flaeche, farbe, r, border_radius=3)
                text = klein.render(titel, True, TEXT)
                self.flaeche.blit(text, (r.x + 8, r.y + 4))
            pygame.display.flip()
            self.uhr.tick(60)


if __name__ == "__main__":
    try:
        Klangpruefer().laufen()
    except (pygame.error, RuntimeError) as fehler:
        print("Klangpruefer: %s" % fehler, file=sys.stderr)
        sys.exit(1)
    finally:
        pygame.quit()
