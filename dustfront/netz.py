"""
DUSTFRONT - Netz
================

LAN-Mehrspieler, so einfach wie moeglich und so ehrlich wie noetig.

**Ein Rechner rechnet, alle anderen schauen zu.** Der Gastgeber simuliert
die ganze Welt. Die Gaeste schicken nur, was sie druecken, und bekommen
zurueck, wo alles steht. Das heisst: kein Streit darueber, wer getroffen
hat, und niemand kann durch eine geaenderte Datei schummeln. Der Preis ist
eine Verzoegerung von einem Hin- und Rueckweg - im LAN sind das unter zwei
Millisekunden, also unsichtbar.

**Keine Threads.** Die Steckdosen stehen auf nicht-blockierend, und einmal
je Bild wird nachgesehen, was angekommen ist. Ein Spiel hat ohnehin eine
Schleife; die zweite Schleife eines Threads waere nur eine Quelle fuer
Fehler, die man nicht nachstellen kann.

**Protokoll: eine JSON-Zeile je Nachricht.** Lesbar, mit blossem Auge zu
pruefen, und der Zeilenumbruch loest gleich das Problem, wo eine Nachricht
aufhoert. Das ist nicht das sparsamste Format, aber bei einer Handvoll
Spielern im LAN ist Bandbreite kein Engpass.

Nachrichten vom Gast zum Gastgeber:

    {"t": "hallo", "name": "MEISTER"}
    {"t": "ein", "will": [x, y], "ziel": [x, y], "feuert": true, ...}

Nachrichten vom Gastgeber zum Gast:

    {"t": "willkommen", "id": 2, "modus": "huegel", "ende_art": "zeit", ...}
    {"t": "welt", "spieler": [...], "schuesse": [...], "rest": 287.4, ...}
    {"t": "ende", "liste": [...], "sieger": 0, "teampunkte": [3, 1]}

Jedes Feld einzeln erklaert steht in docs/MEHRSPIELER.md, Abschnitt 4.
"""

from __future__ import annotations

import json
import select
import socket

from . import config as K


# ══════════════════════════════════════════════════════════════════
# Eine Verbindung, zeilenweise
# ══════════════════════════════════════════════════════════════════

