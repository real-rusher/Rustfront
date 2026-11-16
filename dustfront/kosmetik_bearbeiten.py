"""
DUSTFRONT - Kosmetik im Spiel bearbeiten (seit 0.34.135)
========================================================

Gewuenscht: "man soll seine Cosmetics jetzt bitte auch in-game bearbeiten
koennen". Bis hierhin ging das nur auf der Kontoseite (KONTO.html, Reiter
KOSMETIK); das Spiel konnte Ton und Bild der Blendgranate nur lesen.

Hier dasselbe in klein, als Maske im Spiel:

* **Ton** - eine Datei (WAV, MP3, OGG ...) laden, Anfang und Laenge
  waehlen, lauter machen und den Bass anheben. Heraus kommt eine WAV, mono,
  16 Bit, K.KOSMETIK_EDITOR rate. Ausklingen laesst sie das Spiel ohnehin
  beim Abspielen (spielerkosmetik.ton_ausklingen) - die Vorschau hier
  spielt genau das.
* **Bild** - eine Datei (PNG, JPG ...) laden, einen Filter waehlen, Lage
  und Groesse im Weiss setzen. Heraus kommt ein PNG mit dem
  tEXt-Abschnitt "dustfront", wie ihn die Kontoseite schreibt.

Dateien kommen auf zwei Wegen herein: ins Fenster ziehen (pygame
DROPFILE) oder in den Ordner `kosmetik` neben den Einstellungen legen -
TON LADEN / BILD LADEN blaettern dann durch, was dort liegt. Ein
Dateidialog fehlt mit Absicht: pygame hat keinen, und tkinter ist nicht
auf jedem Rechner da.

Gespeichert wird ins Konto (Konto.kosmetik_speichern, Tabelle `kosmetik`),
dasselbe wie die Kontoseite; die Musik des Kontos bleibt, wie sie ist.
Die Pruefung ist dieselbe wie fuer jedes fremde Paket.
"""

from __future__ import annotations

import array
import base64
import io
import json
import struct
import wave
import zlib
from pathlib import Path

import pygame

from . import config as K
from . import pfade
from . import spielerkosmetik as SK
from . import ui
from .font import SCHRIFT
from .menues import Menue, _mitte

E = K.KOSMETIK_EDITOR
G = K.SPIELERKOSMETIK


# ══════════════════════════════════════════════════════════════════
# Ton
# ══════════════════════════════════════════════════════════════════

