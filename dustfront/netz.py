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
        # Weltmeldungen als Aenderungen (seit 0.34.102, siehe _welt_senden):
        # beim Gastgeber, was dieser Gast zuletzt bekommen hat; beim Gast,
        # was er zuletzt zusammengesetzt hat.
        self._basis = None             # die letzte volle Weltmeldung
        self._seit_voll = 0            # Meldungen seit der letzten vollen
        self._wirkung_rest: list = []  # Ereignisse ausgelassener Meldungen
        self.ausgelassen = 0           # nur zum Nachsehen
        # Quittungen (seit 0.34.102): der Gastgeber nummeriert seine
        # Weltmeldungen ("q"), der Gast sagt in jeder Eingabe, welche er
        # zuletzt hatte ("wq"). So weiss der Gastgeber, wie viele noch
        # unterwegs sind - egal, wie gross die Puffer des Systems sind.
        self._welt_nr = 0              # Gastgeber: so viele geschickt
        self._bestaetigt = -1          # Gastgeber: so weit hat der Gast sie
        self._ausgelassen_folge = 0    # Gastgeber: so viele in Folge nicht geschickt
        self._welt_q = -1              # Gast: die letzte, die ankam
        self.gesendet_bytes = 0        # nur zum Nachsehen

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
        if nachricht.get("t") == "welt" and K.NETZ["welt_aenderungen"]:
            nachricht = self._welt_senden(nachricht)
            if nachricht is None:
                return self.spuelen()            # diesmal ausgelassen
        elif nachricht.get("t") == "ein" and self._welt_q >= 0:
            nachricht = dict(nachricht, wq=self._welt_q)
        try:
            roh = (json.dumps(nachricht, separators=(",", ":")) + "\n").encode()
        except (TypeError, ValueError):
            return False
        self.gesendet_bytes += len(roh)
        self._raus.append(roh)
        self._schlange_kuerzen()
        return self.spuelen()

    # ---- Weltmeldungen: nur, was sich geaendert hat (seit 0.34.102) -----
    #
    # Gemessen in SCHLACHT mit 24 Kaempfern: 18 KB je Weltmeldung, 60 je
    # Sekunde, gut 1 MB/s je Gast - und von 1512 Feldern der Spieler waren
    # 1484 dieselben wie in der Meldung davor. Auf langsamem Internet staute
    # sich das, bis der Gast in der Lobby landete.
    #
    # Darum schickt die Leitung jedem Gast nur, was sich seit seiner letzten
    # Meldung geaendert hat, und alle `voll_alle` Meldungen einmal alles.
    # Der Gast setzt in seiner Leitung (_welt_zusammensetzen) wieder die
    # volle Meldung zusammen - das Spiel auf beiden Seiten merkt davon
    # nichts. TCP verliert nichts und bringt alles in Reihenfolge; die
    # einzige Stelle, an der eine Zeile wegfallen kann, ist _schlange_kuerzen,
    # und die verlangt danach eine volle Meldung.
    #
    # Gegendruck: liegt fuer diesen Gast noch zu viel ungesendet in der
    # Schlange, bekommt er diese Meldung nicht - die naechste sagt den
    # Stand ohnehin richtig. Nur die Ereignisse ("wirkung": Explosionen,
    # Klaenge) sind einmalig; sie wandern in die naechste Meldung.

    def _ungesendet(self) -> int:
        return sum(len(z) for z in self._raus)

    def _welt_senden(self, nachricht: dict):
        """Die Weltmeldung fuer diesen Gast: als Aenderung, voll, oder
        None (ausgelassen, weil die Leitung nicht nachkommt)."""
        n = K.NETZ
        wirkung = nachricht.get("wirkung") or []
        unterwegs = self._welt_nr - self._bestaetigt if self._bestaetigt >= 0 else 0
        stau = ((self._raus and self._ungesendet() > n["welt_stau_bytes"])
                or unterwegs > n["unterwegs_hoechstens"])
        # Hoechstens so viele in Folge auslassen: kommen keine Quittungen
        # mehr (der Gast haengt), geht trotzdem ab und zu eine hinaus.
        if stau and self._ausgelassen_folge < n["auslassen_hoechstens"]:
            self._ausgelassen_folge += 1
            self.ausgelassen += 1
            if wirkung:
                self._wirkung_rest.extend(wirkung)
                del self._wirkung_rest[:-n["wirkung_hoechstens"]]
            return None
        self._ausgelassen_folge = 0
        if self._wirkung_rest:
            wirkung = self._wirkung_rest + list(wirkung)
            self._wirkung_rest = []
        self._welt_nr += 1
        voll = dict(nachricht)
        voll["wirkung"] = wirkung
        voll["q"] = self._welt_nr
        basis = self._basis
        self._seit_voll += 1
        self._basis = voll
        if basis is None or self._seit_voll >= n["voll_alle"]:
            self._seit_voll = 0
            return voll
        return welt_aenderung(basis, voll)

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
            # Eine Eingabezeile mit Tastendruecken darf nicht weg. "ein"
            # traegt zweierlei: den gehaltenen Zustand (Richtung, Ziel,
            # Feuer), den die naechste Zeile ohnehin richtig sagt - und
            # einzelne Druecke wie Nachladen, Medkit oder Dash, die es
            # genau einmal gibt. Wirft man die Zeile weg, ist der Druck
            # verloren: man drueckt Dash, und nichts passiert.
            einmalig = (b'"knoepfe":[]' not in zeile or b'"waffe":-1' not in zeile)
            if zeile.startswith(b'{"t":"ein"') and einmalig:
                behalten.append(zeile)
                continue
            if i > 0 and zeile.startswith(b'{"t":"welt"') and K.NETZ["welt_aenderungen"]:
                # Aenderungen bauen aufeinander auf: faellt eine weg, sind
                # alle danach falsch. Also alle weg, und die naechste
                # Meldung kommt voll (seit 0.34.102).
                self.verworfen += 1
                self._basis = None
                continue
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
        fertig = []
        if not self.offen:
            # spuelen kann die Leitung schliessen (Rueckstand zu gross, die
            # Gegenstelle liest nicht mehr). Dann gibt es keinen Socket mehr,
            # und select darauf warf ValueError - beim Gastgeber mitten im
            # Gefecht, wenn ein Gast haengt (gefunden 0.34.100).
            return []
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
            # Fertige Zeilen gleich herausnehmen und erst den Rest pruefen
            # (seit 0.34.102). Vorher galt die Grenze fuer alles, was auf
            # einmal ankam: nach einem Haenger auf langsamem Internet kamen
            # zwanzig Weltmeldungen zu je 18 KB in einem Schwall, die Leitung
            # galt als kaputt ("Nachricht zu lang") - und der Gast landete
            # in der Lobby.
            if b"\n" in self._rest:
                *zeilen, self._rest = self._rest.split(b"\n")
                fertig.extend(zeilen)
            if len(self._rest) > K.NETZ["hoechstzeile"]:
                # Schutz davor, dass eine kaputte Gegenstelle uns den
                # Speicher vollschreibt: eine einzelne Zeile ohne Ende.
                self.schliessen("Nachricht zu lang")
                break
        for zeile in fertig:
            if not zeile.strip():
                continue
            try:
                nachricht = json.loads(zeile.decode("utf-8", "replace"))
            except (ValueError, UnicodeDecodeError):
                continue          # eine kaputte Zeile wirft niemanden raus
            if isinstance(nachricht, dict) and nachricht.get("t") == "welt":
                nachricht = self._welt_zusammensetzen(nachricht)
                if nachricht is None:
                    continue      # eine Aenderung ohne Grundlage: auf die volle warten
                try:
                    self._welt_q = int(nachricht.get("q", self._welt_q))
                except (TypeError, ValueError):
                    pass
            elif isinstance(nachricht, dict) and "wq" in nachricht:
                try:
                    self._bestaetigt = max(self._bestaetigt, min(self._welt_nr, int(nachricht["wq"])))
                except (TypeError, ValueError):
                    pass
            raus.append(nachricht)
        return raus

    def _welt_zusammensetzen(self, nachricht: dict):
        """Beim Gast: aus einer Aenderung wieder die volle Weltmeldung."""
        if "dl" not in nachricht:
            self._basis = nachricht
            return nachricht
        if self._basis is None:
            return None
        voll = welt_anwenden(self._basis, nachricht)
        self._basis = voll
        return voll


