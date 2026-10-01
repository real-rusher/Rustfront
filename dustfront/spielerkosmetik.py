"""
DUSTFRONT - Spielerkosmetik
===========================

Ein erster Versuch, wie Spieler selbst etwas ins Spiel bringen: ein
eigener Ton und ein eigenes Bild fuer die Blendgranate.

Der Weg, von vorn nach hinten:

1. **Machen** - in der Kontoseite (KONTO.html, Reiter KOSMETIK). Dort wird
   eine MP3 zugeschnitten, im Bass verstaerkt, lauter gemacht, auf Wunsch
   mit dem klassischen Knall gemischt und ausgeblendet; ein Bild bekommt
   Filter. Heraus kommen eine WAV und ein PNG.
2. **Ablegen** - im Konto auf dem Server, Tabelle `kosmetik`
   (docs/KONTO.md 5.6). Das Spiel holt sie beim Anmelden und merkt sie
   sich auf der Platte, damit sie auch ohne Netz da sind.
3. **Verteilen** - in der Lobby. Jeder schickt seine an den Gastgeber,
   der Gastgeber an alle (`KosmetikTeil` unten). Wer was hat, meldet
   jeder Rechner zurueck; der Gastgeber kann mit Kosmetik erst starten,
   wenn alle alles haben.
4. **Zeigen** - wenn eine Blendgranate zuendet, klingt sie wie die des
   Werfers, und im Weiss der Blendung steht sein Bild.

**Alles, was von aussen kommt, wird hier geprueft** - vom Server wie von
einem anderen Rechner, und zwar jedes Mal. Groesse, Format, Laenge,
Abmessungen, und vor allem: der Ton wird **immer leiser**. Die Kontoseite
blendet aus, aber darauf verlaesst sich das Spiel nicht; eine veraenderte
Seite oder ein veraenderter Klient kaeme sonst mit einem Dauerton durch.
"""

from __future__ import annotations

import array
import base64
import hashlib
import io
import json
import struct
import wave

import pygame

from . import config as K

G = K.SPIELERKOSMETIK


# ══════════════════════════════════════════════════════════════════
# Der Ton
# ══════════════════════════════════════════════════════════════════

def ton_lesen(daten: bytes):
    """WAV -> (Rate, Proben als array('h'), mono). Wirft ValueError.

    Angenommen wird nur, was die Kontoseite schreibt und was harmlos ist:
    PCM mit 16 Bit, eine oder zwei Spuren, eine uebliche Rate. Die Laenge
    zaehlt nach den **wirklich vorhandenen** Proben, nicht nach dem Kopf -
    ein Kopf kann alles behaupten.
    """
    if not isinstance(daten, (bytes, bytearray)) or not daten:
        raise ValueError("KEIN TON")
    if len(daten) > G["ton_bytes"]:
        raise ValueError("TON ZU GROSS")
    if daten[:4] != b"RIFF" or daten[8:12] != b"WAVE":
        raise ValueError("KEINE WAV-DATEI")
    try:
        with wave.open(io.BytesIO(bytes(daten)), "rb") as w:
            spuren = w.getnchannels()
            breite = w.getsampwidth()
            rate = w.getframerate()
            roh = w.readframes(w.getnframes())
    except (wave.Error, EOFError, struct.error) as fehler:
        raise ValueError("WAV NICHT LESBAR") from fehler
    if breite != 2 or spuren not in (1, 2) or rate not in G["ton_raten"]:
        raise ValueError("WAV-FORMAT NICHT ERLAUBT")
    proben = array.array("h")
    proben.frombytes(roh[:len(roh) - len(roh) % 2])
    if struct.pack("=h", 1) != struct.pack("<h", 1):
        proben.byteswap()
    if spuren == 2:
        proben = array.array("h", ((proben[i] + proben[i + 1]) // 2
                                   for i in range(0, len(proben) - 1, 2)))
    dauer = len(proben) / float(rate)
    if dauer < G["ton_min"]:
        raise ValueError("TON ZU KURZ - MINDESTENS %.1f S" % G["ton_min"])
    if dauer > G["ton_max"] + 0.05:
        raise ValueError("TON ZU LANG - HOECHSTENS %.1f S" % G["ton_max"])
    return rate, proben