def _mono_16(roh: bytes, breite: int, spuren: int) -> array.array:
    """PCM beliebiger Breite -> mono, 16 Bit."""
    if breite == 1:
        werte = [(b - 128) << 8 for b in roh]
    elif breite == 2:
        a = array.array("h")
        a.frombytes(roh[:len(roh) - len(roh) % 2])
        if struct.pack("=h", 1) != struct.pack("<h", 1):
            a.byteswap()
        werte = a
    elif breite == 3:
        werte = [int.from_bytes(roh[i:i + 3], "little", signed=True) >> 8
                 for i in range(0, len(roh) - 2, 3)]
    elif breite == 4:
        a = array.array("i")
        a.frombytes(roh[:len(roh) - len(roh) % 4])
        if struct.pack("=i", 1) != struct.pack("<i", 1):
            a.byteswap()
        werte = [x >> 16 for x in a]
    else:
        raise ValueError("TONFORMAT UNBEKANNT")
    if spuren <= 1:
        return array.array("h", werte)
    n = len(werte) // spuren
    return array.array("h", (sum(werte[i * spuren:(i + 1) * spuren]) // spuren for i in range(n)))


def ton_laden(pfad) -> tuple:
    """Eine Tondatei -> (Rate, Proben mono 16 Bit). Wirft ValueError.

    WAV liest das Spiel selbst (jede Breite, jede Rate); alles andere
    dekodiert der Mischer von pygame - dafuer muss er laufen."""
    pfad = Path(pfad)
    if pfad.stat().st_size > E["datei_max"]:
        raise ValueError("DATEI ZU GROSS")
    if pfad.suffix.lower() == ".wav":
        try:
            with wave.open(str(pfad), "rb") as w:
                spuren, breite, rate = w.getnchannels(), w.getsampwidth(), w.getframerate()
                roh = w.readframes(min(w.getnframes(), rate * int(E["ton_quelle_max"])))
        except (wave.Error, EOFError, struct.error) as fehler:
            raise ValueError("WAV NICHT LESBAR") from fehler
        return rate, _mono_16(roh, breite, spuren)
    if pygame.mixer.get_init() is None:
        try:
            pygame.mixer.init()
        except pygame.error as fehler:
            raise ValueError("OHNE TON NUR WAV-DATEIEN") from fehler
    try:
        klang = pygame.mixer.Sound(file=str(pfad))
    except pygame.error as fehler:
        raise ValueError("TON NICHT LESBAR") from fehler
    rate, fmt, spuren = pygame.mixer.get_init()
    roh = klang.get_raw()
    if abs(fmt) == 16:
        a = array.array("h" if fmt < 0 else "H")
        a.frombytes(roh[:len(roh) - len(roh) % 2])
        werte = a if fmt < 0 else array.array("h", (x - 32768 for x in a))
        roh = werte.tobytes()
        breite = 2
    elif abs(fmt) == 8:
        breite = 1
        if fmt < 0:
            roh = bytes((b + 128) & 255 for b in roh)
    elif abs(fmt) == 32:
        f = array.array("f")
        f.frombytes(roh[:len(roh) - len(roh) % 4])
        roh = array.array("h", (max(-32768, min(32767, int(x * 32767))) for x in f)).tobytes()
        breite = 2
    else:
        raise ValueError("TONFORMAT UNBEKANNT")
    obergrenze = rate * int(E["ton_quelle_max"]) * spuren * breite
    return rate, _mono_16(roh[:obergrenze], breite, spuren)


def ton_bauen(rate: int, proben, start: float, laenge: float,
              lauter: float = 1.0, bass: float = 0.0) -> bytes:
    """Ausschnitt -> WAV (mono, 16 Bit, E rate). Anfang und Laenge in s;
    zu kurze Quellen werden mit Stille auf G ton_min aufgefuellt."""
    ziel = int(E["rate"])
    laenge = max(G["ton_min"], min(G["ton_max"], float(laenge)))
    n_quelle = len(proben)
    n = int(laenge * ziel)
    schritt = rate / float(ziel)
    a0 = max(0.0, float(start)) * rate
    aus = array.array("h", bytes(2 * n))
    # Bass: ein einfacher Tiefpass (`bass_grenze` Hz), dazugemischt.
    import math
    alpha = 1.0 - math.exp(-2.0 * math.pi * E["bass_grenze"] / ziel)
    tief = 0.0
    for i in range(n):
        p = a0 + i * schritt
        j = int(p)
        if j + 1 < n_quelle:
            t = p - j
            x = proben[j] * (1.0 - t) + proben[j + 1] * t
        elif j < n_quelle:
            x = float(proben[j])
        else:
            x = 0.0
        tief += alpha * (x - tief)
        y = (x + bass * tief) * lauter
        aus[i] = -32768 if y < -32768 else (32767 if y > 32767 else int(y))
    return SK.wav_schreiben(aus, ziel)


# ══════════════════════════════════════════════════════════════════
# Bild
# ══════════════════════════════════════════════════════════════════

FILTER = ["keiner", "grau", "sepia", "warm", "kalt", "negativ"]
FILTER_NAMEN = {"keiner": "KEINER", "grau": "GRAU", "sepia": "SEPIA", "warm": "WARM",
                "kalt": "KALT", "negativ": "NEGATIV"}


def bild_laden(pfad) -> pygame.Surface:
    pfad = Path(pfad)
    if pfad.stat().st_size > E["datei_max"]:
        raise ValueError("DATEI ZU GROSS")
    try:
        f = pygame.image.load(str(pfad))
    except (pygame.error, FileNotFoundError) as fehler:
        raise ValueError("BILD NICHT LESBAR") from fehler
    return passend(f)


def passend(f: pygame.Surface, hoechstens: int | None = None) -> pygame.Surface:
    """Hoechstens G bild_max breit und hoch, Seitenverhaeltnis bleibt."""
    hoechstens = hoechstens or G["bild_max"]
    b, h = f.get_size()
    m = min(1.0, hoechstens / float(max(b, h, 1)))
    if m < 1.0:
        f = pygame.transform.smoothscale(f.convert_alpha() if pygame.display.get_surface() else f,
                                         (max(1, int(b * m)), max(1, int(h * m))))
    return f


def bild_filter(f: pygame.Surface, art: str) -> pygame.Surface:
    neu = f.copy()
    if art in ("grau", "sepia"):
        neu = pygame.transform.grayscale(neu)
    if art == "sepia":
        neu.fill((255, 222, 170), special_flags=pygame.BLEND_RGB_MULT)
    elif art == "warm":
        neu.fill((255, 218, 176), special_flags=pygame.BLEND_RGB_MULT)
    elif art == "kalt":
        neu.fill((176, 212, 255), special_flags=pygame.BLEND_RGB_MULT)
    elif art == "negativ":
        # pygame-ce kann es seit 2.2; die Deckkraft bleibt die des Bildes.
        umkehren = getattr(pygame.transform, "invert", None)
        if umkehren is not None:
            neu = umkehren(neu)
    return neu


def _abschnitt(art: bytes, inhalt: bytes) -> bytes:
    return (struct.pack(">I", len(inhalt)) + art + inhalt
            + struct.pack(">I", zlib.crc32(art + inhalt) & 0xFFFFFFFF))


def bild_png(f: pygame.Surface, lage: dict) -> bytes:
    """Flaeche -> PNG mit der Lage als tEXt "dustfront" (wie die
    Kontoseite); passt es nicht in G bild_bytes, wird es kleiner."""
    text = json.dumps({"x": round(lage["x"], 3), "y": round(lage["y"], 3),
                       "h": round(lage["h"], 3)}).encode("latin-1")
    bild = f
    for _ in range(12):
        puffer = io.BytesIO()
        pygame.image.save(bild, puffer, "PNG")
        roh = puffer.getvalue()
        # Direkt hinter IHDR (8 Byte Kennung + 25 Byte IHDR).
        png = roh[:33] + _abschnitt(b"tEXt", b"dustfront\0" + text) + roh[33:]
        if len(png) <= G["bild_bytes"]:
            return png
        b, h = bild.get_size()
        bild = pygame.transform.smoothscale(bild, (max(1, int(b * 0.8)), max(1, int(h * 0.8))))
    raise ValueError("BILD ZU GROSS")


# ══════════════════════════════════════════════════════════════════
# Die Maske
# ══════════════════════════════════════════════════════════════════

TON_ENDUNGEN = (".wav", ".mp3", ".ogg", ".flac", ".opus")
BILD_ENDUNGEN = (".png", ".jpg", ".jpeg", ".bmp", ".webp", ".gif", ".tga")


def ordner() -> Path | None:
    o = pfade.datei(E["ordner"])
    if o is not None:
        try:
            o.mkdir(parents=True, exist_ok=True)
        except OSError:
            return None
    return o


def ordner_zeigen(o: Path) -> None:
    """Den Ordner im Dateimanager oeffnen, wo das geht (nicht im Browser,
    nicht auf dem Telefon: plattform.prozesse_erlaubt)."""
    from . import plattform
    if not plattform.prozesse_erlaubt():
        return
    import subprocess
    import sys
    try:
        if sys.platform.startswith("win"):
            import os
            os.startfile(str(o))  # noqa: S606 - nur der eigene Ordner
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(o)])
        else:
            subprocess.Popen(["xdg-open", str(o)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except (OSError, AttributeError):
        pass


class KosmetikBearbeiten(Menue):
    """Ton und Bild der Blendgranate, im Spiel gemacht (seit 0.34.135)."""

    titel = "KOSMETIK"
    LINKS = 300

    def __init__(self, app) -> None:
        self.tafel = _mitte(620, 336)
        # Quelle des Tons: (Rate, Proben, Name) oder None.
        self.ton_quelle = None
        self.ton_b64 = ""            # was gespeichert wird (unveraendert: das Alte)
        self.ton_geaendert = False
        self.bild_quelle = None      # Flaeche vor dem Filter
        self.bild_name = ""
        self.bild_b64 = ""
        self.bild_geaendert = False
        self.lage = {"x": 0.5, "y": 0.5, "h": 0.6}
        self.filter = "keiner"
        self._ton_i = -1
        self._bild_i = -1
        self._vorschau = None
        super().__init__(app)
        self._vom_konto()

    @property
    def konto(self):
        return getattr(self.app, "konto", None)

    # ---- Laden ---------------------------------------------------------
    def _vom_konto(self) -> None:
        konto = self.konto
        if konto is None:
            return
        roh = konto._kosmetik_roh() if hasattr(konto, "_kosmetik_roh") else {}
        if roh.get("ton"):
            try:
                daten = base64.b64decode(roh["ton"])
                rate, proben = SK.ton_lesen(daten)
                self.ton_quelle = (rate, proben, "IM KONTO")
                self.ton_b64 = roh["ton"]
                self._regler("laenge").wert = self._laenge_wert(len(proben) / float(rate))
            except ValueError:
                pass
        if roh.get("bild"):
            try:
                daten = base64.b64decode(roh["bild"])
                f = SK.bild_lesen(daten)
                self.bild_quelle = f
                self.bild_name = "IM KONTO"
                self.bild_b64 = roh["bild"]
                self.lage = SK.bild_lage(daten, f.get_size())
                self._lage_in_regler()
            except ValueError:
                pass

    def datei_laden(self, pfad) -> None:
        """Eine Datei, egal woher (Ordner oder ins Fenster gezogen)."""
        pfad = Path(pfad)
        endung = pfad.suffix.lower()
        try:
            if endung in TON_ENDUNGEN:
                rate, proben = ton_laden(pfad)
                if len(proben) < rate * 0.1:
                    raise ValueError("TON ZU KURZ")
                self.ton_quelle = (rate, proben, pfad.name)
                self._regler("start").wert = 0
                self._regler("laenge").wert = self._laenge_wert(min(G["ton_max"], len(proben) / float(rate)))
                self.ton_geaendert = True
                self.sagen("TON: %s" % pfad.name.upper()[:40])
            elif endung in BILD_ENDUNGEN:
                self.bild_quelle = bild_laden(pfad)
                self.bild_name = pfad.name
                self.bild_geaendert = True
                self._vorschau = None
                self.sagen("BILD: %s" % pfad.name.upper()[:40])
            else:
                self.sagen("UNBEKANNTE DATEI: %s" % endung.upper())
        except (ValueError, OSError) as fehler:
            self.sagen(str(fehler).upper()[:60], 4.0)

    def _naechste(self, endungen, i: int):
        o = ordner()
        if o is None:
            return None, i
        dateien = sorted(p for p in o.iterdir() if p.suffix.lower() in endungen)
        if not dateien:
            self.sagen("KEINE DATEI IM ORDNER %s" % str(o).upper()[-40:], 4.0)
            return None, i
        i = (i + 1) % len(dateien)
        return dateien[i], i

    # ---- Werte ---------------------------------------------------------
    def _regler(self, name: str):
        return next(e for e in self.elemente if e.name == name)

    @staticmethod
    def _laenge_wert(sek: float) -> int:
        a = (sek - G["ton_min"]) / (G["ton_max"] - G["ton_min"])
        return max(0, min(100, int(round(a * 100 / 5.0)) * 5))

    def werte(self) -> dict:
        r = self._regler
        laenge = G["ton_min"] + (G["ton_max"] - G["ton_min"]) * r("laenge").wert / 100.0
        start = 0.0
        if self.ton_quelle is not None:
            rate, proben, _n = self.ton_quelle
            start = max(0.0, len(proben) / float(rate) - laenge) * r("start").wert / 100.0
        lo, hi = E["lauter"]
        return {"start": start, "laenge": laenge,
                "lauter": lo + (hi - lo) * r("lauter").wert / 100.0,
                "bass": E["bass"] * r("bass").wert / 100.0}

    def _lage_in_regler(self) -> None:
        self._regler("x").wert = max(0, min(100, int(round(self.lage["x"] * 100))))
        self._regler("y").wert = max(0, min(100, int(round(self.lage["y"] * 100))))
        lo, hi = E["groesse"]
        self._regler("h").wert = max(0, min(100, int(round((self.lage["h"] - lo) / (hi - lo) * 100))))

    def _lage_aus_regler(self) -> None:
        lo, hi = E["groesse"]
        self.lage = {"x": self._regler("x").wert / 100.0, "y": self._regler("y").wert / 100.0,
                     "h": lo + (hi - lo) * self._regler("h").wert / 100.0}

    def ton_wav(self) -> bytes:
        rate, proben, _n = self.ton_quelle
        w = self.werte()
        return ton_bauen(rate, proben, w["start"], w["laenge"], w["lauter"], w["bass"])

    def bild_fertig(self) -> pygame.Surface:
        return bild_filter(self.bild_quelle, self.filter)

    # ---- Maske ---------------------------------------------------------
    def aufbauen(self) -> None:
        r = self.tafel
        x, b = r.x + 16, self.LINKS
        y = r.y + 34
        h = 17
        self.elemente = [
            ui.Knopf((x, y, b // 2 - 2, h), "TON LADEN", "ton_laden"),
            ui.Knopf((x + b // 2 + 2, y, b // 2 - 2, h), "TON ANHÖREN", "ton_hoeren"),
            ui.Regler((x, y + 20, b, h), "ANFANG", "start", 0, 5),
            ui.Regler((x, y + 39, b, h), "LÄNGE", "laenge", 100, 5),
            ui.Regler((x, y + 58, b, h), "LAUTER", "lauter", 20, 5),
            ui.Regler((x, y + 77, b, h), "BASS", "bass", 0, 5),
            ui.Knopf((x, y + 97, b, h), "TON ENTFERNEN", "ton_weg"),
            ui.Knopf((x, y + 128, b // 2 - 2, h), "BILD LADEN", "bild_laden"),
            ui.Wahl((x + b // 2 + 2, y + 128, b // 2 - 2, h), "FILTER", "filter", FILTER, 0,
                    FILTER_NAMEN, spalte=44),
            ui.Regler((x, y + 148, b, h), "LINKS-RECHTS", "x", 50, 5),
            ui.Regler((x, y + 167, b, h), "OBEN-UNTEN", "y", 50, 5),
            ui.Regler((x, y + 186, b, h), "GRÖSSE", "h", 26, 2),
            ui.Knopf((x, y + 206, b, h), "BILD ENTFERNEN", "bild_weg"),
            ui.Knopf((x, y + 238, b // 2 - 2, h + 2), "SPEICHERN", "speichern"),
            ui.Knopf((x + b // 2 + 2, y + 238, b // 2 - 2, h + 2), "ORDNER ÖFFNEN", "ordner"),
        ]

    def geaendert(self, el) -> None:
        if el.name in ("start", "laenge", "lauter", "bass") and self.ton_quelle is not None:
            self.ton_geaendert = True
        elif el.name in ("x", "y", "h"):
            self._lage_aus_regler()
            self.bild_geaendert = self.bild_quelle is not None
        elif el.name == "filter":
            self.filter = el.wert
            self._vorschau = None
            self.bild_geaendert = self.bild_quelle is not None

    def ausloesen(self, el) -> None:
        n = el.name
        if n == "ton_laden":
            p, self._ton_i = self._naechste(TON_ENDUNGEN, self._ton_i)
            if p is not None:
                self.datei_laden(p)
        elif n == "bild_laden":
            p, self._bild_i = self._naechste(BILD_ENDUNGEN, self._bild_i)
            if p is not None:
                self.datei_laden(p)
        elif n == "ton_hoeren":
            self.anhoeren()
        elif n == "ton_weg":
            self.ton_quelle, self.ton_b64, self.ton_geaendert = None, "", True
            self.sagen("TON ENTFERNT (NOCH NICHT GESPEICHERT)")
        elif n == "bild_weg":
            self.bild_quelle, self.bild_b64, self.bild_geaendert = None, "", True
            self._vorschau = None
            self.sagen("BILD ENTFERNT (NOCH NICHT GESPEICHERT)")
        elif n == "speichern":
            self.speichern()
        elif n == "ordner":
            o = ordner()
            if o is not None:
                ordner_zeigen(o)
                self.sagen("DATEIEN HIERHER: %s" % str(o).upper()[-48:], 5.0)

    def anhoeren(self) -> None:
        if self.ton_quelle is None:
            self.sagen("KEIN TON GELADEN")
            return
        try:
            wav = SK.ton_aufbereiten(self.ton_wav())
            if pygame.mixer.get_init() is None:
                self.sagen("TON IST AUS")
                return
            klang = pygame.mixer.Sound(file=io.BytesIO(wav))
            klang.set_volume(E["vorschau_laut"])
            klang.play()
        except (ValueError, pygame.error) as fehler:
            self.sagen(str(fehler).upper()[:60], 4.0)

    def paket(self) -> tuple:
        """(Ton, Bild) als Base64, so wie sie ins Konto gehen. Wirft
        ValueError, wenn etwas die Pruefung nicht besteht."""
        ton, bild = self.ton_b64, self.bild_b64
        if self.ton_geaendert:
            ton = "" if self.ton_quelle is None else base64.b64encode(self.ton_wav()).decode("ascii")
        if self.bild_geaendert:
            bild = ("" if self.bild_quelle is None else
                    base64.b64encode(bild_png(self.bild_fertig(), self.lage)).decode("ascii"))
        # Dieselbe Pruefung wie fuer jedes fremde Paket.
        if ton or bild:
            SK.aus_konto(ton, bild)
        return ton, bild

    def speichern(self) -> None:
        konto = self.konto
        if konto is None or not konto.angemeldet:
            self.sagen("NUR MIT KONTO - ERST ANMELDEN", 4.0)
            return
        try:
            ton, bild = self.paket()
        except ValueError as fehler:
            self.sagen(str(fehler).upper()[:60], 4.0)
            return
        konto.kosmetik_speichern(ton, bild)
        self.ton_b64, self.bild_b64 = ton, bild
        self.ton_geaendert = self.bild_geaendert = False

    def ereignis(self, ev) -> None:
        if ev.type == getattr(pygame, "DROPFILE", -1):
            self.datei_laden(getattr(ev, "file", ""))
            return
        if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 3:
            self.klang("menue", 0.4)
            self.zurueck()
            return
        super().ereignis(ev)

    # ---- Bild ----------------------------------------------------------
    def vorschau_rect(self) -> pygame.Rect:
        r = self.tafel
        b = r.right - 16 - (r.x + 16 + self.LINKS + 16)
        h = int(b * K.GAME_H / float(K.GAME_W))
        return pygame.Rect(r.right - 16 - b, r.y + 34, b, h)

    def inhalt_zeichnen(self, ziel) -> None:
        v = self.vorschau_rect()
        pygame.draw.rect(ziel, (250, 250, 246), v)
        if self.bild_quelle is not None:
            if self._vorschau is None:
                self._vorschau = self.bild_fertig()
            f = self._vorschau
            hoch = max(1, int(self.lage["h"] * v.height))
            breit = max(1, int(f.get_width() * hoch / float(max(1, f.get_height()))))
            klein = pygame.transform.smoothscale(f, (breit, hoch)) if breit * hoch < 400000 else None
            if klein is not None:
                alt = ziel.get_clip()
                ziel.set_clip(v)
                ziel.blit(klein, (v.x + int(self.lage["x"] * v.width) - breit // 2,
                                  v.y + int(self.lage["y"] * v.height) - hoch // 2))
                ziel.set_clip(alt)
        pygame.draw.rect(ziel, K.C_MUTED, v, 1)
        SCHRIFT.zeichnen(ziel, "SO STEHT ES IM WEISS DER BLENDUNG", v.centerx, v.bottom + 4,
                         K.C_MUTED, 1, ausrichtung="mitte")
        y = v.bottom + 20
        if self.ton_quelle is not None:
            w = self.werte()
            ton = "TON: %s  %.1f-%.1f S" % (self.ton_quelle[2].upper()[:22], w["start"],
                                            w["start"] + w["laenge"])
        else:
            ton = "TON: KEINER (KLASSISCHER KNALL)"
        SCHRIFT.zeichnen(ziel, ton, v.x, y, K.C_CREAM, 1)
        bild = ("BILD: %s" % self.bild_name.upper()[:28]) if self.bild_quelle is not None else "BILD: KEINES"
        SCHRIFT.zeichnen(ziel, bild, v.x, y + 11, K.C_CREAM, 1)
        konto = self.konto
        stand = ("NICHT ANGEMELDET - SPEICHERN GEHT NUR MIT KONTO"
                 if konto is None or not konto.angemeldet
                 else (getattr(konto, "kosmetik_meldung", "") or "KONTO: %s" % konto.name.upper()))
        if self.ton_geaendert or self.bild_geaendert:
            stand = "UNGESPEICHERT - " + stand
        SCHRIFT.zeichnen(ziel, stand[:58], v.x, y + 24, K.C_AMBER, 1)
        SCHRIFT.zeichnen(ziel, "DATEIEN INS FENSTER ZIEHEN ODER IN DEN", v.x, y + 42, K.C_MUTED, 1)
        SCHRIFT.zeichnen(ziel, "ORDNER LEGEN (ORDNER ÖFFNEN) UND LADEN", v.x, y + 52, K.C_MUTED, 1)
        SCHRIFT.zeichnen(ziel, "TON: WAV MP3 OGG   BILD: PNG JPG", v.x, y + 62, K.C_MUTED, 1)
        SCHRIFT.zeichnen(ziel, "DER TON KLINGT IMMER AUS (WIE IM SPIEL).", v.x, y + 76, K.C_MUTED_DK, 1)

    def fusstext(self) -> str:
        return "[PFEILE] WÄHLEN   [ENTER] AUSLÖSEN   [ESC] ZURÜCK"
