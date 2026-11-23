"""
DUSTFRONT - Spielen ueber das Internet
======================================

Seit 0.34.13. Bis dahin ging es ueber das Internet nur, wenn der Router
den Port per UPnP freigab (upnp.py) oder jemand ihn von Hand freigab - und
jede eigene Lobby lauschte auf allen Netzkarten, wofuer Windows beim
ersten Start mit der Abfrage der Firewall kam.

**Wie es jetzt geht.** Niemand lauscht nach draussen. Beide Seiten bauen
nur ausgehende Verbindungen zu Cloudflare auf, und das reicht ohne jede
Einstellung durch jeden Router und jede Firewall:

    Gastgeber                         Cloudflare                     Gast
    Lobby lauscht auf 127.0.0.1  <-  cloudflared tunnel  ->  [Code]  <-  cloudflared access tcp
                                                                       lauscht auf 127.0.0.1  <-  Spiel

* Der Gastgeber startet `cloudflared tunnel --url tcp://127.0.0.1:PORT`.
  Cloudflare vergibt dafuer einen "Quick Tunnel" mit zufaelligem Namen
  aus vier englischen Woertern (etwa
  `thermal-underlying-providers-toe.trycloudflare.com`). Die vier Woerter
  sind der **Code**, den man Freunden gibt. Ausgesucht werden sie von
  Cloudflare, nicht hier - darum Englisch.
* Der Gast startet `cloudflared access tcp --hostname CODE... --url
  127.0.0.1:P` und verbindet sich mit dem Spiel ganz gewoehnlich mit
  127.0.0.1:P. Ab da ist es dieselbe Leitung wie im LAN (netz.py).

GRUND fuer Cloudflare und nicht einen eigenen Vermittler: ein eigener
Server muesste irgendwo laufen und bezahlt werden. Quick Tunnels kosten
nichts, brauchen kein Konto, und Cloudflare steht in fast jeder Stadt -
der Umweg ist darum klein. Der Preis: es gibt keine Zusage, dass der
Dienst immer da ist. Faellt er aus, geht das LAN weiter (Einstellungen,
NETZ, IM LAN SICHTBAR).

GRUND fuer `--protocol http2`: cloudflared spricht sonst QUIC ueber UDP.
Eine UDP-Steckdose, auf der Antworten von draussen ankommen, kann unter
Windows die Firewall-Abfrage ausloesen - ueber TCP sicher nicht.

**Das Programm** laedt das Spiel beim ersten Spiel ueber das Internet
(seit 0.34.150, vorher lag es fuer drei Systeme in `tools/cloudflared` bei
- 58 MB, von denen jeder ein Drittel brauchte): vom offiziellen Release
auf GitHub, je System die passende Datei (K.ONLINE `pakete`), in einem
eigenen Faden (`Lader`), mit Fortschritt fuer das Ladebild (ladebild.py).
Bevor es laeuft, werden die Pruefsummen von Datei und Programm
verglichen; liegt es einmal im Datenordner (pfade.py), wird nie wieder
geladen. Weil das Spiel selbst schreibt und kein Browser, traegt die
Datei keinen Vermerk "aus dem Internet geladen" - SmartScreen und
Gatekeeper fragen deshalb nicht. Ein installiertes cloudflared oder
DUSTFRONT_CLOUDFLARED geht vor, dann wird nichts geladen.

**Threads.** Anders als in netz.py liest hier je Programm ein kleiner
Faden dessen Ausgabe mit. GRUND: Unter Windows laesst sich eine Pipe nicht
mit select() abfragen; ein Lesen ohne Faden wuerde das Spiel anhalten,
bis cloudflared die naechste Zeile schreibt. Der Faden tut nichts als
Zeilen in eine Schlange zu legen - entschieden wird im Spiel.
"""

from __future__ import annotations

import atexit
import collections
import hashlib
import os
import platform
import queue
import re
import shutil
import socket
import subprocess
import sys
import tarfile
import tempfile
import threading
import time
from pathlib import Path

from . import config as K
# "geraet" und nicht "plattform": so heisst hier schon die Funktion, die die
# passende cloudflared-Datei waehlt.
from . import plattform as geraet
from . import pfade

O = K.ONLINE

