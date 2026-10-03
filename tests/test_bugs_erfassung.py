"""
DUSTFRONT - Gezielter Fehlersuch-Teststand
==========================================

Sucht systematisch nach Fehlern, Randfaellen, Ausnahmen und unlogischem Verhalten
in Konfiguration, Einheiten, Netzprotokoll, Menues, Konten und Einstellungen.
"""

from __future__ import annotations

import json
import os
import socket
import sys
import tempfile
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
from dustfront import einstellungen as E
from dustfront import konto, ablage, regeln as R, ui, netz, lobby, world, entities
from dustfront.font import SCHRIFT
import rustfront_menu


class TestBugsErfassung(unittest.TestCase):

    # ----------------------------------------------------------------------
    # 1. Konfiguration & Datenintegritaet
    # ----------------------------------------------------------------------
    def test_01_waffen_konfiguration_vollstaendig(self):
        """Prueft, ob alle Waffen notwendige Felder besitzen und gueltige Werte haben."""
        erforderlich = ["name", "art", "schaden", "takt"]
        for w_id, w in K.WAFFEN.items():
            for f in erforderlich:
                self.assertIn(f, w, f"Waffe '{w_id}' fehlt Feld '{f}'")
            self.assertGreaterEqual(w["schaden"], 0, f"Waffe '{w_id}' hat ungueltigen Schaden")
            self.assertGreater(w["takt"], 0, f"Waffe '{w_id}' hat ungueltigen Takt")
            if w["art"] == "schuss":
                self.assertIn("magazin", w, f"Schusswaffe '{w_id}' hat kein Magazin-Feld")

    def test_02_hotbar_deckt_waffen_ab(self):
        """Prueft, ob alle Hotbar-Eintraege in K.WAFFEN existieren."""
        for w_id in K.HOTBAR:
            self.assertIn(w_id, K.WAFFEN, f"Hotbar-Eintrag '{w_id}' existiert nicht in K.WAFFEN")

    def test_03_bild_mass_vollstaendig(self):
        """Prueft, ob Bildgroessen in K.BILD_MASS gueltige Tuples (w, h) sind."""
        for name, mass in K.BILD_MASS.items():
            self.assertEqual(len(mass), 2, f"BILD_MASS für '{name}' ist kein 2er-Tuple")
            self.assertGreater(mass[0], 0, f"Breite von '{name}' ungueltig")
            self.assertGreater(mass[1], 0, f"Hoehe von '{name}' ungueltig")

    # ----------------------------------------------------------------------
    # 2. Einstellungen & Tastenbelegung (Datei-Fehlertoleranz)
    # ----------------------------------------------------------------------
    def test_04_einstellungen_kaputte_json_toleranz(self):
        """Prueft, wie Einstellungen mit kaputten JSON-Dateien umgeht."""
        with tempfile.TemporaryDirectory() as tmpdir:
            orig = E.pfade.datei
            p = Path(tmpdir) / "einstellungen.json"
            p.write_text("{ kaputtes json ::: ", encoding="utf-8")
            E.pfade.datei = lambda n: p if n == "einstellungen.json" else None
            try:
                opt = E.Einstellungen()
                # Sollte nicht abstuerzen und Vorgaben laden
                self.assertEqual(opt["fenstermodus"], E.VORGABE["fenstermodus"])
            finally:
                E.pfade.datei = orig

    def test_05_tasten_fest_geschuetzt(self):
        """Prueft, ob fest verdrahtete Tasten (z.B. Pause) verstellt werden koennen."""
        opt = E.Einstellungen()
        for fest in E.FEST:
            verdraengt = opt.belegen(fest, pygame.K_x)
            self.assertIsNone(verdraengt, f"Feste Aktion '{fest}' durfte nicht belegt werden!")

    # ----------------------------------------------------------------------
    # 3. Spielregeln & Rundenplanung
    # ----------------------------------------------------------------------
    def test_06_regeln_saeubern_extremwerte(self):
        """Prueft R.saeubern auf Extremwerte, unbekannte Modus-Schluessel und Typfehler."""
        eingabe = {
            "modus": "UNBEKANNT_MODUS_XYZ",
            "ende_wert": -999,
            "karte": "<script>alert(1)</script>",
            "knapp": "vielleicht",
        }
        bereinigt = R.saeubern(eingabe)
        self.assertIn(bereinigt["modus"], K.MODI, "Ungueltiger Modus muss auf Vorgabe fallen")
        self.assertGreaterEqual(bereinigt["ende_wert"], 1)
        self.assertIsInstance(bereinigt["knapp"], bool)

    def test_07_rundenplan_hoechstgrenze(self):
        """Prueft, ob die Lobby-Rundenplanung die Höchstgrenze an Runden einhaelt."""
        class MockSender:
            def an_alle(self, msg): pass

        class MockGefecht(lobby.LobbyTeil):
            def __init__(self):
                self.gastgeber = MockSender()
                self._lobby_anlegen({})
            def _umfeld(self):
                return {}
            @property
            def ist_gastgeber(self):
                return True

        m = MockGefecht()
        max_r = K.LOBBY["plan_hoechstens"]
        for _ in range(max_r + 10):
            m.plan_dazu(0)
        self.assertLessEqual(len(m.plan), max_r, "Rundenplan ueberschreitet Höchstgrenze!")

    # ----------------------------------------------------------------------
    # 4. Konto & Namensbereinigung
    # ----------------------------------------------------------------------
    def test_08_namenssauberung_extremfaelle(self):
        """Prueft Namenssaeuberung mit Leerzeichen und Überlaenge sowie Namenspruefung."""
        self.assertEqual(ablage.name_saeubern(""), "")
        self.assertEqual(ablage.name_saeubern("   "), "")
        self.assertNotEqual(ablage.name_pruefen(""), "") # Grund angegeben
        self.assertEqual(ablage.name_saeubern("A" * 300), ("A" * 300)[:ablage.NAMENSLAENGE])

    def test_09_journal_abgleich_doppelung(self):
        """Prueft, ob Runden im Journal nicht mehrfach als offen verbleiben."""
        with tempfile.TemporaryDirectory() as tmpdir:
            j = konto.Journal(Path(tmpdir))
            runden_id = "test-partie-123"
            j.dazu({"partie": runden_id, "modus": "pvp", "werte": {"abschuesse": 1}})
            self.assertEqual(len(j.offen()), 1)
            j.abhaken([runden_id])
            self.assertEqual(len(j.offen()), 0)
            j.abhaken([runden_id]) # Zweites Abhaken soll sanft ignoriert werden
            self.assertEqual(len(j.offen()), 0)

    # ----------------------------------------------------------------------
    # 5. UI & Schriftberechnungen
    # ----------------------------------------------------------------------
    def test_10_schrift_kuerzen_extremwerte(self):
        """Prueft `ui.kuerzen` mit negativer/null Breite und sehr langen Texten."""
        self.assertEqual(ui.kuerzen("Hallo", 0), "")
        self.assertEqual(ui.kuerzen("Hallo", -10), "")
        self.assertEqual(ui.kuerzen("", 100), "")
        lang = "A" * 500
        gekuerzt = ui.kuerzen(lang, 50)
        self.assertLess(len(gekuerzt), len(lang))
        self.assertTrue(gekuerzt.endswith(">"))

    def test_11_regler_aus_x_grenzen(self):
        """Prueft Regler-Eingaben ausserhalb der normalen x-Koordinaten."""
        r = ui.Regler((10, 10, 200, 20), "Lautstärke", "vol", 50)
        self.assertEqual(r.aus_x(-9999), 0)
        self.assertEqual(r.aus_x(9999), 100)

    # ----------------------------------------------------------------------
    # 6. Netzprotokoll & JSON-Sicherheit
    # ----------------------------------------------------------------------
    def test_12_netz_zeilen_parser_schutzklausel(self):
        """Prueft, wie das Netzprotokoll auf fehlerhaftes JSON oder riesige Zeilen reagiert."""
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.bind(("127.0.0.1", 0))
        server.listen(1)
        port = server.getsockname()[1]
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.connect(("127.0.0.1", port))
        remote, _ = server.accept()
        try:
            leitung = netz.Leitung(remote)
            client.sendall(b'{"t": "ping"}\n{kaputt json\n')
            msg_list = leitung.holen()
            self.assertEqual(len(msg_list), 1)
            self.assertEqual(msg_list[0], {"t": "ping"})
        finally:
            client.close()
            remote.close()
            server.close()


    # ----------------------------------------------------------------------
    # 7. Weitere Spiel- und Einheiten-Randfaelle
    # ----------------------------------------------------------------------
    def test_13_loadout_saeubern_duplikate(self):
        """Prueft, ob doppelte Waffen in Loadouts automatisch auf gefuellte Saetze korrigiert werden."""
        roh = {"name": "Test", "waffen": ["sturm", "sturm"], "wuerfe": ["granate"]}
        sauber = konto.loadout_saeubern(roh)
        self.assertEqual(len(sauber["waffen"]), K.LOADOUT["waffen"])
        self.assertEqual(len(set(sauber["waffen"])), K.LOADOUT["waffen"], "Waffen im Loadout muessen eindeutig sein!")

    def test_14_regeln_verstellen_grenzen(self):
        """Prueft R.verstellen am oberen und unteren Ende der Stufen."""
        d = R.vorgabe(modus="pvp", ende_art="zeit", ende_wert=60)
        # Zurueckschalten darf nicht unter den Minimalwert fallen
        R.verstellen(d, "ende_wert", -10)
        self.assertGreaterEqual(d["ende_wert"], 60)

    def test_15_textfeld_tippen_steuerzeichen(self):
        """Prueft `ui.Textfeld` gegen nicht-druckbare Steuerzeichen."""
        tf = ui.Textfeld((0, 0, 100, 20), "NAME", "name", laenge=10)
        class MockEv:
            key = pygame.K_a
            unicode = "\x00\x07\x1b"
        consumed = tf.tippen(MockEv())
        self.assertFalse(consumed)
        self.assertEqual(tf.wert, "")


if __name__ == "__main__":
    unittest.main()
