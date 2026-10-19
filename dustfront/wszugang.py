"""
DUSTFRONT - Der Weg eines Gastes zu einem Online-Code, ohne cloudflared
======================================================================

Seit 0.34.20, fuer iOS. Dort darf ein Spiel kein zweites Programm
starten, und `cloudflared access tcp` (online.Zugang) faellt weg. Was es
tut, ist aber klein - und hier in Python nachgebaut:

1. Auf 127.0.0.1 lauschen. Damit verbindet sich das Spiel wie immer
   (netz.Gast) - es merkt keinen Unterschied.
2. Fuer jede Verbindung dorthin ein WebSocket zu
   `https://CODE.trycloudflare.com/`: ein gewoehnliches HTTP/1.1
   `GET /` mit `Upgrade: websocket`. Cloudflare reicht es durch den
   Tunnel des Gastgebers an dessen Lobby weiter.
3. Danach Bytes hin und her, in binaeren WebSocket-Rahmen - roh, ohne
   eigenes Format darin. Was das Spiel schickt, kommt beim Gastgeber
   genauso an wie von einem Gast mit cloudflared.

So schickt es auch cloudflared 2026.10.0 (nachgemessen mit einem
Probe-Server: dieselben Kopfzeilen, ein Rahmen je Lesen, maskiert, Typ 2).
Darum spielt ein iPhone auch mit einem Gastgeber am Rechner, der seinen
Code ganz normal mit cloudflared aufmacht: **Crossplay**.

Gastgeber mit Code geht auf iOS nicht. Der Tunnel selbst ist mehr als ein
WebSocket (eine eigene Anmeldung bei Cloudflare ueber QUIC oder HTTP/2),
und den nachzubauen lohnt nicht. Im LAN aufmachen geht.

**Fehler.** Gleich beim Anlegen wird einmal durchverbunden (der erste
Weg wird aufgehoben und vom Spiel benutzt). Ist der Code falsch oder die
Lobby zu, antwortet Cloudflare nicht mit 101, und `fehler` sagt es, bevor
das Spiel ueberhaupt anklopft - genau wie beim Zugang mit cloudflared.

Je Verbindung zwei Faeden, einer je Richtung. GRUND: eine TLS-Steckdose
laesst sich nicht verlaesslich mit select() abfragen (es koennen Bytes im
TLS-Puffer liegen, die select nicht sieht); ein Faden, der blockierend
liest, kennt das Problem nicht.
"""

from __future__ import annotations

import base64
import hashlib
import os
import socket
import ssl
import struct
import threading
import time

from . import config as K

O = K.ONLINE
_MAGIE = b"258EAFA5-E914-47DA-95CA-C5AB0DC85B11"     # RFC 6455, 1.3


class HandschlagFehler(Exception):
    pass