# Die Adresse, die cloudflared fuer den Quick Tunnel ausgibt.
ADRESSE_MUSTER = re.compile(r"https://([a-z0-9]+(?:-[a-z0-9]+)+)\.trycloudflare\.com")
# Ein Code, wie man ihn eintippt: mindestens vier Woerter mit Bindestrich.
# GRUND fuer "mindestens vier": ein Rechnername im LAN wie "spiele-pc"
# hat auch einen Bindestrich, soll aber eine Adresse bleiben.
CODE_MUSTER = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+){3,}")
# Fehlerzeilen, die cloudflared auch im Normalbetrieb schreibt und die
# nichts ueber den Tunnel sagen.
HARMLOS = ("fetch features", "icmp", "ping_group_range", "update check")


# ══════════════════════════════════════════════════════════════════
# Das Programm finden
# ══════════════════════════════════════════════════════════════════

def plattform() -> str:
    """Welche Datei von cloudflared auf diesen Rechner passt."""
    maschine = platform.machine().lower()
    if sys.platform.startswith("win"):
        # Windows auf ARM fuehrt das amd64-Programm ueber die eingebaute
        # Uebersetzung aus; ein eigenes gibt es von cloudflared nicht.
        return "windows-amd64"
    if sys.platform == "darwin":
        return "darwin-arm64" if maschine in ("arm64", "aarch64") else "darwin-amd64"
    if sys.platform.startswith("linux"):
        return "linux-" + ("amd64" if maschine in ("x86_64", "amd64") else maschine)
    return sys.platform


def _summe(pfad) -> str:
    h = hashlib.sha256()
    with open(pfad, "rb") as f:
        for stueck in iter(lambda: f.read(1 << 20), b""):
            h.update(stueck)
    return h.hexdigest()


def _ziel(name: str) -> Path:
    """Wo das geladene Programm liegt (dieselbe Stelle wie bis 0.34.149,
    als es aus dem mitgelieferten Archiv kam - wer es so schon hat, laedt
    nichts)."""
    basis = pfade.ordner()
    if basis is None:
        basis = Path(tempfile.gettempdir()) / "dustfront"
    return Path(basis) / "cloudflared" / O["version"] / name


def _paket():
    """(Datei, Summe der Datei, Programmname, Summe des Programms) fuer
    dieses System - oder None, wenn Cloudflare keines anbietet."""
    return O["pakete"].get(plattform())


def _vorhanden() -> str:
    """Pfad des schon geladenen und geprueften Programms, sonst ""."""
    paket = _paket()
    if paket is None:
        return ""
    ziel = _ziel(paket[2])
    try:
        if ziel.is_file() and _summe(ziel) == paket[3]:
            return str(ziel)
    except OSError:
        pass
    return ""


_gefunden: dict = {}


def programm() -> tuple[str, str]:
    """Wo cloudflared liegt: (Pfad, "") oder ("", Grund).

    Der Reihe nach: eine Umgebungsvariable (fuer Pruefungen und wer eine
    andere Fassung will), das schon geladene, ein installiertes. Fehlt
    alles, ist der Grund LADEN_NOETIG - dann laedt `laden_starten` es.
    Gemerkt wird nur ein Fund: das Pruefen kostet einmal eine
    Zehntelsekunde, nicht bei jedem Tunnel.
    """
    eigen = os.environ.get("DUSTFRONT_CLOUDFLARED", "")
    if eigen:
        return (eigen, "") if os.path.isfile(eigen) else \
            ("", "DUSTFRONT_CLOUDFLARED ZEIGT INS LEERE")
    if "pfad" in _gefunden:
        return _gefunden["pfad"], ""
    pfad = _vorhanden() or shutil.which("cloudflared") or ""
    if pfad:
        _gefunden["pfad"] = pfad
        return pfad, ""
    if os.environ.get("DUSTFRONT_OHNE_LADEN", "") not in ("", "0"):
        # Fuer die Pruefungen: sie laden nichts aus dem Netz.
        return "", "CLOUDFLARED FEHLT (DUSTFRONT_OHNE_LADEN)"
    if _paket() is None:
        return "", "CLOUDFLARED GIBT ES FÜR DIESES SYSTEM NICHT"
    return "", LADEN_NOETIG


