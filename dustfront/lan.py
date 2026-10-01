"""
DUSTFRONT - Lobbys im eigenen Netz finden
=========================================

Bis 0.31 musste ein Gast die Adresse des Gastgebers kennen und im Terminal
eintippen. Jetzt sitzt jeder in seiner eigenen Lobby, und die Lobbys der
anderen im selben Netz stehen in einer Liste.

**Wie sie sich finden.** Ueber UDP, ohne Server dazwischen:

* Jede offene Lobby hat einen `Ansager`. Er horcht auf einem festen Port
  (K.NETZ["such_port"]) und antwortet auf die Frage `DUSTFRONT?` mit einer
  JSON-Zeile: Name, Port, Version, wie viele schon drin sind.
* Wer sucht, hat einen `Sucher`. Er ruft die Frage als Rundruf ins Netz
  und sammelt die Antworten ein.

GRUND fuer Fragen statt Rufen: Ein Ansager, der von sich aus alle Sekunde
ins Netz ruft, rufte auch dann, wenn niemand sucht - auf jedem Rechner, der
das Spiel offen hat. So redet nur, wer gefragt wird, und nur der, der
gerade die Liste offen hat, fragt.

**Keine Threads**, wie in netz.py: beide Steckdosen sind nicht-blockierend,
und einmal je Bild wird nachgesehen.

Was ueber UDP kommt, kann jeder schicken. Darum wird jede Antwort
geprueft und gekuerzt, bevor sie in die Liste kommt, und beitreten heisst
weiterhin: eine ganz normale Verbindung zum Gastgeber, die dort genauso
geprueft wird wie jede andere (Version, Kennwort, Platz).
"""

from __future__ import annotations

import json
import random
import socket
import time

from . import config as K
from . import netz

FRAGE = b"DUSTFRONT?"


def _rundruf_ziele() -> list[str]:
    """Wohin die Frage geht.

    255.255.255.255 erreicht das eigene Netz, aber nicht auf jedem System:
    manche Windows-Rechner mit mehreren Netzkarten schicken diesen Rundruf
    nur auf einer hinaus, oft der falschen. Darum zusaetzlich der Rundruf
    des eigenen /24-Netzes (die haeufigste Heimnetzgroesse), und 127.0.0.1
    fuer eine zweite Lobby auf demselben Rechner.
    """
    ziele = ["255.255.255.255", "127.0.0.1"]
    eigen = netz.eigene_adresse()
    teile = eigen.split(".")
    if len(teile) == 4 and eigen != "127.0.0.1":
        ziele.append(".".join(teile[:3] + ["255"]))
    return ziele


class Ansager:
    """Beantwortet die Suchfrage fuer eine offene Lobby.

    `kennung` ist eine Zufallszahl je Lobby. Mit ihr erkennt der eigene
    Sucher die eigene Lobby wieder und zeigt sie nicht als fremde an.
    """

    def __init__(self, port: int | None = None) -> None:
        self.kennung = "%08x" % random.getrandbits(32)
        self.sock: socket.socket | None = None
        self.fehler = ""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            # GRUND: Mehrere Lobbys auf einem Rechner (zwei Fenster zum
            # Ausprobieren) muessen denselben Suchport teilen koennen. Fuer
            # UDP ist das gefahrlos: ein Rundruf kommt bei allen an.
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            if hasattr(socket, "SO_REUSEPORT"):
                try:
                    # macOS und BSD wollen dafuer zusaetzlich REUSEPORT.
                    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
                except OSError:
                    pass
            sock.bind(("", int(port or K.NETZ["such_port"])))
            sock.setblocking(False)
            self.sock = sock
        except OSError as grund:
            # Ohne Ansager ist die Lobby nur nicht zu finden - beitreten
            # ueber die Adresse geht weiterhin. Kein Grund, abzubrechen.
            self.fehler = str(grund)

    def schritt(self, auskunft) -> None:
        """Alle wartenden Fragen beantworten. `auskunft()` liefert das dict."""
        if self.sock is None:
            return
        antwort = None
        for _ in range(16):              # mehr als 16 je Bild ist kein Suchen
            try:
                daten, absender = self.sock.recvfrom(64)
            except (BlockingIOError, InterruptedError):
                break
            except OSError:
                break
            if daten.strip() != FRAGE:
                continue
            if antwort is None:
                d = dict(auskunft())
                d["kennung"] = self.kennung
                antwort = json.dumps(d, separators=(",", ":")).encode()[:1024]
            try:
                self.sock.sendto(antwort, absender)
            except OSError:
                pass

    def schliessen(self) -> None:
        if self.sock is not None:
            try:
                self.sock.close()
            except OSError:
                pass
            self.sock = None