def _maskieren(daten: bytes, maske: bytes) -> bytes:
    """XOR mit der Maske, ueber den ganzen Block auf einmal. GRUND: Byte
    fuer Byte in Python kostet bei 16 KB eine Millisekunde je Rahmen."""
    n = len(daten)
    if not n:
        return b""
    lang = (maske * (n // 4 + 1))[:n]
    return (int.from_bytes(daten, "big") ^ int.from_bytes(lang, "big")).to_bytes(n, "big")


# ══════════════════════════════════════════════════════════════════
# WebSocket, nur was hier gebraucht wird (RFC 6455, als Client)
# ══════════════════════════════════════════════════════════════════

class WebSocket:
    def __init__(self, sock) -> None:
        self.sock = sock
        self._puffer = b""
        self._schreiben = threading.Lock()
        self.zu = False

    @classmethod
    def verbinden(cls, host: str, port: int = 443, tls=True,
                  frist: float | None = None, name: str = "") -> "WebSocket":
        """Verbinden und den Handschlag machen. Wirft HandschlagFehler mit
        einer Meldung fuer die Anzeige.

        `name`: der Name des Tunnels (Host-Zeile und Zertifikat), wenn er
        nicht die Adresse ist, mit der verbunden wird - nur in den
        Pruefungen, wo "Cloudflare" auf diesem Rechner steht."""
        frist = O["ws_frist"] if frist is None else frist
        name = name or host
        try:
            roh = socket.create_connection((host, port), timeout=frist)
        except OSError as e:
            raise HandschlagFehler("CLOUDFLARE NICHT ERREICHBAR") from e
        try:
            roh.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        except OSError:
            pass
        sock = roh
        try:
            if tls:
                if tls is True:
                    from .ablage import tls_kontext
                    tls = tls_kontext()
                sock = tls.wrap_socket(roh, server_hostname=name)
            ws = cls(sock)
            ws._handschlag(name, port, tls)
        except HandschlagFehler:
            sock.close()
            raise
        except ssl.SSLError as e:
            sock.close()
            raise HandschlagFehler("ZERTIFIKAT VON CLOUDFLARE ABGELEHNT") from e
        except OSError as e:
            sock.close()
            raise HandschlagFehler("CLOUDFLARE NICHT ERREICHBAR") from e
        sock.settimeout(None)
        return ws

    def _handschlag(self, host: str, port: int, tls) -> None:
        schluessel = base64.b64encode(os.urandom(16))
        name = host if port in ((443,) if tls else (80,)) else "%s:%d" % (host, port)
        # Dieselben Kopfzeilen wie cloudflared, in derselben Reihenfolge.
        # Auch die Kennung: Cloudflare soll den Weg behandeln wie den von
        # cloudflared selbst - es ist ja derselbe.
        anfrage = ("GET / HTTP/1.1\r\n"
                   "Host: %s\r\n"
                   "User-Agent: cloudflared/%s\r\n"
                   "Connection: Upgrade\r\n"
                   "Sec-WebSocket-Key: %s\r\n"
                   "Sec-WebSocket-Version: 13\r\n"
                   "Upgrade: websocket\r\n\r\n"
                   % (name, O["version"], schluessel.decode("ascii")))
        self.sock.sendall(anfrage.encode("ascii"))
        while b"\r\n\r\n" not in self._puffer:
            stueck = self.sock.recv(4096)
            if not stueck:
                raise HandschlagFehler("CLOUDFLARE HAT AUFGELEGT")
            self._puffer += stueck
            if len(self._puffer) > 65536:
                raise HandschlagFehler("CLOUDFLARE ANTWORTET UNVERSTÄNDLICH")
        kopf, self._puffer = self._puffer.split(b"\r\n\r\n", 1)
        zeilen = kopf.decode("latin-1").split("\r\n")
        teile = zeilen[0].split(" ", 2)
        status = teile[1] if len(teile) > 1 else ""
        if status != "101":
            # Was Cloudflare fuer einen unbekannten oder geschlossenen Tunnel
            # schickt: 404 oder eine der 5xx-Seiten (530, 502).
            raise HandschlagFehler("LOBBY NICHT ERREICHBAR - CODE FALSCH ODER ZU")
        felder = {}
        for z in zeilen[1:]:
            k, _, v = z.partition(":")
            felder[k.strip().lower()] = v.strip()
        soll = base64.b64encode(hashlib.sha1(schluessel + _MAGIE).digest()).decode("ascii")
        if felder.get("sec-websocket-accept") != soll:
            raise HandschlagFehler("CLOUDFLARE ANTWORTET UNVERSTÄNDLICH")

    # ---- Rahmen ---------------------------------------------------------
    def senden(self, daten: bytes, art: int = 0x2) -> None:
        """Ein Rahmen, maskiert, wie es ein Client muss (RFC 6455, 5.3)."""
        n = len(daten)
        kopf = bytearray([0x80 | art])
        if n < 126:
            kopf.append(0x80 | n)
        elif n < 65536:
            kopf.append(0x80 | 126)
            kopf += struct.pack(">H", n)
        else:
            kopf.append(0x80 | 127)
            kopf += struct.pack(">Q", n)
        maske = os.urandom(4)
        kopf += maske
        with self._schreiben:
            self.sock.sendall(bytes(kopf) + _maskieren(bytes(daten), maske))

    def _lesen(self, n: int) -> bytes:
        while len(self._puffer) < n:
            stueck = self.sock.recv(max(4096, n - len(self._puffer)))
            if not stueck:
                raise EOFError
            self._puffer += stueck
        raus, self._puffer = self._puffer[:n], self._puffer[n:]
        return raus

    def empfangen(self) -> bytes | None:
        """Die Nutzdaten des naechsten Daten-Rahmens. None: Ende.

        Ping wird beantwortet, Pong uebergangen. Ein Rahmen, der in
        Stuecken kommt (Fortsetzung), wird Stueck fuer Stueck
        weitergegeben - fuer einen Bytestrom ist das dasselbe."""
        while True:
            try:
                b1, b2 = self._lesen(2)
                art = b1 & 0x0F
                n = b2 & 0x7F
                if n == 126:
                    n = struct.unpack(">H", self._lesen(2))[0]
                elif n == 127:
                    n = struct.unpack(">Q", self._lesen(8))[0]
                maske = self._lesen(4) if b2 & 0x80 else None
                daten = self._lesen(n) if n else b""
            except (EOFError, OSError, ValueError):
                return None
            if maske is not None:
                daten = _maskieren(daten, maske)
            if art in (0x0, 0x1, 0x2):
                if daten:
                    return daten
                continue
            if art == 0x8:                       # Schluss
                try:
                    self.senden(daten[:2], 0x8)
                except OSError:
                    pass
                return None
            if art == 0x9:                       # Ping
                try:
                    self.senden(daten, 0xA)
                except OSError:
                    return None

    def schliessen(self) -> None:
        if self.zu:
            return
        self.zu = True
        try:
            self.senden(struct.pack(">H", 1000), 0x8)
        except OSError:
            pass
        try:
            self.sock.close()
        except OSError:
            pass


# ══════════════════════════════════════════════════════════════════
# Der Zugang: wie online.Zugang, nur ohne cloudflared
# ══════════════════════════════════════════════════════════════════

class WsZugang:
    """Gleiche Schnittstelle wie online.Zugang: `adresse`, `bereit`,
    `fehler`, `schritt()`, `schliessen()`.

    `ziel` und `tls` nur fuer die Pruefungen: statt Cloudflare ein Server
    auf diesem Rechner, ohne TLS."""

    def __init__(self, code: str, ziel=None, tls=True) -> None:
        from .online import host
        self.code = code
        self.port = 0
        self.bereit = False
        self.fehler = ""
        self._name = host(code)
        self._ziel = ziel or (self._name, 443)
        self._tls = tls
        self._vorrat: WebSocket | None = None    # der erste Weg, schon offen
        self._offen: list = []
        self._lauscher: socket.socket | None = None
        self._zu = False
        self._sperre = threading.Lock()
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.bind(("127.0.0.1", 0))
            s.listen(2)
            # Mit Frist, damit der Faden beim Schliessen aufwacht: ein
            # blockierendes accept() endet nicht ueberall, wenn ein anderer
            # Faden die Steckdose schliesst.
            s.settimeout(0.25)
            self.port = s.getsockname()[1]
            self._lauscher = s
        except OSError as e:
            self.fehler = "KEIN PORT FREI: %s" % str(e).upper()[:30]
            return
        threading.Thread(target=self._vorab, daemon=True).start()

    @property
    def adresse(self) -> str:
        return "127.0.0.1:%d" % self.port

    def _verbinden(self) -> WebSocket:
        adresse, port = self._ziel
        return WebSocket.verbinden(adresse, port, self._tls, name=self._name)

    def _vorab(self) -> None:
        """Einmal durchverbinden, bevor das Spiel anklopft - so steht ein
        falscher Code sofort da, und das Spiel wartet nicht umsonst."""
        try:
            ws = self._verbinden()
        except HandschlagFehler as e:
            self.fehler = str(e)
            return
        with self._sperre:
            if self._zu:
                ws.schliessen()
                return
            self._vorrat = ws
        self.bereit = True
        self._annehmen()

    def _annehmen(self) -> None:
        while not self._zu:
            lauscher = self._lauscher
            if lauscher is None:
                return
            try:
                lokal, _ = lauscher.accept()
            except socket.timeout:
                continue
            except OSError:
                return
            lokal.settimeout(None)
            with self._sperre:
                ws, self._vorrat = self._vorrat, None
            if ws is None:
                # Eine zweite Verbindung (das Spiel verbindet neu): ein
                # neuer Weg, wie bei cloudflared.
                try:
                    ws = self._verbinden()
                except HandschlagFehler as e:
                    self.fehler = str(e)
                    lokal.close()
                    continue
            self._paar(lokal, ws)

    def _paar(self, lokal, ws: WebSocket) -> None:
        try:
            lokal.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        except OSError:
            pass
        with self._sperre:
            self._offen.append((lokal, ws))

        def hin():
            # Spiel -> Cloudflare. Ein Rahmen je Lesen, wie cloudflared.
            try:
                while True:
                    daten = lokal.recv(O["ws_block"])
                    if not daten:
                        break
                    ws.senden(daten)
            except OSError:
                pass
            ws.schliessen()

        def her():
            # Cloudflare -> Spiel.
            try:
                while True:
                    daten = ws.empfangen()
                    if daten is None:
                        break
                    lokal.sendall(daten)
            except OSError:
                pass
            try:
                lokal.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            lokal.close()

        threading.Thread(target=hin, daemon=True).start()
        threading.Thread(target=her, daemon=True).start()

    def schritt(self) -> None:
        """Wie bei online.Zugang einmal je Bild. Hier rechnen die Faeden;
        es gibt nichts abzuholen."""

    def schliessen(self) -> None:
        with self._sperre:
            self._zu = True
            vorrat, self._vorrat = self._vorrat, None
            offen, self._offen = self._offen, []
        if vorrat is not None:
            vorrat.schliessen()
        for lokal, ws in offen:
            ws.schliessen()
            try:
                lokal.close()
            except OSError:
                pass
        if self._lauscher is not None:
            try:
                self._lauscher.close()
            except OSError:
                pass
            self._lauscher = None
        self.bereit = False


def warten(zugang, sekunden: float) -> bool:
    """Fuer die Pruefungen: bis bereit oder Fehler."""
    ende = time.monotonic() + sekunden
    while time.monotonic() < ende and not zugang.bereit and not zugang.fehler:
        time.sleep(0.01)
    return zugang.bereit