LADEN_NOETIG = "CLOUDFLARED MUSS ERST GELADEN WERDEN"


def lade_text(l) -> str:
    """Eine Zeile zum Stand des Laders, fuer Anzeigen ohne Balken."""
    if l.gesamt:
        return "CLOUDFLARED LÄDT %d %%" % int(l.anteil * 100)
    return "CLOUDFLARED LÄDT ..."


class Lader:
    """Laedt cloudflared einmal in einem eigenen Faden (seit 0.34.150).

    Es gibt hoechstens einen (`lader()`): Gastgeber und Gast warten auf
    denselben. `geladen`/`gesamt` (Bytes) fuer den Balken, `fertig`, wenn
    das Programm geprueft im Datenordner liegt, sonst der Grund in `fehler`.
    """

    def __init__(self) -> None:
        self.geladen = 0
        self.gesamt = 0
        self.fertig = False
        self.fehler = ""
        self._halt = threading.Event()
        paket = _paket()
        if paket is None:
            self.fehler = "CLOUDFLARED GIBT ES FÜR DIESES SYSTEM NICHT"
            return
        self.paket = paket
        self._faden = threading.Thread(target=self._laden, name="cloudflared laden",
                                       daemon=True)
        self._faden.start()

    @property
    def laeuft(self) -> bool:
        return not self.fertig and not self.fehler

    @property
    def anteil(self) -> float:
        """0 bis 1, so weit es ist (0, solange die Groesse unbekannt ist)."""
        if self.fertig:
            return 1.0
        return min(1.0, self.geladen / float(self.gesamt)) if self.gesamt else 0.0

    def abbrechen(self) -> None:
        if self.laeuft:
            self._halt.set()
            self.fehler = "LADEN ABGEBROCHEN"

    def _laden(self) -> None:
        datei, summe_datei, name, summe = self.paket
        ziel = _ziel(name)
        teil = ziel.with_name(ziel.name + ".teil")
        url = O["quelle"].format(version=O["version"], datei=datei)
        try:
            ziel.parent.mkdir(parents=True, exist_ok=True)
            self._holen(url, teil, summe_datei)
            if self._halt.is_set():
                return
            halb = ziel.with_name(ziel.name + ".neu")
            if datei.endswith(".tgz"):
                with tarfile.open(str(teil), "r:gz") as t:
                    rein = t.extractfile(name)
                    if rein is None:
                        raise ValueError("%s FEHLT IM ARCHIV" % name.upper())
                    with open(str(halb), "wb") as raus:
                        shutil.copyfileobj(rein, raus)
                teil.unlink()
            else:
                os.replace(str(teil), str(halb))
            if _summe(halb) != summe:
                halb.unlink()
                raise ValueError("PRÜFSUMME VON CLOUDFLARED FALSCH")
            os.chmod(str(halb), 0o755)
            os.replace(str(halb), str(ziel))
            _gefunden["pfad"] = str(ziel)
            self.fertig = True
        except ValueError as e:
            self.fehler = str(e)
        except (OSError, tarfile.TarError) as e:
            if not self._halt.is_set():
                self.fehler = "LADEN GING NICHT: %s" % _grund(e)
        finally:
            for rest in (teil, ziel.with_name(ziel.name + ".neu")):
                if not self.fertig and rest.exists():
                    try:
                        rest.unlink()
                    except OSError:
                        pass

    def _holen(self, url: str, teil: Path, summe: str) -> None:
        """Die Datei Stueck fuer Stueck nach `teil`, mit Pruefsumme."""
        import urllib.request
        from . import ablage
        anfrage = urllib.request.Request(url, headers={"User-Agent": "dustfront"})
        h = hashlib.sha256()
        with ablage.oeffnen(anfrage, url, wartezeit=O["laden_frist"]) as antwort, \
                open(str(teil), "wb") as raus:
            self.gesamt = int(antwort.headers.get("Content-Length") or 0)
            while not self._halt.is_set():
                stueck = antwort.read(O["laden_block"])
                if not stueck:
                    break
                raus.write(stueck)
                h.update(stueck)
                self.geladen += len(stueck)
        if not self._halt.is_set() and h.hexdigest() != summe:
            raise ValueError("PRÜFSUMME DER DATEI FALSCH - NOCH EINMAL VERSUCHEN")


