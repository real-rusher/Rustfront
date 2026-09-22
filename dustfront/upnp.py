"""
DUSTFRONT - Der Weg durch den Router
====================================

Im LAN reicht die eigene Adresse. Ueber das Internet steht ein Router
dazwischen, und der laesst von aussen nichts herein, was er nicht kennt.
Es gibt genau drei Wege daran vorbei:

1. **Von Hand freigeben.** Funktioniert immer, muss aber jeder selbst im
   Router einstellen.
2. **UPnP.** Der Router macht die Freigabe selbst, wenn man ihn hoeflich
   fragt. Das ist, was hier drinsteht. Viele Heimrouter koennen es und
   haben es an; manche nicht, und in einem Studentenwohnheim oder hinter
   einem Mobilfunkanschluss hilft es gar nicht.
3. **Ein Server in der Mitte**, der beide Seiten verbindet. Das waere der
   Weg, der ueberall funktioniert - er braucht aber einen Rechner, der
   dauerhaft laeuft, und den gibt es hier nicht.

Es bleibt also 2 mit 1 als Rueckfall. Schlaegt UPnP fehl, sagt das Spiel
genau, was in den Router einzutragen ist, statt bloss "geht nicht".

**Wie UPnP ablaeuft.** Drei Schritte, alle mit Bordmitteln:

    M-SEARCH per UDP an 239.255.255.250:1900   -> wer ist hier Router?
    GET auf die genannte Beschreibung (XML)    -> wo nehme ich Befehle an?
    POST mit SOAP an diese Stelle              -> mach mir Port X auf

Nichts davon darf das Spiel aufhalten: jede Antwort hat ein kurzes
Zeitlimit, und jeder Fehler endet hier und nicht im Gefecht.
"""

from __future__ import annotations

import re
import socket
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

from . import config as K

# Die beiden Dienste, die eine Portfreigabe koennen. Kabel- und
# DSL-Router melden sich unterschiedlich, gefragt werden darum beide.
DIENSTE = (
    "urn:schemas-upnp-org:service:WANIPConnection:1",
    "urn:schemas-upnp-org:service:WANPPPConnection:1",
)

SOAP_HUELLE = (
    '<?xml version="1.0"?>'
    '<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/"'
    ' s:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/">'
    '<s:Body><u:%(befehl)s xmlns:u="%(dienst)s">%(werte)s'
    '</u:%(befehl)s></s:Body></s:Envelope>'
)


def _ohne_raum(text: str) -> str:
    return (text or "").strip()


def gateway_suchen(wartezeit: float | None = None) -> list[str]:
    """Sucht per M-SEARCH nach Routern und gibt deren Beschreibungen zurueck.

    Mehrere Antworten sind normal - ein Router meldet sich gern mehrfach,
    und in manchen Netzen antwortet mehr als einer. Zurueck kommen die
    Adressen der Beschreibungen, ohne Doppelte, in der Reihenfolge des
    Eintreffens.
    """
    u = K.UPNP
    wartezeit = u["suchzeit"] if wartezeit is None else wartezeit
    frage = (
        "M-SEARCH * HTTP/1.1\r\n"
        "HOST: %s:%d\r\n"
        'MAN: "ssdp:discover"\r\n'
        "MX: %d\r\n"
        "ST: urn:schemas-upnp-org:device:InternetGatewayDevice:1\r\n"
        "\r\n" % (u["gruppe"], u["port"], int(max(1, wartezeit)))
    ).encode()

    gefunden: list[str] = []
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.settimeout(wartezeit)
        sock.sendto(frage, (u["gruppe"], u["port"]))
        while True:
            try:
                daten, _woher = sock.recvfrom(u["puffer"])
            except (socket.timeout, OSError):
                break
            ort = kopfzeile_lesen(daten.decode("utf-8", "replace"), "location")
            if ort and ort not in gefunden:
                gefunden.append(ort)
                if len(gefunden) >= u["hoechstens"]:
                    break
    finally:
        sock.close()
    return gefunden


def kopfzeile_lesen(antwort: str, name: str) -> str:
    """Eine Kopfzeile aus einer HTTP-artigen Antwort herausziehen.

    Eigene kleine Auswertung statt einer Bibliothek: SSDP-Antworten sind
    kein sauberes HTTP, und die Grossschreibung der Kopfzeilen ist bei
    jedem Hersteller anders.
    """
    for zeile in antwort.splitlines():
        if ":" not in zeile:
            continue
        schluessel, _, wert = zeile.partition(":")
        if schluessel.strip().lower() == name.lower():
            return _ohne_raum(wert)
    return ""


def dienst_finden(beschreibung: str, xml_text: str) -> tuple[str, str]:
    """Sucht in der Geraetebeschreibung die Stelle fuer Portfreigaben.

    Gibt (Dienst, vollstaendige Adresse) zurueck, oder ("", "").
    Der Weg in der Beschreibung ist oft relativ - er wird hier an die
    Adresse der Beschreibung angehaengt, sonst zeigt er ins Leere.
    """
    try:
        baum = ET.fromstring(xml_text)
    except ET.ParseError:
        return "", ""
    # Die Namensraeume sind je Hersteller verschieden. Statt sie zu
    # raten, wird auf den Namen hinter der Klammer geschaut.
    for knoten in baum.iter():
        if not knoten.tag.endswith("service"):
            continue
        art = steuerweg = ""
        for kind in knoten:
            name = kind.tag.rsplit("}", 1)[-1]
            if name == "serviceType":
                art = _ohne_raum(kind.text)
            elif name == "controlURL":
                steuerweg = _ohne_raum(kind.text)
        if art in DIENSTE and steuerweg:
            return art, urllib.parse.urljoin(beschreibung, steuerweg)
    return "", ""