class Leitung:
    """Eine TCP-Verbindung, die JSON-Zeilen sendet und empfaengt.

    Haelt einen Puffer, weil TCP keine Nachrichtengrenzen kennt: was als
    eine Zeile losgeschickt wurde, kann in drei Stuecken ankommen, und drei
    Zeilen koennen in einem Stueck ankommen. Beides kommt im LAN wirklich
    vor, sobald es schnell geht.
    """

    def __init__(self, sock: socket.socket) -> None:
        self.sock = sock
        self.sock.setblocking(False)
        self.sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        self._rest = b""
        self._raus: list[bytes] = []   # was noch hinaus will, Zeile fuer Zeile
        self.offen = True
        self.grund = ""
        self.verworfen = 0             # ueberholte Zeilen, nur zum Nachsehen

    def schliessen(self, grund: str = "") -> None:
        if self.offen:
            self.offen = False
            self.grund = grund or self.grund
            try:
                self.sock.close()
            except OSError:
                pass

    def senden(self, nachricht: dict) -> bool:
        """Eine Nachricht rausschicken. False, wenn die Leitung tot ist.

        Hier stand `sendall` auf einer **nicht-blockierenden** Steckdose,
        und das ist ein stiller Widerspruch. Ist der Sendepuffer des Kerns
        voll - und das ist er, sobald jemand mit schwacher Verbindung
        mitspielt oder die Karte voller Wesen ist -, dann schreibt
        `sendall` einen Teil der Zeile und wirft danach BlockingIOError.
        Der halbe Satz ist dann schon unterwegs, der Rest fehlt, und die
        Leitung wurde im Fehlerzweig kurzerhand zugemacht. Aus Sicht des
        Spielers: die Welt stand fuer einen Moment, Granaten sprangen oder
        blieben ganz aus, und manchmal flog jemand aus der Runde.

        Jetzt wird gepuffert. Was nicht durchgeht, bleibt liegen und geht
        beim naechsten Versuch raus; die Zeilengrenze bleibt dabei immer
        heil, weil nur ganze Zeilen in die Schlange kommen und ein
        angefangener Rest vorn wieder eingesetzt wird.
        """
        if not self.offen:
            return False
        try:
            roh = (json.dumps(nachricht, separators=(",", ":")) + "\n").encode()
        except (TypeError, ValueError):
            return False
        self._raus.append(roh)
        self._schlange_kuerzen()
        return self.spuelen()

    def _schlange_kuerzen(self) -> None:
        """Staut sich zu viel, fliegt das Ueberholte raus - nicht die Leitung.

        Eine Weltmeldung von vor zwei Zehnteln ist wertlos: die naechste
        sagt dasselbe, nur richtig. Sie noch zu schicken kostet nur Zeit
        und schiebt den Rueckstand weiter vor sich her. Andere Nachrichten
        - Willkommen, Ende, Abgelehnt - gibt es genau einmal und bleiben
        immer stehen.
        """
        grenze = K.NETZ["stau_zeilen"]
        if len(self._raus) <= grenze:
            return
        behalten = []
        # Die vorderste Zeile kann schon angefangen gesendet sein und
        # bleibt darum in jedem Fall stehen.
        for i, zeile in enumerate(self._raus):
            if i > 0 and (zeile.startswith(b'{"t":"welt"')
                          or zeile.startswith(b'{"t":"ein"')):
                if len(behalten) + (len(self._raus) - i) > grenze:
                    self.verworfen += 1
                    continue
            behalten.append(zeile)
        self._raus = behalten

    def spuelen(self) -> bool:
        """Schickt so viel aus der Schlange, wie gerade durchgeht."""
        if not self.offen:
            return False
        while self._raus:
            try:
                geschickt = self.sock.send(self._raus[0])
            except (BlockingIOError, InterruptedError):
                return True       # Puffer voll, der Rest wartet auf spaeter
            except OSError as fehler:
                self.schliessen(str(fehler))
                return False
            if geschickt <= 0:
                return True
            if geschickt < len(self._raus[0]):
                self._raus[0] = self._raus[0][geschickt:]
                return True
            self._raus.pop(0)
        return True

    def holen(self) -> list[dict]:
        """Alles, was inzwischen angekommen ist. Blockiert nie.

        Nebenbei geht hier los, was noch in der Sendeschlange liegt.
        Beide Seiten fragen einmal je Bild nach Post, also ist das die
        Stelle, an der ein Rueckstand zuverlaessig wieder abfliesst -
        auch dann, wenn gerade nichts Neues zu schicken ist.
        """
        if not self.offen:
            return []
        self.spuelen()
        raus = []
        while True:
            bereit, _, _ = select.select([self.sock], [], [], 0)
            if not bereit:
                break
            try:
                stueck = self.sock.recv(K.NETZ["puffer"])
            except BlockingIOError:
                break
            except OSError as fehler:
                self.schliessen(str(fehler))
                break
            if not stueck:
                self.schliessen("Gegenstelle hat aufgelegt")
                break
            self._rest += stueck
            if len(self._rest) > K.NETZ["hoechstzeile"]:
                # Schutz davor, dass eine kaputte Gegenstelle uns den
                # Speicher vollschreibt.
                self.schliessen("Nachricht zu lang")
                break
        while b"\n" in self._rest:
            zeile, self._rest = self._rest.split(b"\n", 1)
            if not zeile.strip():
                continue
            try:
                raus.append(json.loads(zeile.decode("utf-8", "replace")))
            except (ValueError, UnicodeDecodeError):
                continue          # eine kaputte Zeile wirft niemanden raus
        return raus


# ══════════════════════════════════════════════════════════════════
# Gastgeber
# ══════════════════════════════════════════════════════════════════

class Gastgeber:
    """Nimmt Verbindungen an und haelt sie. Rechnen tut die Spielszene."""

    def __init__(self, port: int | None = None, online: bool = False) -> None:
        # online=True heisst nur eines: versuche, den Router zu ueberreden,
        # den Port von aussen durchzulassen. Am Spiel selbst aendert es
        # nichts - es ist dieselbe Leitung, nur von weiter her.
        self.online = bool(online)
        self.freigabe = None
        self.port = int(port or K.NETZ["port"])
        self.leitungen: dict[int, Leitung] = {}
        self.naechste_id = 1
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind(("", self.port))
        self.sock.listen(K.NETZ["warteschlange"])
        self.sock.setblocking(False)
        if self.online:
            from .upnp import Freigabe
            self.freigabe = Freigabe(self.port, eigene_adresse())
            self.freigabe.oeffnen()

    @property
    def adresse(self) -> str:
        """Die Adresse, die man den Mitspielern im eigenen Netz ansagt."""
        return "%s:%d" % (eigene_adresse(), self.port)

    @property
    def aussen(self) -> str:
        """Die Adresse von ausserhalb, falls der Router mitgespielt hat."""
        if self.freigabe is not None and self.freigabe.offen:
            return "%s:%d" % (self.freigabe.aussen or "?", self.port)
        return ""

    def annehmen(self) -> list[int]:
        """Neue Gaeste hereinlassen. Gibt deren Nummern zurueck."""
        neu = []
        while True:
            bereit, _, _ = select.select([self.sock], [], [], 0)
            if not bereit:
                break
            try:
                verbindung, _ = self.sock.accept()
            except OSError:
                break
            if len(self.leitungen) >= K.NETZ["hoechstens"]:
                try:
                    verbindung.close()
                except OSError:
                    pass
                continue
            nummer = self.naechste_id
            self.naechste_id += 1
            self.leitungen[nummer] = Leitung(verbindung)
            neu.append(nummer)
        return neu

    def holen(self) -> list[tuple[int, dict]]:
        """Alle Nachrichten aller Gaeste, mit ihrer Nummer davor."""
        raus = []
        for nummer, leitung in list(self.leitungen.items()):
            for nachricht in leitung.holen():
                raus.append((nummer, nachricht))
        return raus

    def gegangen(self) -> list[int]:
        """Nummern der Gaeste, deren Leitung tot ist. Raeumt sie gleich weg."""
        weg = [n for n, l in self.leitungen.items() if not l.offen]
        for n in weg:
            self.leitungen.pop(n, None)
        return weg

    def an_alle(self, nachricht: dict) -> None:
        for leitung in list(self.leitungen.values()):
            leitung.senden(nachricht)

    def an_einen(self, nummer: int, nachricht: dict) -> None:
        leitung = self.leitungen.get(nummer)
        if leitung is not None:
            leitung.senden(nachricht)

    def schliessen(self) -> None:
        for leitung in list(self.leitungen.values()):
            leitung.schliessen("Gastgeber beendet")
        self.leitungen.clear()
        try:
            self.sock.close()
        except OSError:
            pass
        if self.freigabe is not None:
            # Die Tuer im Router wieder zumachen. Wer das vergisst,
            # hinterlaesst eine offene Stelle, die bis zum naechsten
            # Neustart des Routers offen bleibt.
            self.freigabe.zumachen()