def _grund(e) -> str:
    """Ein kurzer Grund fuer die Anzeige."""
    grund = getattr(e, "reason", None) or e
    return str(grund).upper()[:40]


_lader: list = []


def lader() -> Lader | None:
    """Der laufende oder letzte Lader, sonst None."""
    return _lader[0] if _lader else None


def laden_starten() -> Lader:
    """Den Lader starten, wenn nicht schon einer laeuft oder fertig ist.
    Ist der letzte gescheitert, versucht es ein neuer."""
    alt = lader()
    if alt is not None and not alt.fehler:
        return alt
    neu = Lader()
    _lader[:] = [neu]
    return neu


# ══════════════════════════════════════════════════════════════════
# Codes
# ══════════════════════════════════════════════════════════════════

def code_lesen(text: str) -> str:
    """Aus dem, was jemand eintippt oder einfuegt, den Code machen.

    Nimmt den Code allein, den vollen Namen oder die ganze Adresse mit
    https:// - so, wie man ihn eben bekommen hat. Gibt "" zurueck, wenn es
    kein Code ist (dann ist es eine gewoehnliche Adresse im LAN).
    """
    t = str(text or "").strip().lower()
    for vorne in ("https://", "http://"):
        if t.startswith(vorne):
            t = t[len(vorne):]
    t = t.split("/", 1)[0]
    if t.endswith(O["endung"]):
        t = t[:-len(O["endung"])]
    return t if CODE_MUSTER.fullmatch(t) else ""


def host(code: str) -> str:
    return code + O["endung"]


def freier_port() -> int:
    """Ein freier Port auf 127.0.0.1 - nur dort, nie nach aussen."""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]
    finally:
        s.close()


def _ernst(zeile: str) -> bool:
    """Ist das eine Fehlerzeile, die etwas bedeutet?"""
    return " ERR " in zeile and not any(h in zeile.lower() for h in HARMLOS)


def _fehler_kurz(zeile: str) -> str:
    """Aus einer Fehlerzeile von cloudflared etwas, das man lesen kann."""
    z = zeile.lower()
    # Zuerst der Gast: seine Zeile nennt auch "trycloudflare" (die Adresse
    # der Lobby), meint aber, dass dort niemand antwortet.
    if "websocket" in z or "failed to connect to origin" in z:
        return "LOBBY NICHT ERREICHBAR - CODE FALSCH ODER ZU"
    if "quick tunnel" in z or ("trycloudflare" in z and "fail" in z):
        return "CLOUDFLARE GIBT GERADE KEINEN TUNNEL"
    if "dns" in z or "lookup" in z:
        return "CLOUDFLARE NICHT ERREICHBAR (DNS)"
    if "connection refused" in z or "timeout" in z or "timed out" in z:
        return "CLOUDFLARE NICHT ERREICHBAR"
    teil = zeile.split(" ERR ", 1)[-1]
    return teil.strip().upper()[:44] or "CLOUDFLARED IST STEHEN GEBLIEBEN"


# ══════════════════════════════════════════════════════════════════
# Laufende Programme
# ══════════════════════════════════════════════════════════════════

_laufende: set = set()
_job = None


