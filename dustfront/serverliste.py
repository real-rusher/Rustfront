"""
DUSTFRONT - Die Serverliste (seit 0.34.155)
===========================================

Gewuenscht: "eine Liste, wo man alle Server sieht, die gerade online sind ...
und beitreten kann."

Bis dahin fand man fremde Lobbys nur im eigenen Netz (lan.py) oder ueber den
Code, den der Gastgeber einem schickte (online.py). Jetzt haengt jeder
Gastgeber mit Online-Code seine Lobby in eine Tabelle beim Server des Kontos
(Supabase, ablage.py), und die Lobbysuche zeigt sie neben denen aus dem Netz.
Ein Klick tritt ueber den Code bei - genau wie von Hand eingegeben.

**Wer aushaengt.** Nur, wer angemeldet ist (ein Konto auf dem Server) und
einen Online-Code hat; abschaltbar unter EINSTELLUNGEN > NETZ > IN DER
SERVERLISTE. GRUND fuer die Anmeldung: die Tabelle laesst nur den Besitzer
einer Zeile schreiben und loeschen (Zeilenschutz). Ohne Konto koennte jeder
beliebige Zeilen eintragen oder fremde ueberschreiben.

**Was aushaengt.** Name, Version, Spieler/Plaetze, Lobby oder Runde,
Spielart, Karte, ob ein Kennwort gilt - dasselbe wie im LAN (`_ansage`) - und
der Code. Das Kennwort selbst geht nie hinaus.

**Wie lange.** Alle `takt` Sekunden neu (K.ONLINE serverliste); was laenger
als `gilt` Sekunden nicht erneuert wurde, zeigt der Server nicht mehr (der
Zeilenschutz filtert es). Geht die Lobby zu, wird die Zeile geloescht; stuerzt
das Spiel ab, verschwindet sie nach `gilt` Sekunden von selbst.

**Nie ein Ruckeln.** Jede Anfrage laeuft in einem eigenen Faden; das Spiel
fragt nur nach dem Ergebnis. Ist die Tabelle (noch) nicht angelegt -
docs/KONTO.md, Abschnitt Serverliste -, sagt die Suche das, und alles andere
geht weiter.
"""

from __future__ import annotations

import threading

from . import config as K
from . import netz


def _ablage():
    from . import ablage
    a = ablage.NetzAblage()
    return a if a.eingerichtet else None


def _konto(app):
    try:
        return getattr(app, "_konto", None)
    except Exception:                    # noqa: BLE001
        return None


def angemeldet_mit_server(app) -> bool:
    k = _konto(app)
    return bool(k is not None and k.angemeldet and getattr(k, "mit_server", False))


def zeile_bauen(ansage: dict, code: str) -> dict:
    """Was ausgehaengt wird: die LAN-Ansage plus Code, gekuerzt wie dort."""
    return {"code": str(code).lower()[:80],
            "name": netz.name_saeubern(str(ansage.get("name", "")))[:24],
            "version": str(ansage.get("version", ""))[:16],
            "spieler": max(0, min(99, int(ansage.get("spieler", 1)))),
            "hoechstens": max(1, min(99, int(ansage.get("hoechstens", K.NETZ["hoechstens"])))),
            "lobby": bool(ansage.get("lobby", True)),
            "modus": str(ansage.get("modus", ""))[:24].upper(),
            "karte": str(ansage.get("karte", ""))[:24].upper(),
            "passwort": bool(ansage.get("passwort", False))}


def eintrag_aus_zeile(z) -> dict | None:
    """Eine Zeile vom Server in das Format der Lobbysuche (wie lan.py)."""
    from . import online
    if not isinstance(z, dict):
        return None
    code = online.code_lesen(str(z.get("code", "")))
    if not code:
        return None
    try:
        spieler = max(0, min(99, int(z.get("spieler", 0))))
        hoechstens = max(1, min(99, int(z.get("hoechstens", K.NETZ["hoechstens"]))))
    except (TypeError, ValueError):
        return None
    return {"name": netz.name_saeubern(str(z.get("name", ""))) or "LOBBY",
            "wirt": "", "port": 0, "adresse": code,
            "version": str(z.get("version", ""))[:16],
            "spieler": spieler, "hoechstens": hoechstens,
            "lobby": bool(z.get("lobby", False)),
            "modus": str(z.get("modus", ""))[:24].upper(),
            "karte": str(z.get("karte", ""))[:24].upper(),
            "passwort": bool(z.get("passwort", False)),
            "kennung": "online:" + code, "online": True}


class _Auftrag:
    """Eine Anfrage in einem eigenen Faden - immer hoechstens eine zur Zeit."""

    def __init__(self) -> None:
        self._faden = None
        self.ergebnis = None             # die letzte Antwort (ablage.Antwort)

    @property
    def laeuft(self) -> bool:
        return self._faden is not None and self._faden.is_alive()

    def starten(self, arbeit) -> bool:
        if self.laeuft:
            return False

        def lauf():
            try:
                self.ergebnis = arbeit()
            except Exception as fehler:          # noqa: BLE001  nie das Spiel stoeren
                from .ablage import schlecht
                self.ergebnis = schlecht(str(fehler)[:80].upper())

        self._faden = threading.Thread(target=lauf, daemon=True, name="serverliste")
        self._faden.start()
        return True