# ══════════════════════════════════════════════════════════════════
# Gastgeber
# ══════════════════════════════════════════════════════════════════

class Gastgeber:
    """Nimmt Verbindungen an und haelt sie. Rechnen tut die Spielszene."""

    def __init__(self, port: int | None = None, online: bool = False,
                 nur_lokal: bool = False) -> None:
        # online=True heisst nur eines: versuche, den Router zu ueberreden,
        # den Port von aussen durchzulassen. Am Spiel selbst aendert es
        # nichts - es ist dieselbe Leitung, nur von weiter her.
        self.online = bool(online)
        self.freigabe = None
        self.port = int(port or K.NETZ["port"])
        self.leitungen: dict[int, Leitung] = {}
        self.naechste_id = 1
        # nur_lokal (seit 0.34.13): nur auf 127.0.0.1 lauschen. Dorthin
        # verbindet sich der Tunnel (online.py), und eine Steckdose, die
        # nur dort lauscht, loest unter Windows keine Firewall-Abfrage aus.
        # Im LAN sieht einen dann niemand - das ist der Schalter IM LAN
        # SICHTBAR (lan_setzen).
        self.nur_lokal = bool(nur_lokal)
        self.tunnel = None
        self.sock = self._lauschen()
        if self.online:
            from .upnp import Freigabe
            self.freigabe = Freigabe(self.port, eigene_adresse())
            self.freigabe.oeffnen()

    def _lauschen(self) -> socket.socket:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock = sock
        if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
            # GRUND: Unter Windows heisst SO_REUSEADDR etwas anderes als
            # ueberall sonst - ein zweites Programm darf sich dann auf
            # einen Port setzen, der schon belegt ist. Seit jeder in
            # seiner eigenen Lobby startet, sind zwei Fenster auf einem
            # Rechner normal; das zweite muss merken, dass der Port
            # besetzt ist, und den naechsten nehmen (sitzung.py).
            self.sock.setsockopt(socket.SOL_SOCKET,
                                 socket.SO_EXCLUSIVEADDRUSE, 1)
        else:
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            self.sock.bind(("127.0.0.1" if self.nur_lokal else "", self.port))
        except OSError:
            self.sock.close()
            raise
        self.sock.listen(K.NETZ["warteschlange"])
        self.sock.setblocking(False)
        return sock

    def lan_setzen(self, an: bool) -> bool:
        """Im LAN sichtbar oder nur fuer den Tunnel, im laufenden Spiel.

        Nur die lauschende Steckdose wird getauscht, auf demselben Port -
        wer schon drin ist, hat seine eigene Leitung und merkt nichts.
        Gibt zurueck, ob es geklappt hat; sonst bleibt es, wie es war.
        """
        if an == (not self.nur_lokal):
            return True
        alt, alt_lokal = self.sock, self.nur_lokal
        try:
            alt.close()
        except OSError:
            pass
        self.nur_lokal = not an
        try:
            self._lauschen()
            return True
        except OSError:
            self.nur_lokal = alt_lokal
            try:
                self._lauschen()
            except OSError:
                pass
            return False

    def tunnel_setzen(self, an: bool) -> None:
        """Den Online-Code an- oder abschalten (online.py)."""
        if an and self.tunnel is None:
            from .online import Tunnel
            self.tunnel = Tunnel(self.port)
        elif not an and self.tunnel is not None:
            self.tunnel.schliessen()
            self.tunnel = None

    @property
    def code(self) -> str:
        """Der Online-Code, sobald der Tunnel steht, sonst leer."""
        t = self.tunnel
        return t.code if t is not None and t.bereit else ""

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
        if self.tunnel is not None:
            self.tunnel.schritt()
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
            try:
                verbindung.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, K.NETZ["sendepuffer"])
            except OSError:
                pass
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

    def spuelen(self) -> None:
        """Was noch in den Schlangen liegt, jetzt hinaus - vor dem Schliessen,
        damit die letzte Nachricht (der Abbruch) noch ankommt."""
        for leitung in list(self.leitungen.values()):
            leitung.spuelen()

    def schliessen(self) -> None:
        for leitung in list(self.leitungen.values()):
            leitung.schliessen("Gastgeber beendet")
        self.leitungen.clear()
        try:
            self.sock.close()
        except OSError:
            pass
        self.tunnel_setzen(False)
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

    def __init__(self, wohin: str, zugang=None) -> None:
        wirt, port = adresse_lesen(wohin)
        self.fehler = ""
        self.leitung: Leitung | None = None
        # Ueber einen Online-Code (online.Zugang): der gehoert zur Leitung
        # und wird mit ihr geschlossen.
        self.zugang = zugang
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
        if self.zugang is not None:
            self.zugang.schritt()
        return self.leitung.holen() if self.leitung else []

    def schliessen(self) -> None:
        if self.leitung:
            self.leitung.schliessen("selbst beendet")
        if self.zugang is not None:
            self.zugang.schliessen()


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