def soap_antwort_lesen(xml_text: str, feld: str) -> str:
    """Einen Wert aus einer SOAP-Antwort holen, ohne Namensraeume zu raten."""
    treffer = re.search(r"<%s>(.*?)</%s>" % (feld, feld), xml_text, re.S)
    return _ohne_raum(treffer.group(1)) if treffer else ""


class Router:
    """Eine gefundene Portfreigabe-Stelle, an die man Befehle schicken kann.

    Der Baukasten sucht **nicht** von selbst - dafuer gibt es `suchen()`.
    So laesst sich die Klasse mit einer erfundenen Adresse pruefen, ohne
    dass ein echter Router im Netz stehen muss.
    """

    def __init__(self, dienst: str, steueradresse: str) -> None:
        self.dienst = dienst
        self.steueradresse = steueradresse
        self.fehler = ""

    @classmethod
    def suchen(cls) -> "Router | None":
        """Den ersten Router im Netz finden, der Portfreigaben kann."""
        for ort in gateway_suchen():
            xml_text = cls._holen(ort)
            if not xml_text:
                continue
            dienst, adresse = dienst_finden(ort, xml_text)
            if dienst:
                return cls(dienst, adresse)
        return None

    @staticmethod
    def _holen(adresse: str) -> str:
        try:
            with urllib.request.urlopen(adresse,
                                        timeout=K.UPNP["wartezeit"]) as antwort:
                return antwort.read().decode("utf-8", "replace")
        except (urllib.error.URLError, OSError, ValueError):
            return ""

    def rufen(self, befehl: str, werte: dict) -> str:
        """Einen SOAP-Befehl schicken. Gibt die Antwort zurueck, oder ""."""
        inhalt = "".join("<%s>%s</%s>" % (name, wert, name)
                         for name, wert in werte.items())
        koerper = (SOAP_HUELLE % dict(befehl=befehl, dienst=self.dienst,
                                      werte=inhalt)).encode()
        anfrage = urllib.request.Request(
            self.steueradresse, data=koerper,
            headers={"Content-Type": 'text/xml; charset="utf-8"',
                     "SOAPAction": '"%s#%s"' % (self.dienst, befehl)})
        try:
            with urllib.request.urlopen(
                    anfrage, timeout=K.UPNP["wartezeit"]) as antwort:
                return antwort.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as grund:
            self.fehler = "Router lehnt ab (%s)" % grund.code
        except (urllib.error.URLError, OSError, ValueError) as grund:
            self.fehler = "%s" % grund
        return ""

    # ---- Die drei Befehle, die gebraucht werden ------------------------
    def aussenadresse(self) -> str:
        return soap_antwort_lesen(self.rufen("GetExternalIPAddress", {}),
                                  "NewExternalIPAddress")

    def freigeben(self, port: int, innen: str) -> bool:
        antwort = self.rufen("AddPortMapping", {
            "NewRemoteHost": "",
            "NewExternalPort": int(port),
            "NewProtocol": "TCP",
            "NewInternalPort": int(port),
            "NewInternalClient": innen,
            "NewEnabled": 1,
            "NewPortMappingDescription": K.UPNP["beschriftung"],
            # 0 heisst "bis auf Widerruf". Manche Router lehnen das ab und
            # wollen eine Dauer - deshalb steht hier eine.
            "NewLeaseDuration": int(K.UPNP["dauer"]),
        })
        return "AddPortMappingResponse" in antwort

    def schliessen(self, port: int) -> bool:
        antwort = self.rufen("DeletePortMapping", {
            "NewRemoteHost": "",
            "NewExternalPort": int(port),
            "NewProtocol": "TCP",
        })
        return "DeletePortMappingResponse" in antwort


class Freigabe:
    """Eine offene Tuer im Router, die sich selbst wieder schliesst.

    Alles daran darf schiefgehen: gibt es keinen Router, der mitmacht,
    bleibt `offen` falsch und `grund` sagt warum. Das Gefecht laeuft
    trotzdem - nur eben nur im eigenen Netz.
    """

    def __init__(self, port: int, innen: str) -> None:
        self.port = int(port)
        self.innen = innen
        self.offen = False
        self.aussen = ""
        self.grund = ""
        self._router: Router | None = None

    def oeffnen(self) -> bool:
        router = Router.suchen()
        if router is None:
            self.grund = "Kein Router im Netz, der UPnP beherrscht"
            return False
        self._router = router
        self.aussen = router.aussenadresse()
        if not router.freigeben(self.port, self.innen):
            self.grund = router.fehler or "Der Router hat die Freigabe abgelehnt"
            return False
        self.offen = True
        return True

    def zumachen(self) -> None:
        if self.offen and self._router is not None:
            self._router.schliessen(self.port)
        self.offen = False

    def bericht(self) -> list[str]:
        """Was man den Mitspielern sagt - oder was zu tun ist."""
        if self.offen:
            return [
                "Der Router hat Port %d von selbst freigegeben (UPnP)." % self.port,
                "Mitspieler verbinden sich mit:",
                "   %s:%d" % (self.aussen or "DEINE-OEFFENTLICHE-IP", self.port),
            ]
        return [
            "Automatisch ging es nicht: %s" % (self.grund or "unbekannt"),
            "Von Hand im Router eintragen (Portfreigabe / Port Forwarding):",
            "   Protokoll TCP, Port %d, Ziel %s" % (self.port, self.innen),
            "Danach verbinden sich Mitspieler mit deiner oeffentlichen",
            "Adresse und diesem Port. Die eigene oeffentliche Adresse",
            "zeigt jede Seite, die 'meine IP' anzeigt.",
        ]
