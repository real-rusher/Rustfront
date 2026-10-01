"""
DUSTFRONT - Windows prueft das Zertifikat
=========================================

Gemeldet aus dem Netz einer Klinik: Firefox oeffnet den Server, das Spiel
nicht - erst "ZERTIFIKAT UNBEKANNT", nach den mitgelieferten Wurzeln
(0.28.1) "ZERTIFIKAT UNGUELTIG". Kein cmd auf dem Rechner, also auch kein
Selbsttest.

Der Grund liegt zwischen den Stuehlen: Python prueft Zertifikate mit
OpenSSL und einer eigenen Liste. Edge, Chrome und - auf verwalteten
Rechnern - auch Firefox fragen dagegen **Windows**. Und nur Windows kennt
alles, was dort gilt: die Wurzeln, die die Verwaltung des Hauses
eingetragen hat, die Zwischenzertifikate, die eine Firewall mitbringt,
und die Wurzeln, die Windows erst bei Bedarf nachlaedt.

Also fragt das Spiel unter Windows ebenfalls Windows - aber nur, wenn
OpenSSL vorher abgelehnt hat:

1. Verbindung aufbauen, Handschlag ohne eigene Pruefung, die Kette des
   Servers lesen. Noch ist **nichts** gesendet.
2. Windows bauen und pruefen lassen (CertGetCertificateChain, dann
   CertVerifyCertificateChainPolicy mit der Regel fuer SSL und dem Namen
   des Servers) - genau das, was ein Browser tut.
3. Sagt Windows ja, geht die Anfrage hinaus. Sagt es nein, wird die
   Verbindung geschlossen, und die Meldung nennt den Grund.

**Alles, was schiefgeht, heisst nein.** Fehlt eine Funktion, passt ein
Typ nicht, wirft ctypes: die Verbindung wird nicht benutzt. Lieber keine
Anmeldung als eine, bei der ein Fremder mitliest.

Vorbild war das Paket `truststore` (das pip seit 23.2 benutzt); hier
schmaler, ohne Abhaengigkeit, und nur fuer diesen einen Fall.
"""

from __future__ import annotations

import http.client
import ssl
import sys
import urllib.request

# Server-Authentifizierung: die einzige Verwendung, fuer die das
# Zertifikat taugen muss.
_SERVERAUTH = b"1.3.6.1.5.5.7.3.1"

# Was Windows zu sagen hat, in Worten fuer die Anzeige.
WINDOWS_GRUENDE = {
    0x800B0109: "WURZEL UNBEKANNT",     # CERT_E_UNTRUSTEDROOT
    0x800B010A: "KETTE UNVOLLSTAENDIG",  # CERT_E_CHAINING
    0x800B0101: "ABGELAUFEN - UHR?",     # CERT_E_EXPIRED
    0x800B010F: "FALSCHER NAME",          # CERT_E_CN_NO_MATCH
    0x800B010C: "ZURUECKGEZOGEN",         # CERT_E_REVOKED
    0x800B0110: "FALSCHER ZWECK",         # CERT_E_WRONG_USAGE
    0x80096004: "SIGNATUR FALSCH",        # TRUST_E_CERT_SIGNATURE
    0x800B0112: "STELLE NICHT VERTRAUT",  # CERT_E_UNTRUSTEDCA
    0x800B0111: "AUSDRUECKLICH GESPERRT",  # TRUST_E_EXPLICIT_DISTRUST
}


def verfuegbar() -> bool:
    return sys.platform == "win32"


def kette_lesen(tls_sock) -> list[bytes]:
    """Alle Zertifikate, die der Server geschickt hat, als DER.

    Ab Python 3.13 oeffentlich (get_unverified_chain), davor gibt es
    dieselbe Funktion am inneren Objekt (seit 3.10). Fehlt beides, bleibt
    das Zertifikat des Servers allein - Windows sucht die Zwischenstufen
    dann selbst.
    """
    kette = []
    for quelle in (tls_sock, getattr(tls_sock, "_sslobj", None)):
        holen = getattr(quelle, "get_unverified_chain", None)
        if holen is None:
            continue
        try:
            roh = holen() or []
        except Exception:
            continue
        for z in roh:
            if isinstance(z, (bytes, bytearray)):
                kette.append(bytes(z))
            else:
                try:
                    kette.append(z.public_bytes(ssl._ssl.ENCODING_DER))
                except Exception:
                    pass
        if kette:
            return kette
    blatt = tls_sock.getpeercert(binary_form=True)
    return [blatt] if blatt else []


