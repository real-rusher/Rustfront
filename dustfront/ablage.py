"""
DUSTFRONT - Ablage fuer Konten, Profile und Werte
=================================================

Hier liegt die Frage, wo ein Konto und seine Zahlen wirklich stehen. Das
Spiel selbst fragt nie danach; es redet mit `konto.py`, und das redet mit
einer Ablage. Es gibt zwei davon, und beide koennen alles:

    LokaleAblage    Dateien im Benutzerordner. Braucht nichts und
                    niemanden, laeuft im Zug ohne Netz, und der
                    Gastgeber einer LAN-Runde kann damit Konten fuer
                    seine Gaeste im Terminal anlegen.
    NetzAblage      Supabase ueber schlichtes HTTPS. Dasselbe Konto auf
                    jedem Rechner, an dem man sich anmeldet.


Warum Supabase
--------------

Gesucht war etwas, das **auf einem frisch heruntergeladenen Spiel sofort
mit einer einfachen Anmeldung funktioniert**, umsonst ist und die Zahlen
nie durcheinanderbringt. Supabase erfuellt das aus vier Gruenden:

1. **Es spricht nur HTTPS und JSON.** Kein SDK, keine Abhaengigkeit,
    kein `pip install` - `urllib.request` aus der Standardbibliothek
    reicht, genau wie schon bei der Portfreigabe in `upnp.py`. Wer das
    Spiel herunterlaedt, hat damit alles, was er braucht.
2. **Der oeffentliche Schluessel darf oeffentlich sein.** Der "anon key"
    ist dafuer gemacht, im Klienten zu stehen. Er darf also mit im
    Quelltext liegen, und deshalb geht die Anmeldung auf einem neuen
    Rechner sofort, ohne dass irgendwer irgendwo etwas eintragen muss.
    Genau das war die Bedingung.
3. **Kennwoerter fasst das Spiel nie an.** Sie gehen einmal ueber TLS
    zum Anmeldedienst und werden dort mit bcrypt gehasht. Weder liegt
    hier ein Klartextkennwort, noch koennte eines hier liegen.
4. **Zeilenschutz (RLS).** Der mitgelieferte Schluessel kommt an fremde
    Zeilen nicht heran - der Server entscheidet das, nicht der Klient.
    Ein veraenderter Klient nuetzt also nichts.

Was aufgesetzt werden muss und wie die Tabellen aussehen, steht in
`docs/KONTO.md`. Bis das steht, laeuft alles ueber die lokale Ablage
weiter - kein einziger Aufruf im Spiel merkt den Unterschied.


Warum nichts durcheinandergeraet
--------------------------------

Drei Regeln, und alle drei stehen in der Ablage, nicht im Spielcode:

1. **Jede Zahl traegt eine Kennung, die der Klient vergibt.** Die
    Tabelle hat darauf einen eindeutigen Index. Zweimal geschickt heisst
    einmal gespeichert. Ein Wiederholungsversuch nach einem Abbruch kann
    also nichts doppelt zaehlen.
2. **Erst ins Journal, dann ins Netz.** Was in einer Runde passiert ist,
    liegt in dem Augenblick auf der Platte, in dem die Runde endet. Der
    Abgleich ist ein eigener, spaeterer Schritt, der scheitern und
    beliebig oft wiederholt werden darf.
3. **Das Profil zaehlt seine Fassungen.** Wer speichert, schickt die
    Fassung mit, die er gelesen hat; passt sie nicht mehr, lehnt der
    Server ab und der Klient liest neu. Zwei Rechner koennen sich damit
    nicht gegenseitig still ueberschreiben.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import time
import urllib.error
import urllib.parse
import urllib.request

from . import pfade

# ══════════════════════════════════════════════════ Zugang zum Server
#
# Hier hinein kommen die beiden Werte aus der Supabase-Projektseite. Beide
# duerfen oeffentlich sein - der anon key ist dafuer gedacht. Solange
# `url` leer ist, benutzt das Spiel die lokale Ablage und sagt das auch.
#
# Steht eine Datei `server.json` im Benutzerordner, gilt die davor. So
# kann man ein eigenes Projekt benutzen, ohne den Quelltext zu aendern.
SERVER = {
    "url": "",            # z.B. "https://abcdefghijkl.supabase.co"
    "schluessel": "",     # der oeffentliche anon key
}

SERVER_DATEI = "server.json"
KONTEN_DATEI = "konten.json"
PROFIL_DATEI = "profil.json"
JOURNAL_DATEI = "journal.json"

# Wie lange auf den Server gewartet wird, bevor aufgegeben wird. Kurz:
# der Abgleich laeuft zwar nebenher, aber niemand soll beim Anmelden
# eine halbe Minute vor einem haengenden Fenster sitzen.
WARTEZEIT = 8.0

NAMENSLAENGE = 24
WORTLAENGE = 72           # bcrypt schneidet darueber ohnehin ab


def server_lesen() -> dict:
    """Zugangsdaten, erst aus dem Benutzerordner, sonst aus SERVER."""
    werte = dict(SERVER)
    pfad = pfade.datei(SERVER_DATEI)
    if pfad is not None and pfad.is_file():
        try:
            roh = json.loads(pfad.read_text(encoding="utf-8"))
            if isinstance(roh, dict):
                for k in ("url", "schluessel"):
                    if isinstance(roh.get(k), str) and roh[k].strip():
                        werte[k] = roh[k].strip()
        except (OSError, ValueError):
            pass
    werte["url"] = werte["url"].rstrip("/")
    return werte


# ══════════════════════════════════════════════════ Antwort
#
# Jeder Aufruf gibt dasselbe zurueck, egal welche Ablage antwortet. Kein
# Aufrufer muss unterscheiden, ob gerade eine Datei oder ein Server
# geantwortet hat.

class Antwort:
    __slots__ = ("ok", "daten", "fehler")

    def __init__(self, ok: bool, daten=None, fehler: str = "") -> None:
        self.ok = bool(ok)
        self.daten = daten if daten is not None else {}
        self.fehler = str(fehler)

    def __bool__(self) -> bool:
        return self.ok

    def __repr__(self) -> str:
        return "Antwort(%s, %r)" % (self.ok, self.fehler or self.daten)


def gut(daten=None) -> Antwort:
    return Antwort(True, daten)


def schlecht(fehler: str) -> Antwort:
    return Antwort(False, None, fehler)


# ══════════════════════════════════════════════════ Namen und Kennwoerter

def name_saeubern(name: str) -> str:
    """Ein Kontoname: Buchstaben, Ziffern, Strich, Unterstrich.

    Absichtlich eng. Ein Name steht spaeter ueber der Figur, in der
    Bestenliste und in der Siegtafel; Leerzeichen am Rand, unsichtbare
    Zeichen und Gross-/Kleinschreibung, die zwei Konten gleich aussehen
    laesst, sind dort nur Aerger.
    """
    sauber = "".join(c for c in str(name).strip()
                     if c.isalnum() or c in "-_")
    return sauber[:NAMENSLAENGE]


def name_pruefen(name: str) -> str:
    """Leerer Text, wenn der Name geht, sonst der Grund."""
    if len(name) < 3:
        return "NAME ZU KURZ (MINDESTENS 3)"
    if len(name) > NAMENSLAENGE:
        return "NAME ZU LANG"
    if not name[0].isalnum():
        return "NAME MUSS MIT BUCHSTABE ODER ZIFFER BEGINNEN"
    return ""


def wort_pruefen(wort: str) -> str:
    """Leerer Text, wenn das Kennwort geht, sonst der Grund.

    Bewusst nur eine Laenge und keine Bastelregeln aus Sonderzeichen.
    Was kurze Kennwoerter unsicher macht, ist ihre Kuerze; ein
    erzwungenes Ausrufezeichen macht daraus kein gutes.
    """
    if len(wort) < 8:
        return "KENNWORT ZU KURZ (MINDESTENS 8)"
    if len(wort) > WORTLAENGE:
        return "KENNWORT ZU LANG (HOECHSTENS %d)" % WORTLAENGE
    return ""


def kennung() -> str:
    """Eine Kennung, die nirgends zweimal vorkommt."""
    return "%s-%s" % (format(int(time.time() * 1000), "x"),
                      secrets.token_hex(8))


# ══════════════════════════════════════════════════ Lokale Ablage

class LokaleAblage:
    """Konten und Zahlen in Dateien im Benutzerordner.

    Das ist keine Notloesung, sondern ein vollwertiger Stand: eine
    LAN-Runde im Keller ohne Internet soll Konten, Loadouts und
    Statistik genauso haben wie eine Runde mit Server. Der Gastgeber
    kann Konten fuer seine Gaeste im Terminal anlegen
    (`python -m dustfront --konto <name>`).

    Kennwoerter liegen als scrypt-Hash mit eigenem Salz je Konto. scrypt
    steht in hashlib, also wieder ohne Fremdpaket, und es ist auf
    Rechenaufwand gebaut - wer die Datei stiehlt, hat damit noch keine
    Kennwoerter.
    """

    art = "lokal"

    # Kosten des Hashs. n=2**14 braucht auf einem heutigen Rechner ein
    # paar Zehntelsekunden - beim Anmelden nicht zu merken, beim
    # Durchprobieren von Millionen Woertern sehr wohl.
    SCRYPT = dict(n=2 ** 14, r=8, p=1, dklen=32)

    def __init__(self, ordner=None) -> None:
        self._ordner = ordner          # nur fuer Tests: ein eigener Ort
        self._zwischen = None

    # ---- Dateien -----------------------------------------------------
    def _pfad(self, name: str):
        if self._ordner is not None:
            return self._ordner / name
        return pfade.datei(name)

    def _lesen(self) -> dict:
        pfad = self._pfad(KONTEN_DATEI)
        if pfad is None or not pfad.is_file():
            return {"fassung": 1, "konten": {}}
        try:
            daten = json.loads(pfad.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {"fassung": 1, "konten": {}}
        if not isinstance(daten, dict) or not isinstance(daten.get("konten"), dict):
            return {"fassung": 1, "konten": {}}
        return daten

    def _schreiben(self, daten: dict) -> bool:
        pfad = self._pfad(KONTEN_DATEI)
        if pfad is None:
            return False
        try:
            pfad.parent.mkdir(parents=True, exist_ok=True)
            # Erst daneben schreiben, dann umbenennen. Ein Stromausfall
            # mitten im Schreiben laesst sonst eine halbe Datei zurueck,
            # und die halbe Datei ist alles, was es von den Konten gibt.
            neben = pfad.with_suffix(".neu")
            neben.write_text(json.dumps(daten, indent=1, ensure_ascii=False),
                             encoding="utf-8")
            neben.replace(pfad)
            return True
        except OSError:
            return False

    # ---- Kennwoerter --------------------------------------------------
    @classmethod
    def _hash(cls, wort: str, salz: bytes) -> str:
        roh = hashlib.scrypt(wort.encode("utf-8"), salt=salz, **cls.SCRYPT)
        return base64.b64encode(roh).decode("ascii")

    # ---- Konten -------------------------------------------------------
    def anlegen(self, name: str, wort: str) -> Antwort:
        name = name_saeubern(name)
        fehler = name_pruefen(name) or wort_pruefen(wort)
        if fehler:
            return schlecht(fehler)
        daten = self._lesen()
        schluessel = name.lower()
        if schluessel in daten["konten"]:
            return schlecht("NAME SCHON VERGEBEN")
        salz = os.urandom(16)
        daten["konten"][schluessel] = {
            "kennung": kennung(),
            "name": name,
            "salz": base64.b64encode(salz).decode("ascii"),
            "hash": self._hash(wort, salz),
            "angelegt": int(time.time()),
            "profil": {"fassung": 0, "werte": {}, "loadouts": []},
            "gefechte": {},
        }
        if not self._schreiben(daten):
            return schlecht("KONTEN LASSEN SICH HIER NICHT SPEICHERN")
        return gut({"kennung": daten["konten"][schluessel]["kennung"],
                    "name": name, "sitzung": self._sitzung(schluessel)})

    def anmelden(self, name: str, wort: str) -> Antwort:
        name = name_saeubern(name)
        daten = self._lesen()
        eintrag = daten["konten"].get(name.lower())
        if eintrag is None:
            # Absichtlich dieselbe Auskunft wie beim falschen Kennwort:
            # sonst verraet die Anmeldemaske, welche Namen es gibt.
            return schlecht("NAME ODER KENNWORT FALSCH")
        try:
            salz = base64.b64decode(eintrag["salz"])
        except (KeyError, ValueError):
            return schlecht("KONTO BESCHAEDIGT")
        if not hmac.compare_digest(self._hash(wort, salz),
                                   str(eintrag.get("hash", ""))):
            return schlecht("NAME ODER KENNWORT FALSCH")
        return gut({"kennung": eintrag["kennung"], "name": eintrag["name"],
                    "sitzung": self._sitzung(name.lower())})

    def _sitzung(self, schluessel: str) -> str:
        """Eine Sitzung ist lokal nur der Kontoschluessel.

        Kein Geheimnis noetig: wer die Datei lesen kann, ist ohnehin am
        Rechner angemeldet. Im Netz ist das anders, und dort steht auch
        ein richtiges Token.
        """
        return "lokal:" + schluessel

    def sitzung_pruefen(self, sitzung: str) -> Antwort:
        if not str(sitzung).startswith("lokal:"):
            return schlecht("KEINE LOKALE SITZUNG")
        schluessel = str(sitzung)[6:]
        eintrag = self._lesen()["konten"].get(schluessel)
        if eintrag is None:
            return schlecht("KONTO GIBT ES NICHT MEHR")
        return gut({"kennung": eintrag["kennung"], "name": eintrag["name"],
                    "sitzung": sitzung})

    def abmelden(self, sitzung: str) -> Antwort:
        return gut()

    def namen(self) -> list[str]:
        """Alle angelegten Konten - fuer die Liste im Terminal."""
        return sorted(e["name"] for e in self._lesen()["konten"].values())

    # ---- Profil -------------------------------------------------------
    def profil_lesen(self, sitzung: str) -> Antwort:
        prfg = self.sitzung_pruefen(sitzung)
        if not prfg:
            return prfg
        eintrag = self._lesen()["konten"][str(sitzung)[6:]]
        profil = eintrag.get("profil") or {}
        return gut({"fassung": int(profil.get("fassung", 0)),
                    "werte": dict(profil.get("werte") or {}),
                    "loadouts": list(profil.get("loadouts") or [])})

    def profil_schreiben(self, sitzung: str, profil: dict) -> Antwort:
        prfg = self.sitzung_pruefen(sitzung)
        if not prfg:
            return prfg
        schluessel = str(sitzung)[6:]
        daten = self._lesen()
        eintrag = daten["konten"][schluessel]
        steht = eintrag.get("profil") or {"fassung": 0}
        erwartet = int(profil.get("fassung", 0))
        if erwartet != int(steht.get("fassung", 0)):
            # Jemand anders war schneller. Nicht ueberschreiben, sondern
            # den neuen Stand zurueckgeben - der Aufrufer mischt.
            return Antwort(False, {"fassung": int(steht.get("fassung", 0)),
                                   "werte": dict(steht.get("werte") or {}),
                                   "loadouts": list(steht.get("loadouts") or [])},
                           "PROFIL WURDE ZWISCHENDURCH GEAENDERT")
        neu = {"fassung": erwartet + 1,
               "werte": dict(profil.get("werte") or {}),
               "loadouts": list(profil.get("loadouts") or [])}
        eintrag["profil"] = neu
        if not self._schreiben(daten):
            return schlecht("PROFIL LAESST SICH HIER NICHT SPEICHERN")
        return gut(neu)

    # ---- Zahlen -------------------------------------------------------
    def gefechte_senden(self, sitzung: str, eintraege: list) -> Antwort:
        """Rundenergebnisse ablegen. Doppelte werden still verworfen.

        Der Schluessel ist die Kennung der Partie. Dieselbe Runde zweimal
        zu schicken - nach einem Abbruch zum Beispiel - aendert darum
        nichts an den Zahlen. Das ist die ganze Absicherung gegen
        doppeltes Zaehlen, und sie liegt bewusst in der Ablage und nicht
        im Spiel.
        """
        prfg = self.sitzung_pruefen(sitzung)
        if not prfg:
            return prfg
        schluessel = str(sitzung)[6:]
        daten = self._lesen()
        eintrag = daten["konten"][schluessel]
        gefechte = eintrag.setdefault("gefechte", {})
        genommen = []
        for e in eintraege:
            if not isinstance(e, dict):
                continue
            partie = str(e.get("partie") or "")
            if not partie:
                continue
            gefechte[partie] = e
            genommen.append(partie)
        if not self._schreiben(daten):
            return schlecht("ZAHLEN LASSEN SICH HIER NICHT SPEICHERN")
        return gut({"genommen": genommen})

    def gefechte_lesen(self, sitzung: str) -> Antwort:
        prfg = self.sitzung_pruefen(sitzung)
        if not prfg:
            return prfg
        eintrag = self._lesen()["konten"][str(sitzung)[6:]]
        return gut({"gefechte": list((eintrag.get("gefechte") or {}).values())})


# ══════════════════════════════════════════════════ Netzablage

class NetzAblage:
    """Dasselbe ueber Supabase, mit nichts als urllib.

    Angesprochen werden zwei Teile des Projekts:

        /auth/v1/...       Anmeldedienst (GoTrue). Kennwoerter gehen nur
                           hierhin und werden dort mit bcrypt gehasht.
        /rest/v1/...       Die Tabellen (PostgREST). Jede Anfrage traegt
                           das Token der Sitzung, und der Server laesst
                           ueber RLS nur die eigenen Zeilen durch.

    Kein Aufruf hier blockiert laenger als WARTEZEIT, und keiner wirft:
    was schiefgeht, kommt als Antwort mit ok=False zurueck. Ein Server,
    der nicht antwortet, darf niemals einen Spielstart verhindern.
    """

    art = "netz"

    def __init__(self, url: str = "", schluessel: str = "") -> None:
        werte = server_lesen()
        self.url = (url or werte["url"]).rstrip("/")
        self.schluessel = schluessel or werte["schluessel"]

    @property
    def eingerichtet(self) -> bool:
        return bool(self.url and self.schluessel)

    # ---- HTTP ---------------------------------------------------------
    def _rufen(self, weg: str, daten=None, token: str = "",
               methode: str = "", kopf=None) -> Antwort:
        if not self.eingerichtet:
            return schlecht("KEIN SERVER EINGETRAGEN")
        koerper = None
        if daten is not None:
            koerper = json.dumps(daten).encode("utf-8")
        anfrage = urllib.request.Request(
            self.url + weg, data=koerper,
            method=methode or ("POST" if koerper is not None else "GET"))
        anfrage.add_header("apikey", self.schluessel)
        anfrage.add_header("Authorization",
                           "Bearer " + (token or self.schluessel))
        anfrage.add_header("Content-Type", "application/json")
        anfrage.add_header("Accept", "application/json")
        for k, v in (kopf or {}).items():
            anfrage.add_header(k, v)
        try:
            with urllib.request.urlopen(anfrage, timeout=WARTEZEIT) as antwort:
                roh = antwort.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as fehler:
            try:
                text = fehler.read().decode("utf-8", "replace")
                inhalt = json.loads(text)
                grund = (inhalt.get("msg") or inhalt.get("message")
                         or inhalt.get("error_description") or text)
            except (ValueError, OSError):
                grund = "FEHLER %d" % fehler.code
            return schlecht(str(grund)[:120].upper())
        except (urllib.error.URLError, OSError, ValueError) as fehler:
            return schlecht("SERVER NICHT ERREICHBAR (%s)"
                            % str(getattr(fehler, "reason", fehler))[:60])
        if not roh.strip():
            return gut({})
        try:
            return gut(json.loads(roh))
        except ValueError:
            return schlecht("ANTWORT NICHT LESBAR")

    # ---- Konten -------------------------------------------------------
    @staticmethod
    def _postfach(name: str) -> str:
        """Supabase will eine Adresse, das Spiel will einen Namen.

        Angemeldet wird darum mit `<name>@spieler.dustfront`, einer
        Domaene, die es nicht gibt und nie geben wird. Eine echte
        Adresse wird nicht abgefragt: sie waere fuer ein Schulprojekt
        eine Menge personenbezogener Daten, die niemand braucht.
        """
        return "%s@spieler.dustfront" % name.lower()

    def anlegen(self, name: str, wort: str) -> Antwort:
        name = name_saeubern(name)
        fehler = name_pruefen(name) or wort_pruefen(wort)
        if fehler:
            return schlecht(fehler)
        antwort = self._rufen("/auth/v1/signup", {
            "email": self._postfach(name), "password": wort,
            "data": {"name": name},
        })
        if not antwort:
            return antwort
        sitzung = self._sitzung_lesen(antwort.daten, name)
        if not sitzung:
            return sitzung
        # Das Profil wird beim Anlegen gleich mit angelegt, damit es
        # spaeter nie den Fall "es gibt noch keines" gibt.
        self._rufen("/rest/v1/profil", {
            "konto": sitzung.daten["kennung"], "name": name,
            "fassung": 0, "werte": {}, "loadouts": [],
        }, token=sitzung.daten["sitzung"],
            kopf={"Prefer": "resolution=merge-duplicates"})
        return sitzung

    def anmelden(self, name: str, wort: str) -> Antwort:
        name = name_saeubern(name)
        antwort = self._rufen("/auth/v1/token?grant_type=password", {
            "email": self._postfach(name), "password": wort,
        })
        if not antwort:
            # Der Server sagt gern genau, was falsch war. Hier nicht:
            # sonst laesst sich abfragen, welche Namen es gibt.
            return schlecht("NAME ODER KENNWORT FALSCH")
        return self._sitzung_lesen(antwort.daten, name)

    def _sitzung_lesen(self, daten, name: str) -> Antwort:
        if not isinstance(daten, dict):
            return schlecht("ANTWORT NICHT LESBAR")
        token = daten.get("access_token")
        nutzer = daten.get("user") or {}
        wer = nutzer.get("id") or (daten.get("id") if "id" in daten else "")
        if not token or not wer:
            # signup ohne Sitzung heisst: der Server will eine Bestaetigung
            # per Post. Fuer dieses Spiel ist das ausgeschaltet, aber wenn
            # jemand ein eigenes Projekt aufsetzt, soll er es erfahren.
            return schlecht("KONTO ANGELEGT, ABER NOCH NICHT BESTAETIGT")
        return gut({"kennung": str(wer), "name": name, "sitzung": str(token),
                    "erneuern": str(daten.get("refresh_token") or "")})

    def sitzung_pruefen(self, sitzung: str) -> Antwort:
        antwort = self._rufen("/auth/v1/user", token=sitzung)
        if not antwort:
            return antwort
        nutzer = antwort.daten if isinstance(antwort.daten, dict) else {}
        wer = nutzer.get("id")
        if not wer:
            return schlecht("SITZUNG ABGELAUFEN")
        name = ((nutzer.get("user_metadata") or {}).get("name")
                or str(nutzer.get("email", "")).split("@")[0])
        return gut({"kennung": str(wer), "name": name_saeubern(name),
                    "sitzung": sitzung})

    def erneuern(self, marke: str) -> Antwort:
        """Eine abgelaufene Sitzung mit dem Erneuerungstoken auffrischen."""
        antwort = self._rufen("/auth/v1/token?grant_type=refresh_token",
                              {"refresh_token": marke})
        if not antwort:
            return antwort
        return self._sitzung_lesen(antwort.daten, "")

    def abmelden(self, sitzung: str) -> Antwort:
        return self._rufen("/auth/v1/logout", {}, token=sitzung)

    # ---- Profil -------------------------------------------------------
    def profil_lesen(self, sitzung: str) -> Antwort:
        antwort = self._rufen(
            "/rest/v1/profil?select=fassung,werte,loadouts&limit=1",
            token=sitzung)
        if not antwort:
            return antwort
        zeilen = antwort.daten if isinstance(antwort.daten, list) else []
        if not zeilen:
            return gut({"fassung": 0, "werte": {}, "loadouts": []})
        zeile = zeilen[0]
        return gut({"fassung": int(zeile.get("fassung", 0)),
                    "werte": dict(zeile.get("werte") or {}),
                    "loadouts": list(zeile.get("loadouts") or [])})

    def profil_schreiben(self, sitzung: str, profil: dict) -> Antwort:
        """Nur schreiben, wenn die Fassung noch stimmt.

        Der Filter `fassung=eq.<gelesen>` macht das Ganze: die Zeile
        wird nur veraendert, wenn sie seit dem Lesen niemand angefasst
        hat. Kommt nichts zurueck, war jemand anders schneller - dann
        wird neu gelesen statt blind ueberschrieben.
        """
        erwartet = int(profil.get("fassung", 0))
        antwort = self._rufen(
            "/rest/v1/profil?fassung=eq.%d" % erwartet,
            {"fassung": erwartet + 1,
             "werte": dict(profil.get("werte") or {}),
             "loadouts": list(profil.get("loadouts") or [])},
            token=sitzung, methode="PATCH",
            kopf={"Prefer": "return=representation"})
        if not antwort:
            return antwort
        zeilen = antwort.daten if isinstance(antwort.daten, list) else []
        if not zeilen:
            neu = self.profil_lesen(sitzung)
            return Antwort(False, neu.daten if neu else None,
                           "PROFIL WURDE ZWISCHENDURCH GEAENDERT")
        zeile = zeilen[0]
        return gut({"fassung": int(zeile.get("fassung", erwartet + 1)),
                    "werte": dict(zeile.get("werte") or {}),
                    "loadouts": list(zeile.get("loadouts") or [])})

    # ---- Zahlen -------------------------------------------------------
    def gefechte_senden(self, sitzung: str, eintraege: list) -> Antwort:
        """Rundenergebnisse hochladen, doppelsicher.

        `resolution=ignore-duplicates` zusammen mit dem eindeutigen
        Index auf (partie, konto) heisst: dieselbe Runde zweimal zu
        schicken aendert nichts. Genau darum darf der Abgleich beliebig
        oft wiederholt werden, ohne dass Zahlen wachsen, die nicht
        sollen.
        """
        if not eintraege:
            return gut({"genommen": []})
        antwort = self._rufen(
            "/rest/v1/gefecht", list(eintraege), token=sitzung,
            kopf={"Prefer": "resolution=ignore-duplicates,return=minimal"})
        if not antwort:
            return antwort
        return gut({"genommen": [str(e.get("partie")) for e in eintraege
                                 if isinstance(e, dict) and e.get("partie")]})

    def gefechte_lesen(self, sitzung: str, hoechstens: int = 200) -> Antwort:
        antwort = self._rufen(
            "/rest/v1/gefecht?select=*&order=gespielt.desc&limit=%d" % hoechstens,
            token=sitzung)
        if not antwort:
            return antwort
        zeilen = antwort.daten if isinstance(antwort.daten, list) else []
        return gut({"gefechte": zeilen})


def waehlen(lokal_erzwingen: bool = False):
    """Die Ablage, die gerade passt.

    Ohne eingetragenen Server wird gar nicht erst gefragt - das Spiel
    laeuft dann vollstaendig lokal und sagt das in der Anmeldemaske.
    """
    if not lokal_erzwingen:
        netz = NetzAblage()
        if netz.eingerichtet:
            return netz
    return LokaleAblage()
