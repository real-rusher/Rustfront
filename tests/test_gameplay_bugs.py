"""
DUSTFRONT - Exklusive Gameplay-Bug-Testsuite
============================================

Prueft gezielt Spielmechaniken, Physik, Kampf, Statuseffekte,
Stuerze, Aufzuege und Randfaelle auf potentielle Gameplay-Bugs.
"""

from __future__ import annotations

import math
import os
import sys
import unittest
from pathlib import Path

# Pygame im Headless-Modus
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pygame

pygame.init()
pygame.display.set_mode((640, 360))

from dustfront import config as K
from dustfront import entities, world


class TestGameplayBugs(unittest.TestCase):

    def setUp(self):
        self.welt = world.testkarte()

    # ----------------------------------------------------------------------
    # 1. Heilung & Statuseffekte
    # ----------------------------------------------------------------------
    def test_01_heilung_nach_tot_oder_am_boden(self):
        """Prueft, ob verzögerte Heilung (heilt_rest) nach Tod oder am_boden Gesundheit hinzufuegt."""
        sp = entities.Spieler((100, 100), ebene=0)
        self.welt.dazu(sp)
        sp.leben = 10.0
        sp.heilen() # Startet 0.8s Verzögerung
        self.assertGreater(sp.heilt_rest, 0)

        # Spieler stirbt vor Ablauf der 0.8s
        sp.leben = 0.0
        sp.sterben()
        self.assertFalse(sp.lebt)

        # Zeit verstreichen lassen (0.9s)
        sp.schritt(0.9)

        # BEFUND: sp.leben sollte nicht wieder steigen, wenn er tot ist!
        self.assertEqual(sp.leben, 0.0, "Toter Spieler hat durch verzögerte Heilung wieder Leben erhalten!")

    def test_02_waffenwechsel_bricht_heilung_nicht_ab(self):
        """Prueft, ob ein Waffenwechsel die angefangene Heilung abricht oder weiterlaufen laesst."""
        sp = entities.Spieler((100, 100), ebene=0)
        self.welt.dazu(sp)
        sp.leben = 50.0
        sp.heilen()
        self.assertGreater(sp.heilt_rest, 0)

        # Waffenwechsel durchfuehren
        sp.waffe_waehlen(1)

        # Pruefen, ob heilt_rest abgebrochen wurde
        self.assertEqual(sp.heilt_rest, 0.0, "Waffenwechsel sollte angefangene Heilung abbrechen!")

    # ----------------------------------------------------------------------
    # 2. Physik & Bewegung (Dash, Sturz, Aufzug)
    # ----------------------------------------------------------------------
    def test_03_dash_waehrend_sturz(self):
        """Prueft das Verhalten, wenn ein Spieler waehrend eines Dashs abrutscht und stuerzt."""
        sp = entities.Spieler((100, 100), ebene=1)
        self.welt.dazu(sp)
        sp.dashen()
        self.assertGreater(sp.dash_rest, 0)

        # Spieler stuerzt ins Loch
        sp.stuerzen()
        self.assertGreater(sp.sturz_rest, 0)

        # In der Luft schritt() ausfuehren
        sp.schritt(0.05)
        # BEFUND: Im Sturz sollte der normale Sturz-Luftsteuerungstakt gelten, nicht das volle Dash-Tempo
        self.assertLessEqual(sp.tempo.length(), K.SPIELER["tempo"] * K.STURZ["luftsteuerung"] + 10,
                             "Dash-Tempo uebersteuert die Sturz-Luftsteuerung!")

    def test_04_aufzug_ohne_ausgang(self):
        """Prueft, wie der Aufzug reagiert, wenn auf der Zielebene alle Nachbarkacheln Wände sind."""
        w = world.testkarte()
        sp = entities.Spieler((100, 100), ebene=0)
        w.dazu(sp)

        # Kacheln um das Ziel auf Ebene 1 künstlich sperren
        e1 = w.ebene(1)
        tx, ty = int(100 // K.TILE), int(100 // K.TILE)
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                e1.setzen(tx + dx, ty + dy, K.WAND)

        # Aufzug versuchen
        erfolg = w.ebene_wechseln(sp, 1, loch_fest=True)
        # Soll nicht wechseln, wenn kein freier Platz existiert
        self.assertFalse(erfolg, "Ebenenwechsel im Aufzug ohne freien Ausgang durfte nicht gelingen!")
        self.assertEqual(sp.ebene, 0)

    # ----------------------------------------------------------------------
    # 3. Projektile & Schaden
    # ----------------------------------------------------------------------
    def test_05_geschoss_einschlag_null_vektor(self):
        """Prueft Geschoss mit Nullvektor-Tempo auf Absturz bei `normalize()`."""
        daten = {"tempo": 0.0, "schaden": 10.0, "reichweite": 100.0, "geschosse": 1}
        g = entities.Geschoss((100, 100), 0.0, daten, ebene=0)
        self.welt.dazu(g)
        sp = entities.Spieler((100, 100), ebene=0)
        self.welt.dazu(sp)

        # Einschlag ausloesen - darf nicht mit ValueError: Cannot normalize... abstuerzen
        try:
            g.einschlag(sp)
        except ValueError as err:
            self.fail(f"Geschoss.einschlag hat Absturz verursacht: {err}")

    def test_06_rakete_ausserhalb_karte_ebenenwechsel(self):
        """Prueft, ob Raketen ausserhalb der Kartengrenzen faelscherweise die Ebene wechseln."""
        sp = entities.Spieler((100, 100), ebene=0)
        d = K.WAFFEN["rakete"]
        rak = entities.Rakete((-50, -50), 0.0, d, ebene=1, von=sp, ziel=sp)
        self.welt.dazu(rak)

        # Ebenenwechsel ausfuehren ausserhalb der Karte
        rak._ebene_wechseln()
        self.assertEqual(rak.ebene, 1, "Rakete ausserhalb der Kartengrenzen darf nicht stuerzen!")

    # ----------------------------------------------------------------------
    # 4. Kartenränder & Lochabfragen
    # ----------------------------------------------------------------------
    def test_07_kartenrand_loch_erkennung(self):
        """Prueft, ob Koordinaten ausserhalb des Kachelgitters fälschlicherweise als Loch (LEER) erkannt werden."""
        e = self.welt.ebene(0)
        # Position -1, -1 ist außerhalb des Gitters
        self.assertFalse(e.loch(-1, -1), "Position außerhalb der Karte darf nicht als Sturzloch gewertet werden!")

    def test_08_brandflaeche_unterschiedliche_ebene_schaden(self):
        """Prueft, ob Brandflaechen versehentlich Schaden auf Spieler auf anderen Ebenen machen."""
        sp = entities.Spieler((100, 100), ebene=1)
        self.welt.dazu(sp)
        sp.leben = 100.0

        # Brandflaeche auf Ebene 0 direkt unter dem Spieler
        bf = entities.Brandflaeche((100, 100), ebene=0, radius=50, dauer=5.0)
        self.welt.feuer.append(bf)

        # Schritt ausfuehren
        bf.schritt(1.0, self.welt)
        self.assertEqual(sp.leben, 100.0, "Brandfläche auf Ebene 0 darf keinen Schaden auf Ebene 1 machen!")


if __name__ == "__main__":
    unittest.main()