def _nicht_eingerichtet(fehler: str) -> bool:
    t = (fehler or "").upper()
    return ("DOES NOT EXIST" in t or "NOT FOUND" in t or "FEHLER 404" in t
            or "COULD NOT FIND" in t or "SCHEMA CACHE" in t)


class Aushang:
    """Beim Gastgeber: die eigene Lobby in der Serverliste."""

    def __init__(self, app) -> None:
        self.app = app
        self._auftrag = _Auftrag()
        self._rest = 0.0
        self._haengt = False             # steht gerade eine Zeile von uns dort?
        self.zustand = ""                # fuer die Anzeige: AUSGEHAENGT, NICHT EINGERICHTET ...

    def schritt(self, dt: float, ansage, code: str, an: bool) -> None:
        a = self._auftrag
        if a.ergebnis is not None and not a.laeuft:
            antwort, a.ergebnis = a.ergebnis, None
            if antwort:
                self.zustand = "IN DER SERVERLISTE" if self._haengt else ""
            else:
                self.zustand = ("SERVERLISTE NICHT EINGERICHTET" if _nicht_eingerichtet(antwort.fehler)
                                else "SERVERLISTE: " + antwort.fehler[:40])
        moeglich = bool(an and code and angemeldet_mit_server(self.app))
        if not moeglich:
            if self._haengt:
                self.entfernen()
            elif not a.laeuft:
                self.zustand = ""
            return
        self._rest -= dt
        if self._rest > 0.0 or a.laeuft:
            return
        self._rest = float(K.ONLINE["serverliste"]["takt"])
        zeile = zeile_bauen(ansage(), code)
        token = _konto(self.app).sitzung
        ablage = _ablage()
        if ablage is None:
            return
        self._haengt = True
        a.starten(lambda: ablage._rufen(
            "/rest/v1/lobby?on_conflict=konto", zeile, token=token,
            kopf={"Prefer": "resolution=merge-duplicates,return=minimal"}))

    def entfernen(self) -> None:
        """Die eigene Zeile loeschen (die Lobby geht zu, oder es ist aus)."""
        if not self._haengt:
            return
        self._haengt = False
        self._rest = 0.0
        k = _konto(self.app)
        ablage = _ablage()
        if ablage is None or k is None or not k.angemeldet:
            return
        token = k.sitzung
        # Nicht ueber _auftrag: ein Loeschen soll nicht warten, bis ein
        # Aushang fertig ist - und es darf nach dem Ende des Gefechts laufen.
        threading.Thread(target=lambda: ablage._rufen(
            "/rest/v1/lobby?konto=not.is.null", None, token=token, methode="DELETE"),
            daemon=True, name="serverliste_weg").start()
        self.zustand = ""

    def schliessen(self) -> None:
        self.entfernen()


class Suche:
    """Beim Spieler: die Serverliste lesen, alle `suche_takt` Sekunden."""

    def __init__(self, app, ohne_code: str = "") -> None:
        self.app = app
        self.ohne = (ohne_code or "").lower()
        self._auftrag = _Auftrag()
        self._rest = 0.0
        self._liste: list = []
        self.zustand = "SUCHE ONLINE ..."
        self.gelesen = False

    def schritt(self, dt: float) -> None:
        a = self._auftrag
        if a.ergebnis is not None and not a.laeuft:
            antwort, a.ergebnis = a.ergebnis, None
            if antwort and isinstance(antwort.daten, list):
                liste = []
                for z in antwort.daten[:K.ONLINE["serverliste"]["hoechstens"]]:
                    e = eintrag_aus_zeile(z)
                    if e is not None and e["adresse"] != self.ohne:
                        liste.append(e)
                self._liste = liste
                self.gelesen = True
                self.zustand = ("%d ONLINE" % len(liste)) if liste else "ONLINE: KEINE OFFENE LOBBY"
            elif antwort:
                self._liste = []
                self.zustand = "ONLINE: KEINE OFFENE LOBBY"
            else:
                self.zustand = ("SERVERLISTE NOCH NICHT EINGERICHTET"
                                if _nicht_eingerichtet(antwort.fehler)
                                else "SERVERLISTE: " + antwort.fehler[:36])
        self._rest -= dt
        if self._rest > 0.0 or a.laeuft:
            return
        self._rest = float(K.ONLINE["serverliste"]["suche_takt"])
        ablage = _ablage()
        if ablage is None:
            self.zustand = "KEIN SERVER EINGETRAGEN"
            return
        a.starten(lambda: ablage._rufen(
            "/rest/v1/lobby?select=code,name,version,spieler,hoechstens,lobby,modus,karte,passwort"
            "&order=aktualisiert.desc&limit=%d" % int(K.ONLINE["serverliste"]["hoechstens"])))

    def liste(self) -> list:
        return list(self._liste)

    def schliessen(self) -> None:
        self._liste = []