def pruefen(kette: list[bytes], name: str) -> int:
    """Fragt Windows. Gibt 0 zurueck, wenn es vertraut, sonst einen Fehler.

    Nie eine Ausnahme: alles Unerwartete wird zu einem Fehlercode (-1),
    und ein Fehlercode heisst, dass die Verbindung nicht benutzt wird.
    """
    if not verfuegbar() or not kette or not name:
        return -1
    try:
        return _pruefen(kette, name)
    except Exception:
        return -1


# ---- Die Strukturen aus wincrypt.h --------------------------------------
# Auf Modulebene, damit tests/test_konto.py ihre Groessen pruefen kann -
# eine falsche Groesse waere hier der gefaehrlichste Fehler, und den
# merkt man nicht an einer Fehlermeldung.
from ctypes import POINTER, Structure, c_char_p, c_int32, c_uint32, c_void_p, c_wchar_p

DWORD = c_uint32


class CERT_ENHKEY_USAGE(Structure):
    _fields_ = [("cUsageIdentifier", DWORD),
                ("rgpszUsageIdentifier", POINTER(c_char_p))]


class CERT_USAGE_MATCH(Structure):
    _fields_ = [("dwType", DWORD), ("Usage", CERT_ENHKEY_USAGE)]


class CERT_CHAIN_PARA(Structure):            # die kurze, alte Form
    _fields_ = [("cbSize", DWORD), ("RequestedUsage", CERT_USAGE_MATCH)]


class SSL_EXTRA_CERT_CHAIN_POLICY_PARA(Structure):
    _fields_ = [("cbSize", DWORD), ("dwAuthType", DWORD),
                ("fdwChecks", DWORD), ("pwszServerName", c_wchar_p)]


class CERT_CHAIN_POLICY_PARA(Structure):
    _fields_ = [("cbSize", DWORD), ("dwFlags", DWORD),
                ("pvExtraPolicyPara", c_void_p)]


class CERT_CHAIN_POLICY_STATUS(Structure):
    _fields_ = [("cbSize", DWORD), ("dwError", DWORD),
                ("lChainIndex", c_int32), ("lElementIndex", c_int32),
                ("pvExtraPolicyStatus", c_void_p)]


