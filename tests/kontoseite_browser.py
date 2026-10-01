# -*- coding: utf-8 -*-
"""Die Kontoseite im echten Browser: der Reiter KOSMETIK.

Was test_konto.py nicht kann - es hat keinen Browser. Hier laeuft die
erzeugte KONTO.html in Chromium (Playwright), mit einem vorgetaeuschten
Server: jede Anfrage an /auth/v1 und /rest/v1 beantwortet dieser Test
selbst. Nichts geht ins Netz, nichts landet auf dem echten Server.

Geprueft wird vor allem das, worauf es ankommt:

* Die Grenze, die die Seite fuer ihre Vorschau rechnet, ist **dieselbe**
  wie im Spiel - Probe fuer Probe, nicht ungefaehr.
* Was die Seite hochlaedt, nimmt das Spiel an (spielerkosmetik.aus_konto),
  und es klingt im Spiel genau wie in der Vorschau.
* Zu kurze Toene gehen gar nicht erst, und der Ausschnitt bleibt in den
  Grenzen, egal wie man zieht.

    python tests/kontoseite_browser.py

Ohne Playwright wird er uebersprungen und sagt das.
"""
import base64
import io
import json
import math
import os
import struct
import sys
import tempfile
import wave
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
WURZEL = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WURZEL))

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print("Playwright fehlt - uebersprungen (pip install playwright)")
    sys.exit(0)

import pygame
import werkzeug_kontoseite
from dustfront import config as K
from dustfront import spielerkosmetik as SK

pygame.init()
pygame.display.set_mode((64, 64))

fails = []


def pruef(t, ok, zusatz=""):
    print(("  ok  " if ok else "FAIL  ") + t + (("   " + str(zusatz)) if zusatz else ""))
    if not ok:
        fails.append(t)


# ── Testdateien ─────────────────────────────────────────────────────────
def wav_bauen(dauer, rate=44100, spuren=2, hz=220.0, laut=0.6):
    n = int(dauer * rate)
    puffer = io.BytesIO()
    with wave.open(puffer, "wb") as w:
        w.setnchannels(spuren)
        w.setsampwidth(2)
        w.setframerate(rate)
        roh = bytearray()
        for i in range(n):
            v = int(32000 * laut * math.sin(2 * math.pi * hz * i / rate))
            roh += struct.pack("<h", v) * spuren
        w.writeframes(bytes(roh))
    return puffer.getvalue()


def mp3_stille(dauer):
    """Eine echte MP3 aus stillen Rahmen. Ohne Kodierer im Haus: ein
    MPEG-1-Layer-III-Rahmen mit lauter Nullen in den Seiteninformationen
    ist gueltige Stille, 1152 Proben lang."""
    kopf = bytes([0xFF, 0xFB, 0x90, 0xC0])      # 128 kbit/s, 44,1 kHz, mono
    rahmen = kopf + bytes(417 - 4)
    return rahmen * int(math.ceil(dauer * 44100 / 1152.0))