def eintrag_pruefen(roh: bytes, wirt: str) -> dict | None:
    """Eine Antwort aus dem Netz lesen. Alles, was nicht passt, fliegt raus."""
    try:
        d = json.loads(roh.decode("utf-8", "replace"))
    except ValueError:
        return None
    if not isinstance(d, dict):
        return None
    try:
        port = int(d.get("port", 0))
        spieler = max(0, min(99, int(d.get("spieler", 0))))
        hoechstens = max(1, min(99, int(d.get("hoechstens", K.NETZ["hoechstens"]))))
    except (TypeError, ValueError):
        return None
    if not 1 <= port <= 65535:
        return None
    return {"name": netz.name_saeubern(str(d.get("name", ""))),
            "wirt": wirt, "port": port,
            "adresse": "%s:%d" % (wirt, port),
            "version": str(d.get("version", ""))[:16],
            "spieler": spieler, "hoechstens": hoechstens,
            "lobby": bool(d.get("lobby", False)),
            "modus": str(d.get("modus", ""))[:24].upper(),
            "karte": str(d.get("karte", ""))[:24].upper(),
            "passwort": bool(d.get("passwort", False)),
            "kennung": str(d.get("kennung", ""))[:16]}


class Sucher:
    """Fragt das Netz nach Lobbys und haelt die Liste aktuell."""

    def __init__(self, port: int | None = None, ohne: str = "") -> None:
        self.port = int(port or K.NETZ["such_port"])
        self.ohne = ohne               # Kennung der eigenen Lobby
        self.gefunden: dict[str, dict] = {}
        self._zuletzt: dict[str, float] = {}
        self._seit_frage = 1e9         # gleich beim ersten Schritt fragen
        self.sock: socket.socket | None = None
        self.fehler = ""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            sock.bind(("", 0))
            sock.setblocking(False)
            self.sock = sock
        except OSError as grund:
            self.fehler = str(grund)

    def fragen(self) -> None:
        if self.sock is None:
            return
        for ziel in _rundruf_ziele():
            try:
                self.sock.sendto(FRAGE, (ziel, self.port))
            except OSError:
                # Ein Netz ohne Rundruf (manche Firmennetze) wirft hier.
                # Die anderen Ziele werden trotzdem versucht.
                pass

    def schritt(self, dt: float) -> None:
        if self.sock is None:
            return
        self._seit_frage += dt
        if self._seit_frage >= K.NETZ["such_takt"]:
            self._seit_frage = 0.0
            self.fragen()
        jetzt = time.monotonic()
        for _ in range(64):
            try:
                daten, (wirt, _port) = self.sock.recvfrom(2048)
            except (BlockingIOError, InterruptedError):
                break
            except OSError:
                break
            e = eintrag_pruefen(daten, wirt)
            if e is None or (self.ohne and e["kennung"] == self.ohne):
                continue
            # GRUND fuer die Kennung als Schluessel: dieselbe Lobby
            # antwortet ueber 127.0.0.1 und ueber die Netzadresse, und
            # stuende sonst zweimal da. Gewinnt die Netzadresse - mit
            # 127.0.0.1 koennte nur derselbe Rechner etwas anfangen.
            schluessel = e["kennung"] or e["adresse"]
            alt = self.gefunden.get(schluessel)
            if alt is not None and e["wirt"].startswith("127.") \
                    and not alt["wirt"].startswith("127."):
                e = dict(e, wirt=alt["wirt"], adresse="%s:%d" % (alt["wirt"], e["port"]))
            self.gefunden[schluessel] = e
            self._zuletzt[schluessel] = jetzt
        for schluessel, wann in list(self._zuletzt.items()):
            if jetzt - wann > K.NETZ["such_vergessen"]:
                self._zuletzt.pop(schluessel, None)
                self.gefunden.pop(schluessel, None)

    def liste(self) -> list[dict]:
        """Nach Name sortiert, damit die Zeilen beim Auffrischen nicht springen."""
        return sorted(self.gefunden.values(),
                      key=lambda e: (e["name"], e["adresse"]))

    def schliessen(self) -> None:
        if self.sock is not None:
            try:
                self.sock.close()
            except OSError:
                pass
            self.sock = None