def _an_mich_binden(prozess) -> None:
    """Unter Windows: stirbt das Spiel, stirbt cloudflared mit.

    Ohne das liefe ein Tunnel nach einem Absturz weiter, bis jemand ihn im
    Taskmanager findet. Ein "Job" mit KILL_ON_JOB_CLOSE erledigt das: sein
    Griff gehoert dem Spiel, und schliesst Windows ihn - auch beim Absturz
    -, endet alles, was darin laeuft. Geht etwas davon schief, bleibt es
    beim gewoehnlichen Beenden (atexit) - das Spiel laeuft trotzdem.
    """
    global _job
    if os.name != "nt":
        return
    try:
        import ctypes
        from ctypes import wintypes

        k32 = ctypes.WinDLL("kernel32", use_last_error=True)
        if _job is None:
            k32.CreateJobObjectW.restype = wintypes.HANDLE
            k32.CreateJobObjectW.argtypes = (ctypes.c_void_p, ctypes.c_wchar_p)
            k32.SetInformationJobObject.argtypes = (
                wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD)

            class Grenzen(ctypes.Structure):
                _fields_ = [("PerProcessUserTimeLimit", ctypes.c_int64),
                            ("PerJobUserTimeLimit", ctypes.c_int64),
                            ("LimitFlags", wintypes.DWORD),
                            ("MinimumWorkingSetSize", ctypes.c_size_t),
                            ("MaximumWorkingSetSize", ctypes.c_size_t),
                            ("ActiveProcessLimit", wintypes.DWORD),
                            ("Affinity", ctypes.c_size_t),
                            ("PriorityClass", wintypes.DWORD),
                            ("SchedulingClass", wintypes.DWORD)]

            class Zaehler(ctypes.Structure):
                _fields_ = [(n, ctypes.c_ulonglong) for n in (
                    "ReadOperationCount", "WriteOperationCount",
                    "OtherOperationCount", "ReadTransferCount",
                    "WriteTransferCount", "OtherTransferCount")]

            class Erweitert(ctypes.Structure):
                _fields_ = [("BasicLimitInformation", Grenzen),
                            ("IoInfo", Zaehler),
                            ("ProcessMemoryLimit", ctypes.c_size_t),
                            ("JobMemoryLimit", ctypes.c_size_t),
                            ("PeakProcessMemoryUsed", ctypes.c_size_t),
                            ("PeakJobMemoryUsed", ctypes.c_size_t)]

            job = k32.CreateJobObjectW(None, None)
            if not job:
                return
            info = Erweitert()
            info.BasicLimitInformation.LimitFlags = 0x2000   # KILL_ON_JOB_CLOSE
            # 9 = JobObjectExtendedLimitInformation
            if not k32.SetInformationJobObject(job, 9, ctypes.byref(info),
                                               ctypes.sizeof(info)):
                return
            _job = job
        k32.AssignProcessToJobObject.argtypes = (wintypes.HANDLE, wintypes.HANDLE)
        k32.AssignProcessToJobObject(_job, wintypes.HANDLE(int(prozess._handle)))
    except Exception:                           # noqa: BLE001
        pass


class Prozess:
    """Ein laufendes cloudflared, dessen Ausgabe zeilenweise ankommt."""

    def __init__(self, argumente: list) -> None:
        kw = dict(stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                  stderr=subprocess.STDOUT)
        if os.name == "nt":
            # Kein schwarzes Konsolenfenster neben dem Spiel.
            kw["creationflags"] = 0x08000000       # CREATE_NO_WINDOW
        self._schlange: queue.Queue = queue.Queue()
        self.zeilen = collections.deque(maxlen=80)   # zum Nachsehen
        argumente = [str(a) for a in argumente]
        if argumente[0].endswith(".py"):
            # Die Attrappe der Pruefungen (tests/attrappe_cloudflared.py) -
            # unter Windows ist eine .py-Datei nicht selbst ausfuehrbar.
            argumente.insert(0, sys.executable)
        self.p = subprocess.Popen(argumente, **kw)
        _an_mich_binden(self.p)
        _laufende.add(self)
        faden = threading.Thread(target=self._mitlesen, daemon=True)
        faden.start()

    def _mitlesen(self) -> None:
        try:
            for roh in iter(self.p.stdout.readline, b""):
                self._schlange.put(roh.decode("utf-8", "replace").rstrip())
        except (OSError, ValueError):
            pass

    def neue_zeilen(self) -> list:
        raus = []
        while True:
            try:
                zeile = self._schlange.get_nowait()
            except queue.Empty:
                break
            self.zeilen.append(zeile)
            raus.append(zeile)
        return raus

    @property
    def laeuft(self) -> bool:
        return self.p.poll() is None

    def beenden(self) -> None:
        _laufende.discard(self)
        if self.p.poll() is None:
            try:
                self.p.terminate()
                self.p.wait(timeout=2.0)
            except (OSError, subprocess.TimeoutExpired):
                try:
                    self.p.kill()
                except OSError:
                    pass
        try:
            self.p.stdout.close()
        except (OSError, AttributeError):
            pass


@atexit.register
def alle_beenden() -> None:
    for p in list(_laufende):
        p.beenden()


# ══════════════════════════════════════════════════════════════════
# Gastgeber: der Tunnel
# ══════════════════════════════════════════════════════════════════