# ══════════════════════════════════════════════════════════════════
# Gast
# ══════════════════════════════════════════════════════════════════

class Gast:
    """Verbindet sich mit einem Gastgeber."""

    def __init__(self, wohin: str) -> None:
        wirt, port = adresse_lesen(wohin)
        self.fehler = ""
        self.leitung: Leitung | None = None
        try:
            sock = socket.create_connection((wirt, port),
                                            timeout=K.NETZ["wartezeit"])
        except OSError as grund:
            self.fehler = "%s" % grund
            return
        self.leitung = Leitung(sock)

    @property
    def offen(self) -> bool:
        return self.leitung is not None and self.leitung.offen

    def senden(self, nachricht: dict) -> bool:
        return self.leitung.senden(nachricht) if self.leitung else False

    def holen(self) -> list[dict]:
        return self.leitung.holen() if self.leitung else []

    def schliessen(self) -> None:
        if self.leitung:
            self.leitung.schliessen("selbst beendet")


# ══════════════════════════════════════════════════════════════════
# Kleine Helfer
# ══════════════════════════════════════════════════════════════════

def adresse_lesen(text: str) -> tuple[str, int]:
    """"192.168.1.7:50000" oder "192.168.1.7" in Wirt und Port zerlegen."""
    text = (text or "").strip()
    if text.count(":") == 1:
        wirt, _, hinten = text.partition(":")
        try:
            return (wirt.strip() or "127.0.0.1"), int(hinten)
        except ValueError:
            pass
    return (text or "127.0.0.1"), int(K.NETZ["port"])


def eigene_adresse() -> str:
    """Die eigene Adresse im LAN, so gut sie sich ermitteln laesst.

    Der Umweg ueber eine Probeverbindung ist Absicht: gethostbyname liefert
    auf vielen Rechnern nur 127.0.0.1 zurueck, und damit kann kein
    Mitspieler etwas anfangen. Gesendet wird dabei nichts, UDP braucht
    keinen Verbindungsaufbau - es geht nur darum, welche Karte das System
    fuer den Weg nach draussen waehlen wuerde.
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.connect((K.NETZ["probe_ziel"], 9))
        return sock.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        sock.close()


def passwort_saeubern(wort: str) -> str:
    """Kuerzt und saeubert ein Kennwort.

    Nur Zeichen, die sich auf jeder Tastatur tippen und in dieser Schrift
    anzeigen lassen. Ein Kennwort, das man nicht vorlesen kann, ist im
    Wohnzimmer nutzlos.
    """
    erlaubt = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_"
    sauber = "".join(c for c in (wort or "").upper() if c in erlaubt)
    return sauber[:K.NETZ["passwortlaenge"]]


def name_saeubern(name: str) -> str:
    """Macht aus einer Eingabe einen Namen, der ueberall anzeigbar ist.

    Die 5x7-Schrift kennt nur Grossbuchstaben, Ziffern und ein paar
    Zeichen. Alles andere wird ersetzt, statt als Fragezeichen im Bild zu
    landen.
    """
    erlaubt = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_"
    sauber = "".join(c for c in (name or "").upper() if c in erlaubt)
    return (sauber[:K.NETZ["namenslaenge"]] or "GAST")