def ton_ausklingen(proben, rate: int):
    """Sorgt dafuer, dass der Ton immer leiser wird. Gibt neue Proben.

    In Abschnitten von 20 ms wird eine **Obergrenze** gefuehrt, und kein
    Abschnitt darf darueber liegen - wer es tut, wird heruntergeregelt:

    * Im Anlauf (120 ms) darf es noch anschwellen. Ein Knall braucht
      einen Moment, bis er da ist. Die Grenze danach ist der lauteste
      Ausschlag darin.
    * Ab da faellt die Grenze geradlinig auf null, ueber die ganze Laenge
      (`ton_ausklang`). Der letzte Abschnitt ist still.
    * Wird der Ton leiser, geht die Grenze mit - aber hoechstens um
      `ton_abfall` je Abschnitt. Sonst duerfte nach der ersten kurzen
      Luecke zwischen zwei Schlaegen nichts mehr kommen, was lauter ist
      als die Luecke, und von einem Lied bliebe ein Rauschen.

    Die Grenze steigt also nie. Lauter werden kann der Ton damit nicht -
    auch nicht ein bisschen, auch nicht ueber einen Umweg.

    Eine Grenze und kein Herunterblenden: was schon darunter liegt,
    bleibt, wie es ist.

    Die Verstaerkung wird zwischen den Abschnitten verschliffen, sonst
    knackt es an jeder Grenze - aber nur nach unten: an jeder Grenze
    zweier Abschnitte gilt die kleinere ihrer beiden Verstaerkungen. So
    bekommt keine Probe mehr, als ihr Abschnitt darf, und das Ende eines
    lauten Schlags wird nicht zur Luecke danach hin wieder lauter.

    Die Kontoseite rechnet **genau dasselbe** fuer ihre Vorschau
    (tonAusklingen in kontoseite_vorlage.html), Schritt fuer Schritt in
    derselben Reihenfolge. Hochgeladen wird aber der Ton davor, und
    gerechnet wird es nur hier, einmal - so ist das, was man auf der
    Seite hoert, auf die Probe das, was im Spiel klingt. Wer hier etwas
    aendert, aendert es dort mit; tests/kontoseite_browser.py vergleicht
    beide.
    """
    n = len(proben)
    breite = max(1, int(rate * G["ton_abschnitt"]))
    anzahl = (n + breite - 1) // breite
    spitzen = []
    for a in range(anzahl):
        stueck = proben[a * breite:(a + 1) * breite]
        spitzen.append(max((abs(x) for x in stueck), default=0))
    # round und nicht int: 0.12 / 0.02 ist im Rechner 5.999..., und int
    # machte daraus fuenf Abschnitte statt sechs.
    anlauf = max(1, round(G["ton_anlauf"] / G["ton_abschnitt"]))
    ausklang_ab = int(n * (1.0 - G["ton_ausklang"]))
    rest = max(1, n - ausklang_ab)
    oben = float(max(spitzen[:anlauf] or [0]))     # die Grenze am Anfang
    erlaubt = oben
    gaenge = []
    for a, spitze in enumerate(spitzen):
        if a < anlauf:
            gaenge.append(1.0)
            continue
        ende = min(n, (a + 1) * breite)    # gemessen am Ende des Abschnitts
        linie = oben * max(0.0, min(1.0, 1.0 - (ende - ausklang_ab) / float(rest)))
        erlaubt = min(erlaubt, linie)
        if a == anzahl - 1:
            erlaubt = 0.0
        g = min(1.0, erlaubt / float(spitze)) if spitze > 0 else 1.0
        gaenge.append(g)
        erlaubt = min(erlaubt, max(spitze * g, erlaubt * G["ton_abfall"]))
    # An jeder Grenze die kleinere der beiden; dazwischen geradlinig.
    kanten = [gaenge[0] if gaenge else 1.0]
    for a in range(1, anzahl):
        kanten.append(min(gaenge[a - 1], gaenge[a]))
    kanten.append(gaenge[-1] if gaenge else 1.0)
    aus = array.array("h", bytes(2 * n))
    for i in range(n):
        a = i // breite
        g = kanten[a] + (kanten[a + 1] - kanten[a]) * ((i % breite) / float(breite))
        aus[i] = max(-32768, min(32767, int(proben[i] * g)))
    return aus