class Tunnel:
    """Haengt den Spielport auf 127.0.0.1 an einen Quick Tunnel.

    Laeuft vor sich hin; `schritt()` einmal je Bild liest, was cloudflared
    meldet. `zustand` ist "startet", "bereit" oder "fehler", `code` steht,
    sobald Cloudflare den Namen vergeben hat - erreichbar ist er erst bei
    "bereit". Bricht der Tunnel ab, wird er nach einer Weile neu gestartet;
    der Code ist dann ein anderer (Quick Tunnels vergeben jedes Mal einen
    neuen Namen).
    """

    def __init__(self, port: int) -> None:
        self.port = int(port)
        self.code = ""
        self.bereit = False
        self.fehler = ""
        self._p: Prozess | None = None
        self._seit = 0.0
        self._neustarts = 0
        self._neu_um = 0.0
        self._lader: Lader | None = None
        self._starten()

    def _starten(self) -> None:
        self.code, self.bereit, self.fehler = "", False, ""
        if not geraet.prozesse_erlaubt():
            # iOS (seit 0.34.20): kein zweites Programm, also kein Tunnel.
            # Beitreten geht (wszugang.py), aufmachen nur im LAN.
            self.fehler = "AUF IOS NUR BEITRETEN - LAN GEHT"
            return
        pfad, fehler = programm()
        if not pfad:
            if fehler == LADEN_NOETIG:
                # Erst laden (seit 0.34.150); schritt() startet danach.
                self._lader = laden_starten()
                return
            self.fehler = fehler
            return
        try:
            self._p = Prozess([pfad, "tunnel", "--no-autoupdate",
                               "--protocol", "http2",
                               "--metrics", "127.0.0.1:0",
                               "--url", "tcp://127.0.0.1:%d" % self.port])
        except OSError as e:
            self._p = None
            self.fehler = "CLOUDFLARED STARTET NICHT: %s" % str(e).upper()[:30]
            return
        self._seit = time.monotonic()

    @property
    def zustand(self) -> str:
        if self.bereit:
            return "bereit"
        if self.fehler:
            return "fehler"
        return "laedt" if self._lader is not None else "startet"

    def schritt(self) -> None:
        if self._lader is not None:
            if self._lader.fertig:
                self._lader = None
                self._starten()
            elif self._lader.fehler:
                self.fehler = self._lader.fehler
                self._lader = None
            return
        if self._p is None:
            if (self._neu_um and time.monotonic() >= self._neu_um
                    and self._neustarts < O["neustart_hoechstens"]):
                self._neu_um = 0.0
                self._neustarts += 1
                self._starten()
            return
        for zeile in self._p.neue_zeilen():
            treffer = ADRESSE_MUSTER.search(zeile)
            if treffer and not self.code and "api.trycloudflare" not in zeile:
                self.code = treffer.group(1)
            if "Registered tunnel connection" in zeile:
                self.bereit = True
                self.fehler = ""
                self._neustarts = 0
            elif ("Unregistered tunnel connection" in zeile
                  or "Retrying connection" in zeile):
                self.bereit = False
            elif _ernst(zeile) and not self.bereit and not self.fehler:
                # Die erste ernste Zeile sagt den Grund; was danach kommt,
                # sind meist Ratschlaege von cloudflared dazu.
                self.fehler = _fehler_kurz(zeile)
        if not self._p.laeuft:
            ernste = [z for z in self._p.zeilen if _ernst(z)]
            self._p.beenden()
            self._p = None
            self.bereit = False
            self.fehler = _fehler_kurz(ernste[0]) if ernste else \
                "CLOUDFLARED IST STEHEN GEBLIEBEN"
            self._neu_um = time.monotonic() + O["neustart_nach"]
            return
        if not self.bereit and not self.fehler \
                and time.monotonic() - self._seit > O["start_frist"]:
            self.fehler = "TUNNEL KOMMT NICHT ZUSTANDE"

    def schliessen(self) -> None:
        if self._p is not None:
            self._p.beenden()
            self._p = None
        self.bereit = False
        self._neu_um = 0.0

    def beschreibung(self) -> str:
        """Eine Zeile fuer die Anzeige."""
        if self.bereit and self.code:
            return self.code.upper()
        if self.fehler:
            return self.fehler
        if self._lader is not None:
            return lade_text(self._lader)
        return "STARTET ..." if not self.code else "VERBINDET ..."