def _pruefen(kette, name):
    import ctypes
    from ctypes import byref, sizeof

    crypt32 = ctypes.WinDLL("crypt32.dll", use_last_error=True)
    BOOL = ctypes.c_int

    CertOpenStore = crypt32.CertOpenStore
    CertOpenStore.argtypes = [c_void_p, DWORD, c_void_p, DWORD, c_void_p]
    CertOpenStore.restype = c_void_p
    CertAddEncodedCertificateToStore = crypt32.CertAddEncodedCertificateToStore
    CertAddEncodedCertificateToStore.argtypes = [c_void_p, DWORD, c_char_p, DWORD,
                                                 DWORD, POINTER(c_void_p)]
    CertAddEncodedCertificateToStore.restype = BOOL
    CertGetCertificateChain = crypt32.CertGetCertificateChain
    CertGetCertificateChain.argtypes = [c_void_p, c_void_p, c_void_p, c_void_p,
                                        POINTER(CERT_CHAIN_PARA), DWORD, c_void_p,
                                        POINTER(c_void_p)]
    CertGetCertificateChain.restype = BOOL
    CertVerifyCertificateChainPolicy = crypt32.CertVerifyCertificateChainPolicy
    CertVerifyCertificateChainPolicy.argtypes = [c_void_p, c_void_p,
                                                 POINTER(CERT_CHAIN_POLICY_PARA),
                                                 POINTER(CERT_CHAIN_POLICY_STATUS)]
    CertVerifyCertificateChainPolicy.restype = BOOL
    CertFreeCertificateChain = crypt32.CertFreeCertificateChain
    CertFreeCertificateChain.argtypes = [c_void_p]
    CertFreeCertificateChain.restype = None
    CertFreeCertificateContext = crypt32.CertFreeCertificateContext
    CertFreeCertificateContext.argtypes = [c_void_p]
    CertFreeCertificateContext.restype = BOOL
    CertCloseStore = crypt32.CertCloseStore
    CertCloseStore.argtypes = [c_void_p, DWORD]
    CertCloseStore.restype = BOOL

    CERT_STORE_PROV_MEMORY = 2
    KODIERUNG = 0x00000001 | 0x00010000        # X509_ASN | PKCS_7_ASN
    CERT_STORE_ADD_USE_EXISTING = 2
    USAGE_MATCH_TYPE_AND = 0
    CERT_CHAIN_POLICY_SSL = 4
    AUTHTYPE_SERVER = 2

    lager = CertOpenStore(CERT_STORE_PROV_MEMORY, 0, None, 0, None)
    if not lager:
        return -1
    blatt = c_void_p()
    kontext = c_void_p()
    try:
        # Das Zertifikat des Servers, und die Zwischenstufen, die er
        # mitgeschickt hat, als Hilfe fuer Windows beim Bauen der Kette.
        if not CertAddEncodedCertificateToStore(lager, KODIERUNG, kette[0], len(kette[0]),
                                                CERT_STORE_ADD_USE_EXISTING, byref(blatt)):
            return -1
        for z in kette[1:]:
            CertAddEncodedCertificateToStore(lager, KODIERUNG, z, len(z),
                                             CERT_STORE_ADD_USE_EXISTING, None)

        verwendungen = (c_char_p * 1)(_SERVERAUTH)
        para = CERT_CHAIN_PARA()
        para.cbSize = sizeof(CERT_CHAIN_PARA)
        para.RequestedUsage.dwType = USAGE_MATCH_TYPE_AND
        para.RequestedUsage.Usage.cUsageIdentifier = 1
        para.RequestedUsage.Usage.rgpszUsageIdentifier = ctypes.cast(verwendungen,
                                                                     POINTER(c_char_p))
        if not CertGetCertificateChain(None, blatt, None, lager, byref(para), 0, None,
                                       byref(kontext)):
            return -1

        extra = SSL_EXTRA_CERT_CHAIN_POLICY_PARA()
        extra.cbSize = sizeof(SSL_EXTRA_CERT_CHAIN_POLICY_PARA)
        extra.dwAuthType = AUTHTYPE_SERVER
        extra.fdwChecks = 0                         # nichts nachsehen lassen
        extra.pwszServerName = name          # ctypes haelt den Puffer selbst fest
        regel = CERT_CHAIN_POLICY_PARA()
        regel.cbSize = sizeof(CERT_CHAIN_POLICY_PARA)
        regel.dwFlags = 0
        regel.pvExtraPolicyPara = ctypes.cast(ctypes.pointer(extra), c_void_p)
        stand = CERT_CHAIN_POLICY_STATUS()
        stand.cbSize = sizeof(CERT_CHAIN_POLICY_STATUS)
        if not CertVerifyCertificateChainPolicy(CERT_CHAIN_POLICY_SSL, kontext,
                                                byref(regel), byref(stand)):
            return -1
        return int(stand.dwError)
    finally:
        if kontext:
            CertFreeCertificateChain(kontext)
        if blatt:
            CertFreeCertificateContext(blatt)
        CertCloseStore(lager, 0)


class WindowsAbgelehnt(ssl.SSLCertVerificationError):
    """Windows hat dem Zertifikat nicht vertraut (oder nicht antworten koennen)."""

    def __init__(self, code: int) -> None:
        super().__init__(1, "windows: 0x%08X" % (code & 0xFFFFFFFF))
        self.verify_code = -1
        self.windows_code = code
        self.verify_message = WINDOWS_GRUENDE.get(code & 0xFFFFFFFF,
                                                  "WINDOWS 0x%08X" % (code & 0xFFFFFFFF)
                                                  if code != -1 else "WINDOWS: KEINE ANTWORT")


def _verbinden(verbindung) -> None:
    """Statt HTTPSConnection.connect: erst Windows fragen, dann benutzen."""
    http.client.HTTPConnection.connect(verbindung)       # Leitung, ggf. ueber Proxy
    name = verbindung._tunnel_host or verbindung.host
    k = ssl.create_default_context()
    k.check_hostname = False
    k.verify_mode = ssl.CERT_NONE        # die Pruefung macht gleich Windows
    s = k.wrap_socket(verbindung.sock, server_hostname=name)
    code = pruefen(kette_lesen(s), name)
    if code != 0:
        s.close()
        raise WindowsAbgelehnt(code)
    verbindung.sock = s


class _Verbindung(http.client.HTTPSConnection):
    def connect(self):
        _verbinden(self)


class _Handler(urllib.request.HTTPSHandler):
    def https_open(self, anfrage):
        return self.do_open(_Verbindung, anfrage)


def oeffner() -> urllib.request.OpenerDirector:
    """Ein urllib-Oeffner, der jedes Zertifikat von Windows pruefen laesst.
    Proxy-Einstellungen gelten wie sonst auch."""
    return urllib.request.build_opener(_Handler())