# ══════════════════════════════════════════════════════════════════
# Weltmeldungen als Aenderungen (seit 0.34.102)
# ══════════════════════════════════════════════════════════════════
#
# Eine Aenderung traegt "dl": 1 und nur, was anders ist als in der Meldung
# davor. Oben: jeder Schluessel, dessen Wert sich geaendert hat ("_weg":
# die, die es nicht mehr gibt). "wirkung" gilt immer nur fuer diese eine
# Meldung - fehlt sie, ist sie leer. Die Spieler einzeln, nach Nummer "i":
# nur die geaenderten Felder ("_x": weggefallene), und nur, wer sich
# geaendert hat; stimmt die Reihenfolge nicht mehr, steht sie in "_sp".

def welt_aenderung(alt: dict, neu: dict) -> dict:
    d = {"t": "welt", "dl": 1}
    for k, v in neu.items():
        if k in ("t", "spieler", "wirkung"):
            continue
        a = alt.get(k, _FEHLT)
        if a != v:
            d[k] = _teil_aenderung(a, v)
    weg = [k for k in alt if k not in neu and k not in ("t", "dl")]
    if weg:
        d["_weg"] = weg
    if neu.get("wirkung"):
        d["wirkung"] = neu["wirkung"]
    alt_sp = alt.get("spieler") or []
    neu_sp = neu.get("spieler") or []
    if not isinstance(alt_sp, list) or not isinstance(neu_sp, list) or not all(
            isinstance(e, dict) and "i" in e for e in alt_sp + neu_sp):
        if alt_sp != neu_sp:
            d["spieler"] = neu_sp
        return d
    vorher = {e["i"]: e for e in alt_sp}
    teile = []
    for e in neu_sp:
        b = vorher.get(e["i"])
        if b is None:
            teile.append(e)
            continue
        geaendert = {k: v for k, v in e.items() if b.get(k, _FEHLT) != v}
        x = [k for k in b if k not in e]
        if x:
            geaendert["_x"] = x
        if geaendert:
            geaendert["i"] = e["i"]
            teile.append(geaendert)
    if teile:
        d["spieler"] = teile
    reihe = [e["i"] for e in neu_sp]
    if reihe != [e["i"] for e in alt_sp]:
        d["_sp"] = reihe
    return d