def png_bauen(b, h):
    s = pygame.Surface((b, h), pygame.SRCALPHA)
    for y in range(h):
        for x in range(b):
            s.set_at((x, y), (x * 255 // b, y * 255 // h, 140, 255))
    puffer = io.BytesIO()
    pygame.image.save(s, puffer, "x.png")
    return puffer.getvalue()


ordner = Path(tempfile.mkdtemp(prefix="dustfront_kontoseite_"))
seite = werkzeug_kontoseite.schreiben(ordner / "KONTO.html")
dateien = {
    "lang.wav": wav_bauen(2.5),
    "kurz.wav": wav_bauen(0.5),
    "still.mp3": mp3_stille(1.6),
    "bild.png": png_bauen(300, 200),
}
for name, inhalt in dateien.items():
    (ordner / name).write_bytes(inhalt)


# ── Der vorgetaeuschte Server ──────────────────────────────────────────
class Server:
    def __init__(self):
        self.kosmetik = None            # die eine Zeile, oder None
        self.tabelle_fehlt = False
        self.geschrieben = []
        self.geloescht = 0
        self.profil = {"name": "TESTER", "fassung": 1, "werte": {}, "loadouts": []}
        self.profil_geschrieben = []
        self.gefechte = []
        self.gefecht_anfragen = 0
        # Der ADMIN (KONTO.md 5.8), so weit nachgebaut, wie die Seite ihn
        # sieht: dieselben Antworten wie die Funktionen in SQL. Ob die
        # Funktionen selbst stimmen, prueft tests/test_admin_sql.py.
        self.admin_wort = "123"
        self.admin_muss = True
        self.admin_sperre = 0          # Sekunden; > 0 heisst gesperrt
        self.admin_frei = 2
        self.rpc = []                  # (name, argumente)
        self.konten = {
            "k-1": {"anmeldename": "erster", "name": "ERSTER", "angelegt": 1700000000,
                    "profil": {"name": "ERSTER", "fassung": 3, "werte": {"bildschirm_ruckeln": 40},
                               "loadouts": []}, "kosmetik": {"ton": "", "bild": ""}},
            "k-2": {"anmeldename": "zweiter", "name": "ZWEITER", "angelegt": 1700000100,
                    "profil": {"name": "ZWEITER", "fassung": 1, "werte": {}, "loadouts": []},
                    "kosmetik": {"ton": "", "bild": ""}},
        }
        self.admin_runden = [
            {"partie": "a1", "konto": "k-1", "gespielt": 2000, "modus": "pvp", "team": -1,
             "gewonnen": True, "werte": {"abschuesse": 6, "runden": 1}, "waffen": {},
             "version": "0.31.0", "ende": "regulaer",
             "opfer": [{"name": "ZWEITER", "konto": "k-2", "anzahl": 6}]},
            {"partie": "a1", "konto": "k-2", "gespielt": 2000, "modus": "pvp", "team": -1,
             "gewonnen": False, "werte": {"abschuesse": 2, "runden": 1}, "waffen": {},
             "version": "0.31.0", "ende": "regulaer",
             "opfer": [{"name": "ERSTER", "konto": "k-1", "anzahl": 2}]},
        ]

    def admin_rpc(self, name, a):
        self.rpc.append((name, a))
        if self.admin_sperre > 0:
            return {"ok": False, "fehler": "GESPERRT", "sekunden": self.admin_sperre}
        if a.get("wort") != self.admin_wort:
            self.admin_frei -= 1
            if self.admin_frei < 0:
                self.admin_sperre = 60
                return {"ok": False, "fehler": "FALSCH", "sekunden": 60, "frei": 0}
            return {"ok": False, "fehler": "FALSCH", "sekunden": 0, "frei": self.admin_frei}
        self.admin_frei = 2
        if name == "admin_anmelden":
            return {"ok": True, "muss_aendern": self.admin_muss}
        if name == "admin_wort_aendern":
            if len(a.get("neu", "")) < 8:
                return {"ok": False, "fehler": "KENNWORT ZU KURZ (MINDESTENS 8)"}
            self.admin_wort, self.admin_muss = a["neu"], False
            return {"ok": True}
        if self.admin_muss:
            return {"ok": False, "fehler": "ERST DAS KENNWORT AENDERN"}
        k = self.konten.get(a.get("konto"))
        if name == "admin_konten":
            return {"ok": True, "konten": [
                {"konto": n, "anmeldename": v["anmeldename"], "name": v["profil"]["name"],
                 "fassung": v["profil"]["fassung"], "angelegt": v["angelegt"],
                 "runden": sum(1 for z in self.admin_runden if z["konto"] == n)}
                for n, v in sorted(self.konten.items())]}
        if name == "admin_gefechte":
            zeilen = [z for z in self.admin_runden
                      if a.get("konto") in (None, z["konto"]) and z["konto"] in self.konten]
            ab = int(a.get("ab") or 0)
            return {"ok": True, "gefechte": zeilen[ab:ab + int(a.get("anzahl") or 1000)]}
        if k is None:
            return {"ok": False, "fehler": "KONTO NICHT GEFUNDEN"}
        if name == "admin_profil":
            return {"ok": True, "profil": dict(k["profil"])}
        if name == "admin_profil_schreiben":
            if int(a["fassung"]) != k["profil"]["fassung"]:
                return {"ok": False, "fehler": "PROFIL WURDE ZWISCHENDURCH GEAENDERT"}
            k["profil"] = {"name": a["name"] or k["profil"]["name"], "fassung": a["fassung"] + 1,
                           "werte": a["werte"], "loadouts": a["loadouts"]}
            return {"ok": True, "profil": dict(k["profil"])}
        if name == "admin_kosmetik":
            return {"ok": True, **k["kosmetik"]}
        if name == "admin_kosmetik_schreiben":
            k["kosmetik"] = {"ton": a["ton"], "bild": a["bild"]}
            return {"ok": True}
        if name == "admin_name_aendern":
            if a["neu"].lower() == "admin":
                return {"ok": False, "fehler": "NAME VORBEHALTEN"}
            k["anmeldename"] = a["neu"].lower()
            k["profil"]["name"] = a["neu"]
            return {"ok": True, "anmeldename": a["neu"].lower()}
        if name == "admin_kennwort_setzen":
            k["wort"] = a["neu"]
            return {"ok": True}
        if name == "admin_loeschen":
            del self.konten[a["konto"]]
            return {"ok": True}
        return {"ok": False, "fehler": "UNBEKANNT"}

    def antworten(self, route):
        anfrage = route.request
        weg, methode = anfrage.url.split("/", 3)[-1], anfrage.method

        def json_antwort(status, daten):
            route.fulfill(status=status, content_type="application/json",
                          headers={"Access-Control-Allow-Origin": "*"},
                          body=json.dumps(daten))

        if methode == "OPTIONS":
            return route.fulfill(status=204, headers={
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET,POST,PATCH,DELETE,PUT",
                "Access-Control-Allow-Headers": "*"})
        if weg.startswith("rest/v1/rpc/"):
            return json_antwort(200, self.admin_rpc(weg.split("/")[3].split("?")[0],
                                                    json.loads(anfrage.post_data or "{}")))
        if weg.startswith("rest/v1/profil"):
            if methode == "PATCH":
                daten = json.loads(anfrage.post_data or "{}")
                self.profil_geschrieben.append(daten)
                self.profil = dict(self.profil, **daten)
            return json_antwort(200, [self.profil])
        if weg.startswith("rest/v1/gefecht"):
            # Wie Supabase: hoechstens 1000 Zeilen je Antwort, limit und
            # offset aus der Adresse.
            from urllib.parse import urlparse, parse_qs
            q = parse_qs(urlparse(anfrage.url).query)
            grenze = min(1000, int((q.get("limit") or ["1000"])[0]))
            ab = int((q.get("offset") or ["0"])[0])
            self.gefecht_anfragen += 1
            zeilen = sorted(self.gefechte, key=lambda z: -z["gespielt"])
            return json_antwort(200, zeilen[ab:ab + grenze])
        if weg.startswith("rest/v1/kosmetik"):
            if self.tabelle_fehlt:
                return json_antwort(404, {
                    "code": "PGRST205",
                    "message": "Could not find the table 'public.kosmetik' in the schema cache"})
            if methode == "GET":
                return json_antwort(200, [self.kosmetik] if self.kosmetik else [])
            if methode == "POST":
                daten = json.loads(anfrage.post_data or "{}")
                self.geschrieben.append((weg, dict(anfrage.headers), daten))
                self.kosmetik = {"blend_ton": daten.get("blend_ton", ""),
                                 "blend_bild": daten.get("blend_bild", "")}
                return route.fulfill(status=201, headers={"Access-Control-Allow-Origin": "*"})
            if methode == "DELETE":
                self.geloescht += 1
                self.kosmetik = None
                return route.fulfill(status=204, headers={"Access-Control-Allow-Origin": "*"})
        return json_antwort(404, {"message": "unbekannt: " + weg})


server = Server()
SITZUNG = {"marke": "falsche.marke.fuer.den.test", "erneuern": "",
           "kennung": "00000000-0000-4000-8000-000000000001", "name": "TESTER",
           "laeuft_ab": 9e15}


def warten(seite_, ausdruck, sekunden=10.0):
    try:
        seite_.wait_for_function(ausdruck, timeout=int(sekunden * 1000))
        return True
    except Exception:
        return False


def regler_setzen(seite_, name, wert):
    seite_.evaluate("""([name, wert]) => {
        const r = document.querySelector('input[type=range][aria-label="' + name + '"]');
        r.value = wert; r.dispatchEvent(new Event('input'));
    }""", [name, wert])


def datei_waehlen(seite_, tafel, pfad):
    # Der versteckte Dateiknopf in der Tafel TON (erste) oder BILD (zweite).
    seite_.locator(".gitter.g2 > .tafel").nth(tafel).locator("input[type=file]") \
        .set_input_files(str(pfad))


def browser_starten(pw):
    """Chromium von Playwright - oder, passt dessen Fassung nicht zum
    installierten Browser, ein vorhandenes Chromium (PLAYWRIGHT_CHROMIUM,
    sonst die ueblichen Orte)."""
    argumente = ["--autoplay-policy=no-user-gesture-required"]
    try:
        return pw.chromium.launch(args=argumente)
    except Exception as fehler:
        for pfad in (os.environ.get("PLAYWRIGHT_CHROMIUM", ""),
                     "/opt/pw-browsers/chromium", "/usr/bin/chromium",
                     "/usr/bin/chromium-browser", "/usr/bin/google-chrome"):
            if pfad and Path(pfad).exists():
                return pw.chromium.launch(executable_path=pfad, args=argumente)
        raise fehler


with sync_playwright() as pw:
    browser = browser_starten(pw)
    kontext = browser.new_context()
    kontext.add_init_script("localStorage.setItem('dustfront.konto.sitzung', %s);"
                            % json.dumps(json.dumps(SITZUNG)))
    kontext.route("**/rest/v1/**", server.antworten)
    kontext.route("**/auth/v1/**", server.antworten)
    s = kontext.new_page()
    fehler_js = []
    s.on("pageerror", lambda e: fehler_js.append(str(e)))
    s.goto(seite.as_uri())
    s.get_by_role("button", name="KOSMETIK").click()
    pruef("Der Reiter KOSMETIK geht auf",
          warten(s, "Werkstatt.server && Werkstatt.server.geladen"))
    pruef("Ohne gespeicherte Kosmetik: es knallt wie immer",
          "KNALLT WIE IMMER" in s.inner_text("body"))

    # ── Dieselbe Grenze wie im Spiel, Probe fuer Probe ─────────────────
    def js_grenze(proben, rate):
        return s.evaluate("([p, r]) => Array.from(tonAusklingen(Int16Array.from(p), r).proben)",
                          [list(proben), rate])

    import array
    import random
    zufall = random.Random(7)
    faelle = {
        "anschwellend": [int(30000 * (i / 30000.0) * math.sin(i / 7.0)) for i in range(30000)],
        "schlaege": [int((29000 if (i // 2205) % 2 == 0 else 900) * math.sin(i / 3.0))
                     for i in range(44100)],
        "rauschen": [zufall.randint(-32768, 32767) for _ in range(23000)],
        "ungerade Laenge": [int(20000 * math.sin(i / 5.0)) for i in range(22051)],
    }
    for name, proben in faelle.items():
        py = list(SK.ton_ausklingen(array.array("h", proben), 22050))
        js = js_grenze(proben, 22050)
        gleich = py == js
        pruef("Grenze Seite = Grenze Spiel: " + name, gleich,
              "" if gleich else "erste Abweichung bei %d" % next(
                  i for i, (a, b) in enumerate(zip(py, js)) if a != b))

    # ── Ton laden ───────────────────────────────────────────────────────
    datei_waehlen(s, 0, ordner / "kurz.wav")
    pruef("Ein zu kurzer Ton wird abgelehnt",
          warten(s, "document.body.innerText.includes('ZU KURZ')")
          and s.evaluate("Werkstatt.ton === null"))
    datei_waehlen(s, 0, ordner / "lang.wav")
    pruef("Eine WAV wird gelesen und gerechnet",
          warten(s, "Werkstatt.ton && Werkstatt.ton.fertig"))
    pruef("Der Ausschnitt ist die ganze Datei, solange sie kurz genug ist",
          abs(s.evaluate("Werkstatt.ton.ende - Werkstatt.ton.start") - 2.5) < 0.01)

    # Ziehen: das Ende weit nach links - es bleibt bei der Mindestlaenge.
    welle = s.locator("canvas.welle").first
    k = welle.bounding_box()
    s.mouse.move(k["x"] + k["width"] - 2, k["y"] + k["height"] / 2)
    s.mouse.down()
    s.mouse.move(k["x"] + 3, k["y"] + k["height"] / 2, steps=8)
    s.mouse.up()
    laenge = s.evaluate("Werkstatt.ton.ende - Werkstatt.ton.start")
    pruef("Kuerzer als erlaubt laesst sich nicht ziehen",
          abs(laenge - K.SPIELERKOSMETIK["ton_min"]) < 0.01, "%.3f S" % laenge)
    # In der Mitte greifen verschiebt den ganzen Ausschnitt.
    vorher = s.evaluate("Werkstatt.ton.start")
    s.mouse.move(k["x"] + k["width"] * 0.2, k["y"] + k["height"] / 2)
    s.mouse.down()
    s.mouse.move(k["x"] + k["width"] * 0.5, k["y"] + k["height"] / 2, steps=8)
    s.mouse.up()
    nachher = s.evaluate("[Werkstatt.ton.start, Werkstatt.ton.ende - Werkstatt.ton.start]")
    pruef("Dazwischen gegriffen, wandert der ganze Ausschnitt",
          nachher[0] > vorher + 0.5 and abs(nachher[1] - laenge) < 0.01, str(nachher))

    stand = s.evaluate("Werkstatt._rechnen")
    for name, wert in (("BASS", 36), ("LAUTER", 24), ("KNALL", 70), ("PFEIFEN", 40),
                       ("ABKLINGEN", 20)):
        regler_setzen(s, name, wert)
    pruef("Die Regler rechnen den Ton neu",
          warten(s, "Werkstatt._rechnen > %d && Werkstatt.ton.fertig "
                    "&& Werkstatt.ton.bass === 36" % stand))
    s.wait_for_timeout(400)
    spitze = s.evaluate("Math.max(...Werkstatt.ton.roh.map(Math.abs))")
    pruef("Laut gemacht, aber nichts abgeschnitten", 25000 < spitze <= 32767 * 0.981,
          spitze)

    # ── Bild ──────────────────────────────────────────────────────────
    datei_waehlen(s, 1, ordner / "bild.png")
    pruef("Ein Bild wird gelesen - ganz, mit seinen Seiten",
          warten(s, "Werkstatt.bild && Werkstatt.bild.flaeche "
                    "&& Werkstatt.bild.flaeche.width === 300 && Werkstatt.bild.flaeche.height === 200"))
    fuellt = s.evaluate("lageVon(Werkstatt.bild)")
    pruef("Und fuellt erst einmal den ganzen Schirm",
          fuellt["x"] == 0.5 and fuellt["y"] == 0.5
          and fuellt["h"] * 360 * 300 / 200.0 >= 639.5 and fuellt["h"] >= 1.0, str(fuellt))
    vorschau = s.locator("canvas.spielbild")
    vorschau.scroll_into_view_if_needed()       # die Maus erreicht nur, was zu sehen ist
    vk = vorschau.bounding_box()
    s.mouse.move(vk["x"] + vk["width"] / 2, vk["y"] + vk["height"] / 2)
    s.mouse.down()
    s.mouse.move(vk["x"] + vk["width"] * 0.75, vk["y"] + vk["height"] * 0.65, steps=6)
    s.mouse.up()
    s.mouse.move(vk["x"] + vk["width"] / 2, vk["y"] + vk["height"] / 2)
    for _ in range(6):
        s.mouse.wheel(0, 120)             # kleiner
    lage = s.evaluate("lageVon(Werkstatt.bild)")
    pruef("Ziehen verschiebt es auf dem Weiss",
          abs(lage["x"] - 0.75) < 0.03 and abs(lage["y"] - 0.65) < 0.03, str(lage))
    pruef("Das Mausrad macht es kleiner", lage["h"] < fuellt["h"] * 0.7, str(lage))
    regler_setzen(s, "GROESSE", 50)
    lage = s.evaluate("lageVon(Werkstatt.bild)")
    pruef("Der Regler GROESSE auch", abs(lage["h"] - 0.5) < 0.001, str(lage))
    regler_setzen(s, "FRITTIERT", 60)
    regler_setzen(s, "PIXEL", 4)
    s.wait_for_timeout(200)
    pruef("Die Filter wirken", s.evaluate("Werkstatt.bild.frittiert === 60 "
                                          "&& Werkstatt.bild.pixel === 4"))
    s.screenshot(path=str(ordner / "kosmetik.png"), full_page=True)

    # ── Speichern ─────────────────────────────────────────────────────
    s.get_by_role("button", name="SPEICHERN").click()
    pruef("Gespeichert", warten(s, "document.body.innerText.includes('GESPEICHERT - IM SPIEL')"),
          s.inner_text(".meldung") if s.locator(".meldung").count() else "")
    pruef("Genau ein Schreibauftrag", len(server.geschrieben) == 1, len(server.geschrieben))
    weg, koepfe, daten = server.geschrieben[0] if server.geschrieben else ("", {}, {})
    pruef("Als Anlegen-oder-Ersetzen fuer das eigene Konto",
          "on_conflict=konto" in weg and "merge-duplicates" in koepfe.get("prefer", "")
          and daten.get("konto") == SITZUNG["kennung"], weg)
    try:
        k_spiel = SK.aus_konto(daten.get("blend_ton", ""), daten.get("blend_bild", ""))
        fehler = ""
    except ValueError as f:
        k_spiel, fehler = None, str(f)
    pruef("Was die Seite hochlaedt, nimmt das Spiel an", k_spiel is not None, fehler)
    if k_spiel is not None:
        pruef("Mit der Laenge aus dem Ausschnitt", abs(k_spiel.dauer - laenge) < 0.01,
              "%.3f S" % k_spiel.dauer)
        pruef("Und dem Bild mit seinen Seiten",
              k_spiel.bild.get_size() == (300, 200), str(k_spiel.bild.get_size()))
        pruef("Und dort, wo es hingeschoben wurde - im Spiel genauso",
              abs(k_spiel.lage["x"] - lage["x"]) < 0.001 and abs(k_spiel.lage["y"] - lage["y"]) < 0.001
              and abs(k_spiel.lage["h"] - 0.5) < 0.001, str(k_spiel.lage))
        _r, im_spiel = SK.ton_lesen(k_spiel.ton)
        vorschau = s.evaluate("Array.from(Werkstatt.ton.fertig.proben)")
        pruef("Und es klingt im Spiel genau wie in der Vorschau",
              list(im_spiel) == vorschau, "%d / %d Proben" % (len(im_spiel), len(vorschau)))
        pruef("Die Groessen passen auch zur Tabelle (docs/KONTO.md 5.6)",
              len(daten["blend_ton"]) <= 540000 and len(daten["blend_bild"]) <= 210000)

    # ── Neu laden: das Gespeicherte ist da ────────────────────────────
    s.reload()
    s.get_by_role("button", name="KOSMETIK").click()
    pruef("Nach dem Neuladen steht der Ton als gespeichert da",
          warten(s, "Werkstatt.server.tonFertig !== null && Werkstatt.server.bildFlaeche !== null"))
    gelage = s.evaluate("Werkstatt.server.bildLage")
    pruef("Auch das gespeicherte Bild steht an seinem Platz",
          k_spiel is not None and abs(gelage["x"] - k_spiel.lage["x"]) < 0.001
          and abs(gelage["h"] - k_spiel.lage["h"]) < 0.001, str(gelage))
    pruef("Und die Vorschau ist dieselbe wie vorher",
          k_spiel is not None and s.evaluate("Array.from(Werkstatt.server.tonFertig.proben)")
          == list(SK.ton_lesen(k_spiel.ton)[1]))
    s.get_by_role("button", name="BLITZ!").click()
    s.wait_for_timeout(300)
    s.locator("canvas.spielbild").screenshot(path=str(ordner / "blitz.png"))

    # ── MP3 und der klassische Knall ──────────────────────────────────
    datei_waehlen(s, 0, ordner / "still.mp3")
    pruef("Eine MP3 wird gelesen", warten(s, "Werkstatt.ton && Werkstatt.ton.fertig "
                                             "&& Werkstatt.ton.name === 'STILL.MP3'"))
    s.get_by_role("button", name="KLASSISCH").click()
    pruef("Der Knall aus dem Spiel geht als Grundlage",
          warten(s, "Werkstatt.ton && Werkstatt.ton.name === 'KLASSISCH' && Werkstatt.ton.fertig"))

    # ── Entfernen ─────────────────────────────────────────────────────
    s.get_by_role("button", name="TON ENTFERNEN").click()
    s.get_by_role("button", name="BILD ENTFERNEN").click()
    s.get_by_role("button", name="SPEICHERN").click()
    pruef("Beides entfernt: die Zeile wird geloescht",
          warten(s, "document.body.innerText.includes('ENTFERNT')") and server.geloescht == 1)

    # ── Loadouts: eine gewaehlte Waffe bleibt gewaehlt ────────────────
    # Gemeldet in 0.29: "man klickt auf die neue Waffe, aber der Schlitz
    # flackert nur kurz" - die Seite baute sich aus dem Gespeicherten neu.
    s.get_by_role("button", name="AUSRÜSTUNG").click()
    erste = s.locator(".satz select").first
    vorher_w = erste.input_value()
    andere = [o for o in erste.locator("option").all_inner_texts()]
    wert = s.evaluate("(sel) => Array.from(sel.options).map(o => o.value)"
                      ".find(v => v !== sel.value)", erste.element_handle())
    erste.select_option(wert)
    s.wait_for_timeout(100)
    pruef("Die gewaehlte Waffe bleibt im Schlitz",
          s.locator(".satz select").first.input_value() == wert,
          "%s -> %s" % (vorher_w, s.locator(".satz select").first.input_value()))
    pruef("Und die Seite sagt, dass noch nicht gespeichert ist",
          "NOCH NICHT GESPEICHERT" in s.inner_text("body"))
    s.locator(".tafel").get_by_role("button", name="SPEICHERN").click()
    pruef("Gespeichert geht sie an den Server",
          warten(s, "document.body.innerText.includes('GESPEICHERT')")
          and server.profil_geschrieben
          and server.profil_geschrieben[-1]["loadouts"][0]["waffen"][0] == wert,
          str(server.profil_geschrieben[-1:])[:200])
    pruef("Und steht danach noch da",
          s.locator(".satz select").first.input_value() == wert
          and "NOCH NICHT GESPEICHERT" not in s.inner_text("body"))

    # ── Statistik aus den Runden (0.31) ───────────────────────────────
    # Bis 0.30 las die Seite die Uebersicht aus profil.werte, wo die
    # Einstellungen stehen - es standen Nullen da. Jetzt aus den Runden,
    # mit Filtern fuer Version, Art und Abbrueche.
    def runde(nr, modus, version, ende, werte, opfer=()):
        return {"partie": "p%d" % nr, "konto": SITZUNG["kennung"], "gespielt": 1000 + nr,
                "modus": modus, "team": -1, "gewonnen": False, "gastgeber": True,
                "werte": werte, "waffen": {"scharf": {"abschuesse": werte.get("abschuesse", 0)}},
                "version": version, "ende": ende, "opfer": list(opfer)}
    server.gefechte = [
        runde(1, "pvp", "0.31.0", "regulaer",
              {"abschuesse": 4, "tode": 2, "runden": 1, "schuesse": 10, "treffer": 5,
               "schuesse_pvp": 10, "treffer_pvp": 5},
              [{"name": "ZWEI", "konto": "k-2", "anzahl": 3},
               {"name": "GAST", "konto": "", "anzahl": 1}]),
        runde(2, "pve", "0.31.0", "regulaer",
              {"abschuesse": 0, "runden": 1, "gegner_abschuesse": 30,
               "schuesse": 40, "treffer": 10, "schuesse_pve": 40, "treffer_pve": 10}),
        runde(3, "pvp", "0.31.0", "abgebrochen",
              {"abschuesse": 2, "runden": 0, "abgebrochen": 1},
              [{"name": "ZWEI-NEU", "konto": "k-2", "anzahl": 2}]),
        # Vor 0.31: ohne Version und Ende.
        dict(runde(4, "pvp", "", "", {"abschuesse": 1, "runden": 1}), version=None, ende=None),
    ]
    s.reload()
    warten(s, "document.body.innerText.includes('AUF EINEN BLICK')")

    def kachel(name):
        return s.evaluate("""(n) => { for (const k of document.querySelectorAll('.wert'))
            if (k.querySelector('.bez').textContent === n) return k.querySelector('.zahl').textContent;
            return null; }""", name)
    namen = {d["schluessel"]: d["name"] for d in s.evaluate("DATEN.werte")}
    pruef("Die Uebersicht rechnet aus den Runden, ohne den Abbruch",
          kachel(namen["abschuesse"]) == "5" and kachel(namen["runden"]) == "3"
          and kachel(namen["abgebrochen"]) == "1" and kachel(namen["gegner_abschuesse"]) == "30",
          "%s / %s / %s" % (kachel(namen["abschuesse"]), kachel(namen["runden"]),
                            kachel(namen["abgebrochen"])))
    pruef("Trefferquote getrennt nach PVP und PVE",
          kachel("QUOTE PVP") == "50.0 %" and kachel("QUOTE PVE") == "25.0 %",
          "%s / %s" % (kachel("QUOTE PVP"), kachel("QUOTE PVE")))
    s.locator(".filter input[type=checkbox]").check()
    pruef("Abgebrochene auf Wunsch mitgezaehlt", kachel(namen["abschuesse"]) == "7",
          kachel(namen["abschuesse"]))
    s.locator(".filter input[type=checkbox]").uncheck()
    s.locator(".filter select").first.select_option("0.31.0")
    pruef("Nur Version 0.31.0: die alte Runde faellt heraus",
          kachel(namen["abschuesse"]) == "4" and kachel(namen["runden"]) == "2",
          kachel(namen["abschuesse"]))
    s.locator(".filter select").first.select_option("")
    pruef("Die Runden ohne Version lassen sich einzeln waehlen",
          kachel(namen["abschuesse"]) == "1", kachel(namen["abschuesse"]))
    s.locator(".filter select").first.select_option("*")
    s.locator(".filter select").nth(1).select_option("pve")
    pruef("Nur PVE", kachel(namen["gegner_abschuesse"]) == "30"
          and kachel(namen["abschuesse"]) == "0")
    s.locator(".filter select").nth(1).select_option("")
    s.get_by_role("button", name="ERLEDIGT").click()
    zeilen_e = s.locator(".tafel table tbody tr").all_inner_texts()
    pruef("ERLEDIGT: wen wie oft, ohne den Abbruch",
          len(zeilen_e) == 2 and "ZWEI" in zeilen_e[0] and "3" in zeilen_e[0], str(zeilen_e))
    s.locator(".filter input[type=checkbox]").check()
    zeilen_e = s.locator(".tafel table tbody tr").all_inner_texts()
    pruef("Mit Abbruch: nach Konto zusammen, unter dem neuesten Namen",
          len(zeilen_e) == 2 and "ZWEI-NEU" in zeilen_e[0] and "\t5" in zeilen_e[0],
          str(zeilen_e))
    s.get_by_role("button", name="RUNDEN").click()
    text_r = s.inner_text("body")
    pruef("RUNDEN zeigt Version und Ende",
          "ABGEBROCHEN" in text_r and "0.31.0" in text_r and "REGULÄR" in text_r)
    s.locator(".filter input[type=checkbox]").uncheck()
    pruef("Ohne Abbrueche sagt RUNDEN, wie viele fehlen",
          "1 abgebrochene ausgeblendet" in s.inner_text("body"))
    s.get_by_role("button", name="WERTE").click()
    pruef("Die Einstellungen aus dem Profil stehen als Einstellungen da",
          "keine Zaehler" in s.inner_text("body") or "keine Einstellungen" in s.inner_text("body"))

    # Mehr als eine Seite: alle Runden muessen ankommen.
    server.gefechte = [runde(100 + i, "pvp", "0.31.0", "regulaer",
                             {"abschuesse": 1, "runden": 1}) for i in range(2345)]
    server.gefecht_anfragen = 0
    s.reload()
    s.get_by_role("button", name="ÜBERSICHT").click()
    warten(s, "document.body.innerText.includes('AUF EINEN BLICK')")
    pruef("Auch 2345 Runden kommen ganz an, seitenweise",
          kachel(namen["abschuesse"]) == "2.345" and server.gefecht_anfragen == 3,
          "%s in %d Anfragen" % (kachel(namen["abschuesse"]), server.gefecht_anfragen))
    server.gefechte = []

    # ── Ohne Tabelle auf dem Server ───────────────────────────────────
    server.tabelle_fehlt = True
    s.reload()
    s.get_by_role("button", name="KOSMETIK").click()
    pruef("Fehlt die Tabelle, steht da, was zu tun ist",
          warten(s, "document.body.innerText.includes('5.6')"))

    # ── Der ADMIN (0.31) ──────────────────────────────────────────────
    # Eine eigene Seite ohne gespeicherte Anmeldung: der ADMIN meldet sich
    # am Tor an, mit dem Namen admin.
    server.tabelle_fehlt = False
    k2 = browser.new_context()
    k2.route("**/rest/v1/**", server.antworten)
    k2.route("**/auth/v1/**", server.antworten)
    a = k2.new_page()
    a.on("pageerror", lambda e: fehler_js.append(str(e)))
    a.goto(seite.as_uri())

    def anmelden(name, wort, knopfname="ANMELDEN"):
        a.locator("input").nth(0).fill(name)
        a.locator("input").nth(1).fill(wort)
        a.get_by_role("button", name=knopfname, exact=True).click()

    anmelden("admin", "123", "NEU")
    pruef("Ein Konto ADMIN laesst sich nicht anlegen",
          warten(a, "document.body.innerText.includes('NAME VORBEHALTEN')")
          and not server.rpc)
    anmelden("admin", "falsch")
    pruef("Falsches Kennwort: die Seite sagt, wie viele Versuche noch frei sind",
          warten(a, "document.body.innerText.includes('NOCH EIN FEHLVERSUCH OHNE SPERRE')"))
    anmelden("Admin", "123")
    pruef("Mit 123 (kurz, aber erlaubt) geht es - und zuerst kommt ein neues Kennwort",
          warten(a, "document.body.innerText.includes('Das erste Kennwort des ADMIN ist 123')")
          and a.get_by_role("button", name="KONTEN").count() == 0)
    a.locator("input[type=password]").nth(0).fill("NeuesAdmin1")
    a.locator("input[type=password]").nth(1).fill("NeuesAdminX")
    a.get_by_role("button", name="KENNWORT SETZEN").click()
    pruef("Zwei verschiedene werden nicht genommen",
          warten(a, "document.body.innerText.includes('NICHT GLEICH')") and server.admin_muss)
    a.locator("input[type=password]").nth(0).fill("NeuesAdmin1")
    a.locator("input[type=password]").nth(1).fill("NeuesAdmin1")
    a.get_by_role("button", name="KENNWORT SETZEN").click()
    pruef("Danach die Liste aller Konten",
          warten(a, "document.body.innerText.includes('Oeffnen zeigt ein Konto')")
          and "erster" in a.inner_text("body") and "zweiter" in a.inner_text("body"))
    pruef("Das Kennwort steht nirgends im Browser gespeichert",
          "NeuesAdmin1" not in a.evaluate("JSON.stringify(localStorage)"))
    a.get_by_role("button", name="ÜBERSICHT").click()
    pruef("Die Statistik aller zusammen",
          warten(a, "document.body.innerText.includes('Runden gezaehlt')")
          and a.evaluate("""() => { for (const k of document.querySelectorAll('.wert'))
              if (k.querySelector('.bez').textContent === DATEN.werte.find(
                  v => v.schluessel === 'abschuesse').name)
                return k.querySelector('.zahl').textContent; }""") == "8")
    a.get_by_role("button", name="RUNDEN").click()
    pruef("RUNDEN zeigt, wessen Runde es ist",
          "ERSTER" in a.inner_text("body") and "KONTO" in a.inner_text("body"))
    a.get_by_role("button", name="ERLEDIGT").click()
    pruef("ERLEDIGT: wer wen am oeftesten - ueber alle",
          "ZWEITER" in a.locator(".tafel table tbody tr").first.inner_text())

    # Ein Konto oeffnen: dieselben Reiter wie beim Spieler.
    a.get_by_role("button", name="KONTEN").click()
    a.locator("tr", has_text="erster").get_by_role("button", name="OEFFNEN").click()
    pruef("Ein Konto oeffnen zeigt seine Zahlen",
          warten(a, "document.body.innerText.includes('VOM ADMIN GEOEFFNET')")
          and warten(a, "document.body.innerText.includes('Runden gezaehlt')"))
    a.get_by_role("button", name="AUSRÜSTUNG").click()
    erste_a = a.locator(".satz select").first
    wert_a = a.evaluate("(sel) => Array.from(sel.options).map(o => o.value)"
                        ".find(v => v !== sel.value)", erste_a.element_handle())
    erste_a.select_option(wert_a)
    a.locator(".tafel").get_by_role("button", name="SPEICHERN").click()
    warten(a, "document.body.innerText.includes('GESPEICHERT')")
    letzte = [x for x in server.rpc if x[0] == "admin_profil_schreiben"]
    pruef("Loadouts eines anderen aendern: geht als ADMIN an den Server, mit Fassung",
          letzte and letzte[-1][1]["konto"] == "k-1" and letzte[-1][1]["fassung"] == 3
          and server.konten["k-1"]["profil"]["loadouts"][0]["waffen"][0] == wert_a,
          str(letzte[-1:])[:200])
    pruef("Die Werte (Einstellungen) bleiben dabei, wie sie waren",
          server.konten["k-1"]["profil"]["werte"] == {"bildschirm_ruckeln": 40})
    a.get_by_role("button", name="KOSMETIK").click()
    pruef("Auch die Kosmetik eines anderen geht auf",
          warten(a, "Werkstatt.server.geladen === true")
          and any(x[0] == "admin_kosmetik" and x[1]["konto"] == "k-1" for x in server.rpc))
    a.get_by_role("button", name="KONTO").click()
    a.locator("input").first.fill("Umbenannt")
    a.get_by_role("button", name="UMBENENNEN").click()
    pruef("Umbenennen",
          warten(a, "document.body.innerText.includes('UMBENANNT IN UMBENANNT')")
          and server.konten["k-1"]["anmeldename"] == "umbenannt")
    a.locator("input[type=password]").nth(0).fill("Spielerwort9")
    a.locator("input[type=password]").nth(1).fill("Spielerwort9")
    a.get_by_role("button", name="KENNWORT SETZEN").click()
    pruef("Kennwort eines anderen setzen",
          warten(a, "document.body.innerText.includes('KENNWORT GESETZT')")
          and server.konten["k-1"].get("wort") == "Spielerwort9")
    a.locator("input[autocomplete=off]").fill("falscher")
    a.get_by_role("button", name="ENDGUELTIG LOESCHEN").click()
    pruef("Loeschen nur mit dem richtigen Namen",
          warten(a, "document.body.innerText.includes('NICHTS GELOESCHT')")
          and "k-1" in server.konten)
    a.locator("input[autocomplete=off]").fill("umbenannt")
    a.get_by_role("button", name="ENDGUELTIG LOESCHEN").click()
    pruef("Und dann ist es weg, und es geht zurueck zur Liste",
          warten(a, "document.body.innerText.includes('GELOESCHT')")
          and warten(a, "document.body.innerText.includes('Oeffnen zeigt ein Konto')")
          and "k-1" not in server.konten and "umbenannt" not in a.inner_text("body"))

    # Gesperrt waehrend der Arbeit: jemand raet gerade. Dann ist Schluss.
    server.admin_sperre = 90
    a.get_by_role("button", name="ADMIN", exact=True).click()
    a.get_by_role("button", name="NEU LADEN").click()
    pruef("Wird der ADMIN gesperrt, endet die Anmeldung mit der Wartezeit",
          warten(a, "document.body.innerText.includes('GESPERRT, NOCH 1 MIN 30 S')")
          and a.locator("input[type=password]").count() == 1)
    server.admin_sperre = 0
    k2.close()

    pruef("Kein Fehler im Skript der Seite", not fehler_js, "; ".join(fehler_js)[:300])
    browser.close()

print()
print("Bilder:", ordner / "kosmetik.png", ordner / "blitz.png")
print("FEHLER:", fails or "keine")
sys.exit(1 if fails else 0)