def wav_schreiben(proben, rate: int) -> bytes:
    puffer = io.BytesIO()
    with wave.open(puffer, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        roh = array.array("h", proben)
        if struct.pack("=h", 1) != struct.pack("<h", 1):
            roh.byteswap()
        w.writeframes(roh.tobytes())
    return puffer.getvalue()


def ton_aufbereiten(daten: bytes) -> bytes:
    """Pruefen und ausklingen lassen. Gibt die WAV, die gespielt wird."""
    rate, proben = ton_lesen(daten)
    return wav_schreiben(ton_ausklingen(proben, rate), rate)


# ══════════════════════════════════════════════════════════════════
# Das Bild
# ══════════════════════════════════════════════════════════════════

def bild_lesen(daten: bytes) -> pygame.Surface:
    """PNG -> Flaeche. Wirft ValueError.

    Erst die Groesse der Datei, dann die Kennung im Kopf, dann laden,
    dann die Abmessungen - in dieser Reihenfolge, damit nichts Grosses
    oder Fremdes ueberhaupt bis zum Dekodieren kommt.
    """
    if not isinstance(daten, (bytes, bytearray)) or not daten:
        raise ValueError("KEIN BILD")
    if len(daten) > G["bild_bytes"]:
        raise ValueError("BILD ZU GROSS")
    if bytes(daten[:8]) != b"\x89PNG\r\n\x1a\n":
        raise ValueError("KEIN PNG")
    try:
        flaeche = pygame.image.load(io.BytesIO(bytes(daten)), "kosmetik.png")
    except (pygame.error, ValueError) as fehler:
        raise ValueError("PNG NICHT LESBAR") from fehler
    b, h = flaeche.get_size()
    if not (1 <= b <= G["bild_max"] and 1 <= h <= G["bild_max"]):
        raise ValueError("BILD ZU GROSS - HOECHSTENS %d PX" % G["bild_max"])
    if pygame.display.get_surface() is not None:
        flaeche = flaeche.convert_alpha()
    return flaeche


def bild_lage(daten: bytes, groesse: tuple[int, int]) -> dict:
    """Wo das Bild im Weiss steht: {"x", "y", "h"} - Mitte und Hoehe als
    Anteil am Bildschirm.

    Steht im PNG selbst, als tEXt-Abschnitt mit dem Schluessel
    "dustfront" und JSON dahinter. So braucht es weder eine neue Spalte
    auf dem Server noch eine neue Netzmeldung, und der Fingerabdruck des
    Pakets deckt die Lage mit ab. Fehlt der Abschnitt (Bilder aus 0.28)
    oder ist er kaputt, fuellt das Bild den ganzen Schirm - so gemeldet:
    "das Bild bei der Flash soll den ganzen Screen bedecken".
    """
    b, h = max(1, groesse[0]), max(1, groesse[1])
    fuellen = max(K.GAME_W / float(b), K.GAME_H / float(h)) * h / float(K.GAME_H)
    lage = {"x": 0.5, "y": 0.5, "h": fuellen}
    try:
        o = 8
        while o + 12 <= len(daten):
            laenge = struct.unpack(">I", daten[o:o + 4])[0]
            art = daten[o + 4:o + 8]
            if art == b"IDAT" or o + 12 + laenge > len(daten):
                break                       # Textabschnitte stehen davor
            if art == b"tEXt":
                inhalt = bytes(daten[o + 8:o + 8 + laenge])
                schluessel, _, text = inhalt.partition(b"\0")
                if schluessel == b"dustfront":
                    roh = json.loads(text.decode("latin-1"))
                    for k, (lo, hi) in (("x", G["lage_xy"]), ("y", G["lage_xy"]),
                                        ("h", G["lage_h"])):
                        v = float(roh[k])
                        if v == v:          # NaN fliegt raus
                            lage[k] = max(lo, min(hi, v))
                    break
            o += 12 + laenge
    except (ValueError, TypeError, KeyError, struct.error):
        pass
    return lage


# ══════════════════════════════════════════════════════════════════
# Ein Paket: Ton und Bild eines Spielers
# ══════════════════════════════════════════════════════════════════

class Kosmetik:
    """Ton und Bild eines Spielers. Eines von beiden darf fehlen.

    Die Kennung ist ein Fingerabdruck des Inhalts. An ihr erkennt jeder
    Rechner, ob er das Paket schon hat - und ob es noch das aktuelle ist.

    Durchs Netz geht der Ton **so, wie er vom Konto kam** (`ton_roh`),
    und jeder Rechner bereitet ihn selbst auf. Die Aufbereitung ist
    festgelegt, also kommt ueberall dasselbe heraus - und die Kennung,
    die am Rohen haengt, stimmt bei allen. Schickte man das Aufbereitete,
    bereitete der Empfaenger es ein zweites Mal auf, und die Kennungen
    liefen auseinander.
    """

    def __init__(self, ton: bytes = b"", bild: bytes = b"") -> None:
        self.ton_roh = bytes(ton) if ton else b""
        self.ton = ton_aufbereiten(self.ton_roh) if self.ton_roh else b""
        self.bild_daten = bytes(bild) if bild else b""
        self.bild = bild_lesen(self.bild_daten) if self.bild_daten else None
        self.lage = (bild_lage(self.bild_daten, self.bild.get_size())
                     if self.bild is not None else None)
        if not self.ton and self.bild is None:
            raise ValueError("LEERE KOSMETIK")
        self.kennung = hashlib.sha1(self.ton_roh + b"|" + self.bild_daten
                                    ).hexdigest()[:16]
        self._klang = None

    @property
    def dauer(self) -> float:
        if not self.ton:
            return 0.0
        with wave.open(io.BytesIO(self.ton), "rb") as w:
            return w.getnframes() / float(w.getframerate())

    def klang(self):
        """Der Ton fuer den Mischer, beim ersten Gebrauch gebaut."""
        if not self.ton or pygame.mixer.get_init() is None:
            return None
        if self._klang is None:
            try:
                self._klang = pygame.mixer.Sound(file=io.BytesIO(self.ton))
            except pygame.error:
                return None
        return self._klang

    def text(self) -> str:
        """So geht es durchs Netz: JSON mit Base64 darin."""
        return json.dumps({"ton": base64.b64encode(self.ton_roh).decode("ascii"),
                           "bild": base64.b64encode(self.bild_daten).decode("ascii")})

    def teile(self) -> list[str]:
        t = self.text()
        g = G["teil"]
        return [t[i:i + g] for i in range(0, len(t), g)]


def aus_text(text: str) -> Kosmetik:
    """Netztext -> Kosmetik. Wirft ValueError bei allem, was nicht passt."""
    try:
        roh = json.loads(text)
        ton = base64.b64decode(str(roh.get("ton", "")), validate=True)
        bild = base64.b64decode(str(roh.get("bild", "")), validate=True)
    except (ValueError, TypeError, AttributeError) as fehler:
        raise ValueError("PAKET NICHT LESBAR") from fehler
    return Kosmetik(ton, bild)


def aus_konto(ton_b64: str, bild_b64: str) -> Kosmetik:
    """Was der Server liefert (Base64) -> Kosmetik. Wirft ValueError."""
    try:
        ton = base64.b64decode(ton_b64 or "", validate=True)
        bild = base64.b64decode(bild_b64 or "", validate=True)
    except (ValueError, TypeError) as fehler:
        raise ValueError("KOSMETIK NICHT LESBAR") from fehler
    return Kosmetik(ton, bild)


class Sammler:
    """Setzt Pakete aus ihren Teilen wieder zusammen.

    Je Absender und Kennung ein Stapel. Kommt eine neue Kennung, ist die
    alte hinfaellig - der Spieler hat seine Kosmetik inzwischen
    geaendert. Mehr als `teile_max` Teile hat kein gueltiges Paket, und
    wer das behauptet, wird gar nicht erst gesammelt.
    """

    def __init__(self) -> None:
        self._stapel: dict = {}

    def nimm(self, von: int, kennung: str, i: int, n: int, teil: str):
        """Gibt die fertige Kosmetik zurueck, sonst None.

        Wirft ValueError, wenn das fertige Paket die Pruefung nicht
        besteht - der Aufrufer entscheidet, was dann passiert.
        """
        if not (isinstance(teil, str) and 0 < n <= G["teile_max"]
                and 0 <= i < n and len(teil) <= G["teil"]):
            return None
        alt = self._stapel.get(von)
        if alt is None or alt[0] != kennung or alt[1] != n:
            alt = (kennung, n, {})
            self._stapel[von] = alt
        alt[2][i] = teil
        if len(alt[2]) < n:
            return None
        del self._stapel[von]
        k = aus_text("".join(alt[2][j] for j in range(n)))
        if k.kennung != kennung:
            raise ValueError("KENNUNG PASST NICHT")
        return k

    def vergessen(self, von: int) -> None:
        self._stapel.pop(von, None)


# ══════════════════════════════════════════════════════════════════
# Verteilen - haengt am Gefecht wie LobbyTeil
# ══════════════════════════════════════════════════════════════════
#
# Drei Meldungen:
#
#   kos        ein Teil eines Pakets. Vom Gast an den Gastgeber ohne
#              Absender (den kennt der Gastgeber), vom Gastgeber an die
#              Gaeste mit "von".
#   kos_index  Gastgeber -> alle: wer welche Kosmetik hat (Nummer ->
#              Kennung). Danach richtet sich jeder Rechner: was nicht
#              mehr im Index steht, fliegt raus.
#   kos_hat    Gast -> Gastgeber: was hier schon fertig angekommen ist.
#              Daraus weiss der Gastgeber, ob er mit Kosmetik starten
#              kann.
#   kos_weg    Gast -> Gastgeber: ich habe meine entfernt.
#
# Die Teile gehen nicht alle auf einmal hinaus, sondern zwei je Schritt.
# Sonst stuende eine Viertelmegabyte vor jeder Weltmeldung in der
# Leitung, und die Lobby ruckelte, waehrend geladen wird.

class KosmetikTeil:
    """Was das Gefecht fuer die Spielerkosmetik tut."""

    def _kosmetik_anlegen(self) -> None:
        self.kosmetiken: dict[int, Kosmetik] = {}
        self.kos_index: dict[int, str] = {}
        self.kos_stand: dict[int, dict] = {}      # nur beim Gastgeber
        self._kos_sammler = Sammler()
        self._kos_raus: list = []                 # (Ziel oder None, Meldung)
        self._kos_eigen = ""                      # zuletzt geschickte Kennung
        self._kos_gemeldet: dict = {}
        self._kos_zugelassen = self.gastgeber is not None
        self.kos_zeigen = None                    # Bild des Werfers im Weiss
        self._kos_gross = (None, None)            # (Bild, skaliert)
        konto = getattr(self.app, "konto", None)
        if konto is not None and konto.angemeldet:
            konto.kosmetik_holen()                # frisch, im Hintergrund

    # ---- Wer was hat --------------------------------------------------
    def _eigene_kosmetik(self):
        konto = getattr(self.app, "konto", None)
        return getattr(konto, "kosmetik", None)

    def kosmetik_von(self, nummer):
        """Die Kosmetik eines Spielers, wenn sie hier ist und gilt."""
        if nummer is None:
            return None
        k = self.kosmetiken.get(nummer)
        if k is None or self.kos_index.get(nummer) != k.kennung:
            return None
        return k

    @property
    def kosmetik_aktiv(self) -> bool:
        """In der Lobby immer - dort probiert man sie aus. In der Runde nur,
        wenn der Gastgeber mit Kosmetik gestartet hat."""
        return self.in_lobby or bool(self.regelwerk.get("kosmetik"))

    def kosmetik_stand(self) -> tuple[int, int]:
        """(angekommen, noetig) ueber alle Rechner.

        Beim Gastgeber ueber alle Gaeste: jeder braucht die Kosmetik jedes
        anderen. Beim Gast nur fuer sich selbst - mehr weiss er nicht.
        """
        if self.ist_gastgeber:
            noetig = da = 0
            for gast in self.kaempfer:
                if gast == 0:
                    continue
                hat = self.kos_stand.get(gast, {})
                for wer, kennung in self.kos_index.items():
                    if wer == gast:
                        continue
                    noetig += 1
                    if hat.get(wer) == kennung:
                        da += 1
            return da, noetig
        andere = {w: k for w, k in self.kos_index.items()
                  if w != self.meine_nummer}
        da = sum(1 for w, k in andere.items()
                 if w in self.kosmetiken and self.kosmetiken[w].kennung == k)
        return da, len(andere)

    @property
    def kosmetik_bereit(self) -> bool:
        da, noetig = self.kosmetik_stand()
        return da >= noetig

    # ---- Schritt -------------------------------------------------------
    def _kosmetik_schritt(self) -> None:
        eigen = self._eigene_kosmetik()
        nummer = 0 if self.ist_gastgeber else self.meine_nummer
        kennung = eigen.kennung if eigen is not None else ""
        if self._kos_zugelassen and kennung != self._kos_eigen:
            self._kos_eigen = kennung
            if eigen is None:
                self.kosmetiken.pop(nummer, None)
                if self.ist_gastgeber:
                    self.kos_index.pop(0, None)
                    self._kos_index_melden()
                else:
                    self.gast.senden({"t": "kos_weg"})
            else:
                self.kosmetiken[nummer] = eigen
                if self.ist_gastgeber:
                    self.kos_index[0] = kennung
                    self._kos_index_melden()
                    for gast in self.kaempfer:
                        if gast != 0:
                            self._kos_schicken(gast, 0, eigen)
                else:
                    self._kos_schicken(None, None, eigen)
        if self.ist_gastgeber:
            # Wer gegangen ist, nimmt seine Kosmetik mit.
            weg = [w for w in self.kos_index if w not in self.kaempfer]
            for w in weg:
                self.kos_index.pop(w, None)
                self.kosmetiken.pop(w, None)
                self.kos_stand.pop(w, None)
                self._kos_sammler.vergessen(w)
            # Auch was noch an ihn oder von ihm unterwegs sein sollte.
            weg_auch = set(weg) | {z for (z, _m) in self._kos_raus
                                   if z is not None and z not in self.kaempfer}
            if weg_auch:
                self._kos_raus = [(z, m) for (z, m) in self._kos_raus
                                  if z not in weg_auch
                                  and m.get("von") not in weg_auch]
            if weg:
                self._kos_index_melden()
        else:
            self._kos_hat_melden()
        for _ in range(G["teile_je_schritt"]):
            if not self._kos_raus:
                break
            ziel, meldung = self._kos_raus.pop(0)
            if ziel is None:
                self.gast.senden(meldung)
            else:
                self.gastgeber.an_einen(ziel, meldung)

    def _kos_schicken(self, ziel, von, kosmetik: Kosmetik) -> None:
        # Was von demselben Absender an dasselbe Ziel noch wartet, ist
        # ueberholt - er hat seine Kosmetik inzwischen geaendert. Ginge es
        # trotzdem hinaus, fiele der Sammler drueben bei jedem alten Teil
        # auf das alte Paket zurueck und finge das neue von vorn an.
        self._kos_raus = [(z, m) for (z, m) in self._kos_raus
                          if not (z == ziel and m.get("von") == von)]
        teile = kosmetik.teile()
        for i, teil in enumerate(teile):
            m = {"t": "kos", "k": kosmetik.kennung, "i": i, "n": len(teile),
                 "d": teil}
            if von is not None:
                m["von"] = von
            self._kos_raus.append((ziel, m))

    def _kos_index_melden(self) -> None:
        self.gastgeber.an_alle({"t": "kos_index", "liste": {
            str(w): k for w, k in self.kos_index.items()}})

    def _kos_hat_melden(self) -> None:
        hat = {str(w): k.kennung for w, k in self.kosmetiken.items()}
        if hat != self._kos_gemeldet:
            self._kos_gemeldet = hat
            self.gast.senden({"t": "kos_hat", "liste": hat})

    # ---- Beim Gastgeber -----------------------------------------------
    def _kos_neuer_gast(self, nummer: int) -> None:
        """Ein Neuer bekommt den Index und alles, was es schon gibt."""
        self.gastgeber.an_einen(nummer, {"t": "kos_index", "liste": {
            str(w): k for w, k in self.kos_index.items()}})
        for wer, k in self.kosmetiken.items():
            if wer != nummer and self.kos_index.get(wer) == k.kennung:
                self._kos_schicken(nummer, wer, k)

    def _kos_vom_gast(self, nummer: int, nachricht: dict) -> None:
        art = nachricht.get("t")
        if art == "kos_hat":
            liste = nachricht.get("liste")
            if isinstance(liste, dict):
                sauber = {}
                for w, k in list(liste.items())[:64]:
                    try:
                        sauber[int(w)] = str(k)[:16]
                    except (TypeError, ValueError):
                        continue
                self.kos_stand[nummer] = sauber
            return
        if art == "kos_weg":
            if self.kos_index.pop(nummer, None) is not None:
                self.kosmetiken.pop(nummer, None)
                self._kos_index_melden()
            return
        k = self._kos_teil_nehmen(nummer, nachricht)
        if k is None:
            return
        self.kosmetiken[nummer] = k
        self.kos_index[nummer] = k.kennung
        self._kos_index_melden()
        for gast in self.kaempfer:
            if gast not in (0, nummer):
                self._kos_schicken(gast, nummer, k)

    def _kos_teil_nehmen(self, von: int, nachricht: dict):
        try:
            return self._kos_sammler.nimm(
                von, str(nachricht.get("k", ""))[:16], int(nachricht.get("i", -1)),
                int(nachricht.get("n", 0)), nachricht.get("d"))
        except (TypeError, ValueError) as fehler:
            name = getattr(self.kaempfer.get(von), "name", "?")
            self._meldung = "KOSMETIK VON %s ABGELEHNT: %s" % (name, fehler)
            self._meldung_rest = 4.0
            self.hinweis = self._meldung
            return None

    # ---- Beim Gast ----------------------------------------------------
    def _kos_beim_gast(self, nachricht: dict) -> None:
        art = nachricht.get("t")
        if art == "kos_index":
            liste = nachricht.get("liste")
            if not isinstance(liste, dict):
                return
            index = {}
            for w, k in list(liste.items())[:64]:
                try:
                    index[int(w)] = str(k)[:16]
                except (TypeError, ValueError):
                    continue
            self.kos_index = index
            for w in list(self.kosmetiken):
                if w != self.meine_nummer and index.get(w) != self.kosmetiken[w].kennung:
                    del self.kosmetiken[w]
            return
        try:
            von = int(nachricht.get("von", -1))
        except (TypeError, ValueError):
            return
        if von < 0 or von == self.meine_nummer:
            return
        k = self._kos_teil_nehmen(von, nachricht)
        if k is not None:
            self.kosmetiken[von] = k

    # ---- Die Blendgranate -------------------------------------------
    def kosmetik_blitz(self, von, staerke: float, laut: float) -> bool:
        """Zuendet eine Blendgranate von `von`: eigener Ton und eigenes Bild.

        Gibt zurueck, ob die Kosmetik gegriffen hat - dann spielt der
        Aufrufer den gewoehnlichen Knall nicht. `von` ist beim Gastgeber
        der Kaempfer, beim Gast seine Nummer aus der Meldung.
        """
        if not self.kosmetik_aktiv:
            return False
        nummer = getattr(von, "nummer", von)
        k = self.kosmetik_von(nummer if isinstance(nummer, int) else None)
        if k is None:
            return False
        klang = k.klang()
        if klang is not None and laut > 0.0:
            self.app.klaenge.ton_spielen(klang, laut)
        if k.bild is not None and staerke > 0.0:
            self.kos_zeigen = k
        return True

    def _kosmetik_bild_zeichnen(self, ziel) -> None:
        """Das Bild des Werfers im Weiss - so stark, wie das Weiss noch ist.

        Wo und wie gross, sagt seine Lage (bild_lage): ohne Angabe fuellt
        es den Schirm, sonst steht es, wo der Spieler es in der Kontoseite
        hingeschoben hat. Was ueber den Rand ragt, ist abgeschnitten.
        """
        k = self.kos_zeigen
        blend = getattr(self.befinden, "blend", 0.0)
        if k is None:
            return
        if blend <= 0.01:
            self.kos_zeigen = None
            return
        # Einmal skaliert und gemerkt, nicht in jedem Bild neu.
        if self._kos_gross[0] is not k:
            b, h = k.bild.get_size()
            ziel_h = max(1, int(k.lage["h"] * K.GAME_H))
            ziel_b = max(1, int(b * ziel_h / float(h)))
            # Weich vergroessert: ein Foto in doppelter Groesse mit harten
            # Pixeln sah aus wie ein Fehler. Wer Pixel will, hat in der
            # Kontoseite den Filter PIXEL - die bleiben auch weich gezogen
            # gut erkennbar.
            try:
                gross = pygame.transform.smoothscale(k.bild.convert_alpha()
                                                     if pygame.display.get_surface()
                                                     else k.bild, (ziel_b, ziel_h))
            except (pygame.error, ValueError):
                gross = pygame.transform.scale(k.bild, (ziel_b, ziel_h))
            self._kos_gross = (k, gross)
        s = self._kos_gross[1]
        s.set_alpha(int(255 * min(1.0, blend * 1.4)))
        ziel.blit(s, (int(k.lage["x"] * K.GAME_W - s.get_width() / 2),
                      int(k.lage["y"] * K.GAME_H - s.get_height() / 2)))
