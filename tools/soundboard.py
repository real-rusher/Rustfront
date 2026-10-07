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
        # `Klaenge` erwartet den Asset-Ordner selbst und haengt daran `sfx`.
        # Der Projektordner liess die Suche irrtuemlich bei `<projekt>/sfx`
        # beginnen und fuellte das Soundboard nur mit Platzhaltern.
        self.klaenge = Klaenge(ROOT / K.ASSETS["ordner"])
        if not self.klaenge.ok:
            raise RuntimeError("Kein Audioausgabegeraet verfuegbar.")
        self.klaenge.gesamt = 1.0
        self.klaenge.effekte = 1.0
        for name in K.KLANG_NAMEN:
            self.klaenge.klang(name)
        self.knopfe = []
        self.gehalten = None
        self.naechster_schuss = 0
        self.laufzeit = 0.0
        self.modus = "dauer"
        self.salve_rest = 0
        self.salve_takt = 0.032
        self.salve_naechster = 0
        dateien = len(self.klaenge.aus_datei)
        self.melden = "%d von %d Klaengen aus Audiodateien; Klick spielt, Halten feuert automatisch." % (
            dateien, len(K.KLANG_NAMEN))

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
            quelle = "DATEI" if name in self.klaenge.aus_datei else "CODE"
            self._knopf((x, y, breite, KNOPF_H), "%s  [%s]" % (name, quelle),
                        ("einmal", name), "Einzelklang")
        y = 56 + ((len(K.KLANG_NAMEN) + 3) // 4) * (KNOPF_H + ABSTAND) + 8
        self._knopf((RAND, y, 180, KNOPF_H), "Sturmgewehr",
                    ("halten", "sturm"), "Gedrueckt halten")
        y += KNOPF_H + ABSTAND
        for i, name in enumerate(("rundenstart", "won_match", "lost_match")):
            x = RAND + i * (breite + ABSTAND)
            titel = {"rundenstart": "Rundenstart", "won_match": "Sieg",
                     "lost_match": "Niederlage"}[name]
            self._knopf((x, y, breite, KNOPF_H), titel, ("einmal", name),
                        "Match-Ereignis")

    def _feuern(self, art):
        jetzt = pygame.time.get_ticks()
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
                                quelle = ("Audiodatei" if wert in self.klaenge.aus_datei
                                          else "Code-Platzhalter")
                                self.melden = "%s: %s" % (quelle, wert)
                            else:
                                self.gehalten = wert
                                self.laufzeit = 0.0
                                self.naechster_schuss = 0
                                self._feuern(wert)
                            break
                if ereignis.type == pygame.MOUSEBUTTONUP and ereignis.button == 1:
                    self.gehalten = None
                    self.laufzeit = 0.0
            if self.gehalten:
                self._feuern(self.gehalten)
            jetzt = pygame.time.get_ticks()
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