# ══════════════════════════════════════════════════════════════════
# Gast: der Zugang
# ══════════════════════════════════════════════════════════════════

def Zugang(code: str):
    """Der Weg eines Gastes zu einem Code - mit cloudflared, oder ohne.

    Ohne (wszugang.py, seit 0.34.20): auf iOS, wo kein zweites Programm
    starten darf, und ueberall, wo cloudflared fehlt (etwa unter Linux,
    wo keines beiliegt). Mit DUSTFRONT_WS_ZUGANG=1 auch sonst - zum
    Ausprobieren, ob der Weg eines iPhones durchkommt.
    """
    erzwungen = os.environ.get("DUSTFRONT_WS_ZUGANG", "") not in ("", "0")
    # Fehlt cloudflared nur, weil es noch nicht geladen ist, wird es
    # geladen (seit 0.34.150) - ohne Weg ohne cloudflared nur, wo es keins gibt.
    if erzwungen or not geraet.prozesse_erlaubt() or \
            not (programm()[0] or programm()[1] == LADEN_NOETIG):
        from .wszugang import WsZugang
        return WsZugang(code)
    return CloudflaredZugang(code)


class CloudflaredZugang:
    """Der Weg eines Gastes zu einem Code: ein Port auf 127.0.0.1.

    `adresse` ist das, womit sich netz.Gast verbinden soll, sobald
    `bereit` ist. Kommt cloudflared nicht bis zur Lobby durch, steht der
    Grund in `fehler`.
    """

    def __init__(self, code: str) -> None:
        self.code = code
        self.port = 0
        self.bereit = False
        self.fehler = ""
        self._p: Prozess | None = None
        self._lader: Lader | None = None
        self._starten()

    def _starten(self) -> None:
        self._seit = time.monotonic()      # die Frist zaehlt erst ab hier
        pfad, fehler = programm()
        if not pfad:
            if fehler == LADEN_NOETIG:
                self._lader = laden_starten()     # schritt() startet danach
                return
            self.fehler = fehler
            return
        try:
            self.port = freier_port()
            self._p = Prozess([pfad, "access", "tcp",
                               "--hostname", host(self.code),
                               "--url", "127.0.0.1:%d" % self.port,
                               "--loglevel", "info"])
        except OSError as e:
            self._p = None
            self.fehler = "CLOUDFLARED STARTET NICHT: %s" % str(e).upper()[:30]

    @property
    def adresse(self) -> str:
        return "127.0.0.1:%d" % self.port

    @property
    def laedt(self) -> bool:
        return self._lader is not None

    def schritt(self) -> None:
        if self._lader is not None:
            if self._lader.fertig:
                self._lader = None
                self._starten()
            elif self._lader.fehler:
                self.fehler = self._lader.fehler
                self._lader = None
            return
        if self._p is None:
            return
        for zeile in self._p.neue_zeilen():
            if "listener" in zeile.lower() and str(self.port) in zeile:
                self.bereit = True
            elif _ernst(zeile) and not self.fehler:
                self.fehler = _fehler_kurz(zeile)
        if not self._p.laeuft and not self.fehler:
            self.fehler = "CLOUDFLARED IST STEHEN GEBLIEBEN"
        if not self.bereit and not self.fehler \
                and time.monotonic() - self._seit > O["zugang_frist"]:
            self.fehler = "ZUGANG KOMMT NICHT ZUSTANDE"

    def schliessen(self) -> None:
        if self._p is not None:
            self._p.beenden()
            self._p = None
        self.bereit = False


# ══════════════════════════════════════════════════════════════════
# Zwischenablage
# ══════════════════════════════════════════════════════════════════

def kopieren(text: str) -> bool:
    """In die Zwischenablage. False, wenn es hier keine gibt."""
    try:
        import pygame
        pygame.scrap.put_text(str(text))
        return True
    except Exception:                           # noqa: BLE001
        return False


def einfuegen() -> str:
    try:
        import pygame
        return str(pygame.scrap.get_text() or "")
    except Exception:                           # noqa: BLE001
        return ""