def welt_anwenden(alt: dict, d: dict) -> dict:
    voll = {k: v for k, v in alt.items() if k not in d.get("_weg", ())}
    for k, v in d.items():
        if k in ("dl", "_weg", "_sp", "spieler"):
            continue
        voll[k] = _teil_anwenden(alt.get(k), v)
    if "wirkung" not in d:
        voll["wirkung"] = []
    alt_sp = alt.get("spieler") or []
    teile = d.get("spieler")
    if "_sp" not in d and teile is not None and not any(
            isinstance(e, dict) and "i" in e for e in teile):
        voll["spieler"] = teile                     # als Ganzes geschickt
        return voll
    eintraege = {e["i"]: e for e in alt_sp if isinstance(e, dict) and "i" in e}
    for e in teile or ():
        if not isinstance(e, dict) or "i" not in e:
            continue
        b = eintraege.get(e["i"])
        if b is None or "_x" not in e and len(e) >= len(b) and set(b) <= set(e):
            neu_e = {k: v for k, v in e.items() if k != "_x"}
        else:
            neu_e = dict(b)
            neu_e.update(e)
            for k in e.get("_x", ()):
                neu_e.pop(k, None)
            neu_e.pop("_x", None)
        eintraege[e["i"]] = neu_e
    reihe = d.get("_sp")
    if reihe is None:
        reihe = [e["i"] for e in alt_sp if isinstance(e, dict) and "i" in e]
    voll["spieler"] = [eintraege[i] for i in reihe if i in eintraege]
    return voll


def _teil_aenderung(alt, neu):
    """Ein einzelner Wert: als Ganzes, oder - wenn das kuerzer ist - nur
    die geaenderten Zeilen einer Liste ({"~": [[Stelle, Zeile], ...]}) bzw.
    die geaenderten Schluessel eines Woerterbuchs ({"~d": {...}, "~x": [...]}).
    Die Fahrzeuge zum Beispiel: meist faehrt einer, die anderen stehen."""
    if (isinstance(alt, list) and isinstance(neu, list) and len(alt) == len(neu)
            and len(neu) > 1):
        zeilen = [[i, z] for i, (a, z) in enumerate(zip(alt, neu)) if a != z]
        if len(zeilen) * 2 <= len(neu):
            return {"~": zeilen}
        return neu
    if isinstance(alt, dict) and isinstance(neu, dict) and "~" not in neu and "~d" not in neu:
        teile = {k: _teil_aenderung(alt.get(k, _FEHLT), v) for k, v in neu.items()
                 if alt.get(k, _FEHLT) != v}
        weg = [k for k in alt if k not in neu]
        aus = {"~d": teile}
        if weg:
            aus["~x"] = weg
        return aus
    return neu


def _teil_anwenden(alt, wert):
    if isinstance(wert, dict) and "~" in wert and isinstance(alt, list):
        neu = list(alt)
        for i, z in wert["~"]:
            if 0 <= i < len(neu):
                neu[i] = z
        return neu
    if isinstance(wert, dict) and "~d" in wert and isinstance(alt, dict):
        neu = {k: v for k, v in alt.items() if k not in wert.get("~x", ())}
        for k, v in wert["~d"].items():
            neu[k] = _teil_anwenden(alt.get(k), v)
        return neu
    return wert


class _Fehlt:
    """Ein Wert, den es nicht gibt (anders als None, das es geben kann)."""


_FEHLT = _Fehlt()
