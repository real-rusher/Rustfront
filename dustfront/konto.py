"""
DUSTFRONT - Konto, Loadouts und das Journal
===========================================

Das eine Ding, mit dem das Spiel redet. Wo die Daten wirklich liegen,
entscheidet `ablage.py`; hier steht, **was** ein Konto ist und wie es sich
verhaelt, wenn das Netz nicht mitspielt.

Drei Dinge haengen daran:

    Anmeldung   Name und Kennwort, eine Sitzung, die einen Neustart
                ueberlebt. Auf einem frisch heruntergeladenen Spiel
                reicht die Anmeldung - es ist nichts einzurichten.
    Profil      Was zum Spieler gehoert und nicht zum Rechner: seine
                Einstellungen und seine drei Loadouts.
    Journal     Was in den Runden passiert ist.


Warum das Journal so gebaut ist
-------------------------------

Die Bedingung war, dass es **nie** Fehler oder Abweichungen in den Zahlen
gibt. Ein Netz erfuellt das nicht von sich aus: eine Antwort kann
ausbleiben, nachdem der Server schon geschrieben hat, und dann weiss der
Klient nicht, ob er nochmal schicken soll. Schickt er nicht, fehlt die
Runde. Schickt er doch, zaehlt sie zweimal. Beides ist falsch.

Darum wird nicht "geschickt", sondern **abgeglichen**:

1. Am Rundenende bekommt die Partie eine Kennung, und ihr Ergebnis geht
   sofort ins Journal auf der Platte. Ab diesem Augenblick kann es nicht
   mehr verloren gehen, egal was das Netz tut.
2. Der Abgleich schickt alles, was noch nicht bestaetigt ist. Die Tabelle
   hat einen eindeutigen Index auf (Partie, Konto): zweimal schicken
   heisst einmal speichern. Ein Wiederholungsversuch ist damit immer
   erlaubt und immer harmlos.
3. Erst wenn der Server bestaetigt, wird die Runde im Journal als
   abgeglichen abgehakt. Bleibt die Antwort aus, bleibt sie offen und
   geht beim naechsten Mal wieder mit.

Dieselbe Ueberlegung gilt fuer das Profil, nur mit einem Zaehler statt
einer Kennung: wer speichert, sagt, welche Fassung er gelesen hat. Passt
sie nicht mehr, lehnt der Server ab, und der Klient liest neu und mischt.
Damit kann ein zweiter Rechner die Loadouts nicht still ueberschreiben.


Warum ein eigener Faden
-----------------------

Der Netzcode des Gefechts kommt bewusst ohne Threads aus - eine
Spielschleife hat schon eine Schleife. Fuer das Konto ist das anders:
eine Anmeldung ueber das Internet dauert ein paar hundert Millisekunden,
und die darf das Bild nicht anhalten. Also **ein** Faden, der nichts tut
als HTTP, und eine Schlange, aus der die Spielschleife die Ergebnisse
abholt. Er beruehrt keinen Spielzustand; alles, was mit dem Ergebnis
passiert, passiert im Hauptfaden in `schritt()`.
"""

from __future__ import annotations

import json
import queue
import threading
import time

from . import ablage
from . import config as K
from . import pfade

SITZUNG_DATEI = "sitzung.json"
# Die eigene Spielerkosmetik, wie sie zuletzt vom Server kam. Damit sie
# auch ohne Netz da ist - und damit nicht jeder Start sie neu laedt.
KOSMETIK_DATEI = "kosmetik.json"
JOURNAL_DATEI = "journal.json"


# ══════════════════════════════════════════════════ Loadouts

def loadout_saeubern(roh) -> dict | None:
    """Ein Loadout aus fremder Hand pruefen und zurechtziehen.

    "Fremde Hand" heisst hier wirklich jede: eine Datei, die jemand von
    Hand geaendert hat, eine Antwort vom Server, eine aeltere Fassung des
    Spiels mit anderen Waffen. Was nicht passt, wird nicht abgelehnt,
    sondern aufgefuellt - ein Loadout, das eine Waffe zu wenig hat, soll
    die Runde nicht verhindern.
    """
    if not isinstance(roh, dict):
        return None
    lo = K.LOADOUT
    name = "".join(c for c in str(roh.get("name", "")).strip().upper()
                   if c.isalnum() or c in " -_")[:lo["namenslaenge"]]
    waffen = [w for w in (roh.get("waffen") or [])
              if isinstance(w, str) and w in lo["auswahl_waffen"]]
    wuerfe = [w for w in (roh.get("wuerfe") or [])
              if isinstance(w, str) and w in lo["auswahl_wuerfe"]]
    # Doppeltes entfernen, Reihenfolge behalten.
    waffen = list(dict.fromkeys(waffen))[:lo["waffen"]]
    wuerfe = list(dict.fromkeys(wuerfe))[:lo["wuerfe"]]
    for auswahl, liste, anzahl in ((lo["auswahl_waffen"], waffen, lo["waffen"]),
                                   (lo["auswahl_wuerfe"], wuerfe, lo["wuerfe"])):
        for wahl in auswahl:
            if len(liste) >= anzahl:
                break
            if wahl not in liste:
                liste.append(wahl)
    return {"name": name or "SATZ", "waffen": waffen, "wuerfe": wuerfe}


def loadout_vorlagen() -> list[dict]:
    """Die drei Saetze, mit denen ein neues Konto anfaengt."""
    return [loadout_saeubern(dict(v)) for v in K.LOADOUT["vorlagen"]]


def loadouts_saeubern(roh) -> list[dict]:
    """Die Liste auf die richtige Laenge bringen, ohne etwas zu verlieren."""
    liste = []
    if isinstance(roh, list):
        for eintrag in roh[:K.LOADOUT["plaetze"]]:
            sauber = loadout_saeubern(eintrag)
            if sauber is not None:
                liste.append(sauber)
    vorlagen = loadout_vorlagen()
    while len(liste) < K.LOADOUT["plaetze"]:
        liste.append(vorlagen[len(liste) % len(vorlagen)])
    return liste


def hotbar_aus_loadout(lo: dict) -> list[str]:
    """Welche Plaetze eine Figur mit diesem Loadout traegt.

    Die Reihenfolge folgt HOTBAR und nicht der Reihenfolge im Loadout:
    wer sich daran gewoehnt hat, dass die Schrotflinte rechts von dem
    Sturmgewehr liegt, soll sie nicht plaetzeweise suchen muessen.
    """
    dabei = set(lo.get("waffen") or []) | set(lo.get("wuerfe") or [])
    return [w for w in K.HOTBAR if w in dabei]


# ══════════════════════════════════════════════════ Journal

class Journal:
    """Was in den Runden passiert ist, auf der Platte, mit Haken dran.

    Eine Datei, eine Liste, je Eintrag eine Partiekennung und ein
    Merkzeichen, ob der Server sie bestaetigt hat. Mehr braucht es nicht,
    und weniger reicht nicht.
    """

    def __init__(self, ordner=None) -> None:
        self._ordner = ordner
        self.eintraege: list[dict] = []
        self.laden()

    def _pfad(self):
        if self._ordner is not None:
            return self._ordner / JOURNAL_DATEI
        return pfade.datei(JOURNAL_DATEI)

    def laden(self) -> None:
        pfad = self._pfad()
        self.eintraege = []
        if pfad is None or not pfad.is_file():
            return
        try:
            daten = json.loads(pfad.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return
        for e in (daten.get("eintraege") or []) if isinstance(daten, dict) else []:
            if isinstance(e, dict) and e.get("partie"):
                self.eintraege.append(e)

    def speichern(self) -> bool:
        pfad = self._pfad()
        if pfad is None:
            return False
        try:
            pfad.parent.mkdir(parents=True, exist_ok=True)
            neben = pfad.with_suffix(".neu")
            neben.write_text(json.dumps({"fassung": 1,
                                         "eintraege": self.eintraege},
                                        indent=1, ensure_ascii=False),
                             encoding="utf-8")
            neben.replace(pfad)
            return True
        except OSError:
            return False

    def dazu(self, eintrag: dict) -> dict:
        """Eine Runde eintragen. Dieselbe Partie nur einmal.

        Das `abgeglichen`-Feld wird hier gesetzt und nicht vom Aufrufer:
        eine Runde, die frisch hereinkommt, ist nie abgeglichen, und das
        soll niemand versehentlich anders behaupten koennen.
        """
        eintrag = dict(eintrag)
        eintrag["abgeglichen"] = False
        partie = str(eintrag.get("partie") or "")
        for i, alt in enumerate(self.eintraege):
            if str(alt.get("partie")) == partie:
                # Schon da. Der bestehende Haken bleibt, sonst wuerde
                # eine zweite Meldung derselben Runde sie wieder oeffnen.
                eintrag["abgeglichen"] = bool(alt.get("abgeglichen"))
                self.eintraege[i] = eintrag
                self.speichern()
                return eintrag
        self.eintraege.append(eintrag)
        # Ueberlauf: das Aelteste, das schon abgeglichen ist, fliegt
        # zuerst. Offene Eintraege bleiben, auch wenn es viele werden -
        # sie sind der einzige Ort, an dem diese Runden noch stehen.
        grenze = K.KONTO["journal_hoechstens"]
        if len(self.eintraege) > grenze:
            offen = [e for e in self.eintraege if not e.get("abgeglichen")]
            fertig = [e for e in self.eintraege if e.get("abgeglichen")]
            behalten = max(0, grenze - len(offen))
            self.eintraege = fertig[-behalten:] + offen if behalten else offen
        self.speichern()
        return eintrag

    def offen(self) -> list[dict]:
        return [e for e in self.eintraege if not e.get("abgeglichen")]

    def abhaken(self, partien) -> int:
        """Bestaetigte Runden abhaken. Gibt zurueck, wie viele es waren."""
        marken = {str(p) for p in partien}
        anzahl = 0
        for e in self.eintraege:
            if str(e.get("partie")) in marken and not e.get("abgeglichen"):
                e["abgeglichen"] = True
                anzahl += 1
        if anzahl:
            self.speichern()
        return anzahl

    @staticmethod
    def abgebrochen(eintrag: dict) -> bool:
        """Endete diese Runde vor ihrer Zeit? (seit 0.31)

        Steht in "ende"; aeltere Zeilen haben das Feld nicht und sind
        regulaer - abgebrochene wurden vor 0.31 gar nicht gebucht. Eine
        Zeile, die ohne die Spalte hochging (alter Server, siehe
        NetzAblage.gefechte_senden), traegt es noch in den Werten.
        """
        if str(eintrag.get("ende") or "") == "abgebrochen":
            return True
        werte = eintrag.get("werte") or {}
        try:
            return float(werte.get("abgebrochen", 0) or 0) > 0
        except (TypeError, ValueError, AttributeError):
            return False

    def summe(self, version: str = "", abgebrochene: bool = False) -> dict:
        """Alle Runden im Journal zu einer Uebersicht zusammengerechnet.

        Gerechnet wird lokal und nicht auf dem Server. Damit stimmt die
        Anzeige auch ohne Netz, und sie stimmt sofort - man schiesst
        jemanden ab und sieht es, ohne auf eine Antwort zu warten.

        Abgebrochene Runden zaehlen nicht mit (`abgebrochene=True` nimmt
        sie dazu). Sonst stimmt "Abschuesse je Runde" nicht mehr: eine
        Runde, die nach einer Minute endete, hat wenige Abschuesse und
        zaehlt dabei nicht als Runde. Nur wie viele es waren, steht
        immer da ("abgebrochen").

        `version`: nur die Runden dieser Fassung des Spiels. Nach einer
        Aenderung am Gleichgewicht - Zombies mit weniger Leben - sind die
        Zahlen davor und danach nicht dieselben, und so lassen sie sich
        auseinanderhalten.
        """
        art = {s: a for s, _t, a in K.WERTE}
        summe = {s: 0 for s in art}
        waffen: dict[str, dict] = {}
        abbrueche = 0
        for e in self.eintraege:
            if version and str(e.get("version") or "") != version:
                continue
            if self.abgebrochen(e):
                abbrueche += 1
                if not abgebrochene:
                    continue
            werte = e.get("werte") or {}
            for s, a in art.items():
                try:
                    wert = float(werte.get(s, 0) or 0)
                except (TypeError, ValueError):
                    continue
                if a == "bestes":
                    summe[s] = max(summe[s], wert)
                else:
                    summe[s] += wert
            for waffe, zahlen in (e.get("waffen") or {}).items():
                if not isinstance(zahlen, dict):
                    continue
                ziel = waffen.setdefault(waffe, {s: 0 for s in K.WAFFEN_WERTE})
                for s in K.WAFFEN_WERTE:
                    try:
                        ziel[s] += float(zahlen.get(s, 0) or 0)
                    except (TypeError, ValueError):
                        pass
        # Ganze Zahlen bleiben ganze Zahlen. 17.0 Abschuesse sieht falsch
        # aus, auch wenn es richtig ist.
        summe["abgebrochen"] = abbrueche
        for s, wert in summe.items():
            if float(wert).is_integer():
                summe[s] = int(wert)
        summe["waffen"] = waffen
        return summe

    def versionen(self) -> list[str]:
        """Mit welchen Fassungen des Spiels gespielt wurde, die neueste vorn."""
        def schluessel(v: str):
            try:
                return tuple(int(t) for t in v.split("."))
            except ValueError:
                return (-1,)
        alle = {str(e.get("version") or "") for e in self.eintraege}
        return sorted((v for v in alle if v), key=schluessel, reverse=True)


# ══════════════════════════════════════════════════ Der Faden fuer das Netz

class Werk:
    """Ein Faden, der Auftraege abarbeitet, und eine Schlange zurueck.

    Absichtlich winzig: hineingegeben wird eine Funktion ohne Argumente,
    heraus kommt, was sie zurueckgegeben hat. Der Faden beruehrt keinen
    Spielzustand - was mit dem Ergebnis passiert, passiert im Hauptfaden.
    """

    def __init__(self) -> None:
        self._hinein: queue.Queue = queue.Queue()
        self._heraus: queue.Queue = queue.Queue()
        self._faden = threading.Thread(target=self._laufen, daemon=True)
        self._laeuft = True
        self._faden.start()

    def _laufen(self) -> None:
        while self._laeuft:
            auftrag = self._hinein.get()
            if auftrag is None:
                break
            marke, arbeit = auftrag
            try:
                ergebnis = arbeit()
            except Exception as fehler:            # noqa: BLE001
                # Ein Faden, der an einer Ausnahme stirbt, nimmt jede
                # weitere Anmeldung mit. Also wird alles gefangen und als
                # Fehlantwort weitergegeben.
                ergebnis = ablage.schlecht("UNERWARTETER FEHLER: %s"
                                           % str(fehler)[:60].upper())
            self._heraus.put((marke, ergebnis))

    def auftrag(self, marke: str, arbeit) -> None:
        self._hinein.put((marke, arbeit))

    def fertig(self) -> list[tuple]:
        raus = []
        while True:
            try:
                raus.append(self._heraus.get_nowait())
            except queue.Empty:
                break
        return raus

    @property
    def beschaeftigt(self) -> bool:
        return not self._hinein.empty()

    def schliessen(self) -> None:
        self._laeuft = False
        self._hinein.put(None)


# ══════════════════════════════════════════════════ Konto

class Konto:
    """Der angemeldete Spieler - oder niemand.

    Ohne Anmeldung laeuft alles weiter: die Loadouts stehen dann in den
    Vorlagen, das Journal sammelt trotzdem, und wer sich spaeter anmeldet,
    nimmt sein bisher Gespieltes mit. Ein Konto ist ein Angebot, keine
    Bedingung - ein Spiel, das ohne Anmeldung nicht startet, ist kaputt.
    """

    def __init__(self, ablage_=None, ordner=None, mit_faden: bool = True) -> None:
        self.ablage = ablage_ if ablage_ is not None else ablage.waehlen()
        self.journal = Journal(ordner)
        self._ordner = ordner
        self.kennung = ""
        self.name = ""
        self.sitzung = ""
        self.erneuern_marke = ""
        self.profil_fassung = 0
        self.werte: dict = {}
        self.loadouts: list[dict] = loadouts_saeubern([])
        self.gewaehlt = 0
        self.hinweis = ""
        self.fehler = ""
        self.laeuft = ""                # Name des laufenden Auftrags
        self._werk = Werk() if mit_faden else None
        self._seit_abgleich = 0.0
        self._ruhe = 0.0
        # Ton und Bild fuer die Blendgranate (spielerkosmetik.py), oder
        # None. Kommt vom Server und liegt danach auch auf der Platte.
        self.kosmetik = None
        self.kosmetik_fehler = ""
        self.sitzung_laden()
        self._kosmetik_merken_laden()

    # ---- Zustand ------------------------------------------------------
    @property
    def angemeldet(self) -> bool:
        return bool(self.kennung and self.sitzung)

    @property
    def art(self) -> str:
        return getattr(self.ablage, "art", "lokal")

    @property
    def mit_server(self) -> bool:
        return self.art == "netz"

    def beschreibung(self) -> str:
        """Ein Satz fuer die Anmeldemaske, damit klar ist, wo man ist."""
        if self.mit_server:
            return "KONTO GILT AUF JEDEM RECHNER"
        return "KONTO GILT AUF DIESEM RECHNER"

    @property
    def loadout(self) -> dict:
        i = max(0, min(len(self.loadouts) - 1, self.gewaehlt))
        return self.loadouts[i]

    # ---- Sitzung ueber einen Neustart hinweg ---------------------------
    def _sitzungspfad(self):
        if self._ordner is not None:
            return self._ordner / SITZUNG_DATEI
        return pfade.datei(SITZUNG_DATEI)

    def sitzung_laden(self) -> bool:
        """Die letzte Sitzung wieder aufnehmen, ohne zu fragen.

        Geprueft wird sie **nicht** sofort beim Start - das waere eine
        Netzanfrage, bevor das erste Bild steht. Sie gilt erst einmal,
        und wenn sich herausstellt, dass sie abgelaufen ist, fliegt sie
        beim ersten Aufruf heraus, der sie braucht.
        """
        pfad = self._sitzungspfad()
        if pfad is None or not pfad.is_file():
            return False
        try:
            daten = json.loads(pfad.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return False
        if not isinstance(daten, dict) or daten.get("art") != self.art:
            # Die Sitzung einer anderen Ablage nuetzt nichts: ein lokales
            # Token ist auf dem Server nichts wert und umgekehrt.
            return False
        self.kennung = str(daten.get("kennung") or "")
        self.name = ablage.name_saeubern(daten.get("name") or "")
        self.sitzung = str(daten.get("sitzung") or "")
        self.erneuern_marke = str(daten.get("erneuern") or "")
        self.profil_fassung = int(daten.get("fassung") or 0)
        self.werte = dict(daten.get("werte") or {})
        self.loadouts = loadouts_saeubern(daten.get("loadouts"))
        self.gewaehlt = int(daten.get("gewaehlt") or 0)
        return self.angemeldet

    def sitzung_speichern(self) -> bool:
        pfad = self._sitzungspfad()
        if pfad is None:
            return False
        try:
            pfad.parent.mkdir(parents=True, exist_ok=True)
            neben = pfad.with_suffix(".neu")
            neben.write_text(json.dumps({
                "art": self.art, "kennung": self.kennung, "name": self.name,
                "sitzung": self.sitzung, "erneuern": self.erneuern_marke,
                "fassung": self.profil_fassung, "werte": self.werte,
                "loadouts": self.loadouts, "gewaehlt": self.gewaehlt,
            }, indent=1, ensure_ascii=False), encoding="utf-8")
            neben.replace(pfad)
            return True
        except OSError:
            return False

    def sitzung_loeschen(self) -> None:
        pfad = self._sitzungspfad()
        if pfad is not None:
            try:
                pfad.unlink()
            except OSError:
                pass

    # ---- Anmelden und anlegen -----------------------------------------
    def anmelden(self, name: str, wort: str) -> None:
        """Anmelden. Laeuft nebenher; das Ergebnis kommt in schritt()."""
        self._starten("anmelden", lambda: self.ablage.anmelden(name, wort))

    def anlegen(self, name: str, wort: str) -> None:
        self._starten("anlegen", lambda: self.ablage.anlegen(name, wort))

    def abmelden(self) -> None:
        """Abmelden. Das Journal bleibt, die Sitzung geht.

        Bewusst in dieser Reihenfolge: was gespielt wurde, gehoert dem
        Rechner genauso wie dem Konto, und wer sich abmeldet, will nicht
        seine Runden loeschen.
        """
        if self.sitzung:
            sitzung = self.sitzung
            self._starten("abmelden", lambda: self.ablage.abmelden(sitzung))
        self.kennung = ""
        self.name = ""
        self.sitzung = ""
        self.erneuern_marke = ""
        self.profil_fassung = 0
        self.sitzung_loeschen()
        self.kosmetik = None
        self._kosmetik_merken(None, "", "")
        self.hinweis = "ABGEMELDET"

    def _starten(self, marke: str, arbeit) -> None:
        self.fehler = ""
        self.hinweis = ""
        self.laeuft = marke
        if self._werk is None:
            # Ohne Faden - so laufen die Tests - wird sofort gearbeitet.
            self._ergebnis(marke, arbeit())
            return
        self._werk.auftrag(marke, arbeit)

    # ---- Profil und Loadouts ------------------------------------------
    def profil_holen(self) -> None:
        if not self.angemeldet:
            return
        sitzung = self.sitzung
        self._starten("profil_lesen",
                      lambda: self.ablage.profil_lesen(sitzung))

    def kosmetik_holen(self) -> None:
        """Die eigene Kosmetik vom Server holen. Laeuft nebenher.

        Still und nicht ueber `_starten`: das loescht Hinweis und Fehler
        und setzt `laeuft` - richtig fuer etwas, das der Spieler angestossen
        hat, falsch fuer etwas, das beim Betreten jeder Lobby mitlaeuft. Ein
        "ANGEMELDET" oder ein echter Fehler bliebe sonst nicht stehen.
        """
        if not self.angemeldet:
            return
        sitzung = self.sitzung
        arbeit = lambda: self.ablage.kosmetik_lesen(sitzung)
        if self._werk is None:
            self._ergebnis("kosmetik_lesen", arbeit())
            return
        self._werk.auftrag("kosmetik_lesen", arbeit)

    def _kosmetik_gelesen(self, antwort) -> None:
        """Pruefen wie jedes fremde Paket - auch das eigene vom Server."""
        from . import spielerkosmetik
        if not antwort:
            # Meist: die Tabelle ist noch nicht angelegt. Dann gilt, was
            # auf der Platte liegt, und das Spiel laeuft ohne weiter.
            self.kosmetik_fehler = antwort.fehler
            return
        ton = str(antwort.daten.get("ton") or "")
        bild = str(antwort.daten.get("bild") or "")
        music_kit = str(antwort.daten.get("music_kit") or "")
        if not ton and not bild and not music_kit:
            self.kosmetik = None
            self.kosmetik_fehler = ""
            self._kosmetik_merken(None, "", "")
            return
        try:
            self.kosmetik = spielerkosmetik.aus_konto(ton, bild, music_kit)
            self.kosmetik_fehler = ""
            self._kosmetik_merken(self.kosmetik, ton, bild, music_kit)
        except ValueError as fehler:
            # Auf dem Server liegt jetzt etwas, das nicht gilt. Dann auch
            # nicht mehr das Alte von der Platte - sonst kaeme es beim
            # naechsten Start wieder, und keiner wuesste, warum.
            self.kosmetik = None
            self.kosmetik_fehler = str(fehler)
            self._kosmetik_merken(None, "", "")

    def _kosmetik_pfad(self):
        if self._ordner is not None:
            return self._ordner / KOSMETIK_DATEI
        return pfade.datei(KOSMETIK_DATEI)

    def _kosmetik_merken(self, kosmetik, ton: str, bild: str,
                          music_kit: str = "") -> None:
        pfad = self._kosmetik_pfad()
        if pfad is None:
            return
        try:
            if kosmetik is None:
                if pfad.is_file():
                    pfad.unlink()
                return
            pfad.parent.mkdir(parents=True, exist_ok=True)
            pfad.write_text(json.dumps({"konto": self.kennung, "ton": ton,
                                        "bild": bild, "music_kit": music_kit}),
                            encoding="utf-8")
        except OSError:
            pass

    def _kosmetik_merken_laden(self) -> None:
        """Was zuletzt vom Server kam - aber nur fuer dasselbe Konto."""
        from . import spielerkosmetik
        pfad = self._kosmetik_pfad()
        if pfad is None or not pfad.is_file() or not self.angemeldet:
            return
        try:
            daten = json.loads(pfad.read_text(encoding="utf-8"))
            if not isinstance(daten, dict) or daten.get("konto") != self.kennung:
                return
            self.kosmetik = spielerkosmetik.aus_konto(
                str(daten.get("ton") or ""), str(daten.get("bild") or ""),
                str(daten.get("music_kit") or ""))
        except (OSError, ValueError):
            self.kosmetik = None

    def profil_sichern(self) -> None:
        """Einstellungen und Loadouts ablegen.

        Ohne Anmeldung passiert nichts Schlimmes: die Werte stehen dann
        in der Sitzungsdatei und gelten auf diesem Rechner. Sie gehen
        beim naechsten Anmelden mit hoch.
        """
        self.sitzung_speichern()
        if not self.angemeldet:
            return
        sitzung = self.sitzung
        profil = {"fassung": self.profil_fassung, "werte": dict(self.werte),
                  "loadouts": list(self.loadouts)}
        self._starten("profil_schreiben",
                      lambda: self.ablage.profil_schreiben(sitzung, profil))

    def loadout_setzen(self, platz: int, lo: dict) -> dict:
        """Ein Loadout aendern und ablegen. Gibt das Ergebnis zurueck."""
        platz = max(0, min(K.LOADOUT["plaetze"] - 1, int(platz)))
        sauber = loadout_saeubern(lo) or loadout_vorlagen()[0]
        while len(self.loadouts) <= platz:
            self.loadouts.append(loadout_vorlagen()[0])
        self.loadouts[platz] = sauber
        self.profil_sichern()
        return sauber

    def loadout_waehlen(self, platz: int) -> dict:
        self.gewaehlt = max(0, min(len(self.loadouts) - 1, int(platz)))
        self.sitzung_speichern()
        return self.loadout

    @property
    def loadout_gewaehlt_je(self) -> bool:
        """Hat sich hier schon einmal jemand ein Loadout zusammengestellt?

        Danach richtet sich, ob beim Start gefragt wird. Wer schon einen
        Satz gespeichert hat, soll nicht jedes Mal wieder eine Maske
        wegklicken.
        """
        return bool(self.werte.get("loadout_gewaehlt"))

    def loadout_bestaetigen(self) -> None:
        self.werte["loadout_gewaehlt"] = True
        self.profil_sichern()

    # ---- Werte einer Runde --------------------------------------------
    def runde_eintragen(self, eintrag: dict) -> dict:
        """Eine gespielte Runde ins Journal, und Abgleich anstossen.

        Aufgerufen wird das genau einmal je Runde und nur dort, wo die
        Zahlen sicher vollstaendig sind. Ob der Server erreichbar ist,
        spielt hier keine Rolle - deswegen gibt es das Journal.
        """
        eintrag = dict(eintrag)
        eintrag.setdefault("partie", ablage.kennung())
        eintrag.setdefault("gespielt", int(time.time()))
        if self.kennung:
            eintrag["konto"] = self.kennung
        genommen = self.journal.dazu(eintrag)
        self._seit_abgleich = K.KONTO["abgleich_takt"]     # gleich versuchen
        return genommen

    def abgleichen(self) -> bool:
        """Alles Offene hochschicken. True, wenn ein Versuch losging."""
        if not self.angemeldet or self.laeuft or self._ruhe > 0.0:
            return False
        offen = self.journal.offen()
        if not offen:
            return False
        sitzung = self.sitzung
        # Nur die Felder, die der Server kennt - `abgeglichen` ist eine
        # Notiz fuer das Journal und gehoert nicht in die Tabelle.
        paket = []
        for e in offen:
            zeile = {k: v for k, v in e.items() if k != "abgeglichen"}
            zeile["konto"] = self.kennung
            paket.append(zeile)
        self._starten("gefechte_senden",
                      lambda: self.ablage.gefechte_senden(sitzung, paket))
        return True

    def uebersicht(self) -> dict:
        """Die Zahlen, wie sie angezeigt werden - immer aus dem Journal."""
        return self.journal.summe()

    # ---- Schleife -----------------------------------------------------
    def schritt(self, dt: float) -> None:
        """Ergebnisse abholen und gelegentlich abgleichen.

        Wird aus der Spielschleife aufgerufen. Alles, was den Zustand des
        Kontos aendert, passiert hier - nie im Faden.
        """
        self._ruhe = max(0.0, self._ruhe - dt)
        if self._werk is not None:
            for marke, ergebnis in self._werk.fertig():
                self._ergebnis(marke, ergebnis)
        self._seit_abgleich += dt
        if self._seit_abgleich >= K.KONTO["abgleich_takt"]:
            self._seit_abgleich = 0.0
            self.abgleichen()

    def _ergebnis(self, marke: str, antwort) -> None:
        if self.laeuft == marke:
            self.laeuft = ""
        if marke in ("anmelden", "anlegen"):
            self._angemeldet(marke, antwort)
        elif marke == "profil_lesen":
            self._profil_gelesen(antwort)
        elif marke == "profil_schreiben":
            self._profil_geschrieben(antwort)
        elif marke == "gefechte_senden":
            self._gefechte_geschickt(antwort)
        elif marke == "kosmetik_lesen":
            self._kosmetik_gelesen(antwort)

    def _angemeldet(self, marke: str, antwort) -> None:
        if not antwort:
            self.fehler = antwort.fehler or "ANMELDUNG FEHLGESCHLAGEN"
            return
        self.kennung = str(antwort.daten.get("kennung") or "")
        self.name = ablage.name_saeubern(antwort.daten.get("name") or "")
        self.sitzung = str(antwort.daten.get("sitzung") or "")
        self.erneuern_marke = str(antwort.daten.get("erneuern") or "")
        self.hinweis = ("KONTO ANGELEGT" if marke == "anlegen"
                        else "ANGEMELDET ALS %s" % self.name)
        self.sitzung_speichern()
        # Was auf diesem Rechner schon gespielt wurde, gehoert ab jetzt
        # zum Konto. Die Partiekennungen sind eindeutig, also kann dabei
        # nichts doppelt gezaehlt werden.
        for e in self.journal.eintraege:
            e.setdefault("konto", self.kennung)
        self.journal.speichern()
        self.profil_holen()
        self.kosmetik_holen()

    def _profil_gelesen(self, antwort) -> None:
        if not antwort:
            self.fehler = antwort.fehler
            self._ruhe = K.KONTO["ruhe_nach_fehler"]
            return
        ferne_fassung = int(antwort.daten.get("fassung", 0))
        loadouts = antwort.daten.get("loadouts") or []
        if ferne_fassung > 0 and loadouts:
            # Der Server hat den jüngeren Stand: er gilt.
            self.profil_fassung = ferne_fassung
            self.werte = dict(antwort.daten.get("werte") or {})
            self.loadouts = loadouts_saeubern(loadouts)
            self.hinweis = "PROFIL GELADEN"
            self.sitzung_speichern()
            return
        # Der Server hat noch nichts. Dann geht hoch, was hier steht -
        # so nimmt ein frisch angelegtes Konto die Loadouts mit, die
        # vorher ohne Anmeldung gebaut wurden.
        self.profil_fassung = ferne_fassung
        self.profil_sichern()

    def _profil_geschrieben(self, antwort) -> None:
        if antwort:
            self.profil_fassung = int(antwort.daten.get("fassung",
                                                        self.profil_fassung + 1))
            self.sitzung_speichern()
            return
        # Abgelehnt, weil jemand anders schneller war. Der fremde Stand
        # kommt mit der Antwort; er gilt, und was hier geaendert wurde,
        # wird danach nochmal geschrieben. Blind ueberschreiben waere der
        # Weg zu verschwundenen Loadouts.
        if isinstance(antwort.daten, dict) and antwort.daten.get("fassung") is not None:
            self.profil_fassung = int(antwort.daten.get("fassung", 0))
            fern = loadouts_saeubern(antwort.daten.get("loadouts"))
            if fern != self.loadouts:
                self.hinweis = "PROFIL WAR NEUER, WIRD ZUSAMMENGEFÜHRT"
            # Die eigenen Werte gewinnen. Mit ** statt `|`: das Spiel laeuft
            # auch unter Python 3.8, und dort gibt es `|` fuer dict nicht
            # (gemeldet nach 0.31.1, Absturz beim Gastgeber).
            self.werte = {**dict(antwort.daten.get("werte") or {}), **dict(self.werte)}
            self.sitzung_speichern()
        else:
            self.fehler = antwort.fehler
            self._ruhe = K.KONTO["ruhe_nach_fehler"]

    def _gefechte_geschickt(self, antwort) -> None:
        if not antwort:
            self.fehler = antwort.fehler
            self._ruhe = K.KONTO["ruhe_nach_fehler"]
            return
        anzahl = self.journal.abhaken(antwort.daten.get("genommen") or [])
        if anzahl:
            self.hinweis = "%d RUNDEN ABGEGLICHEN" % anzahl

    def hochladen_vor_ende(self) -> bool:
        """Beim Beenden: was offen ist, jetzt noch hoch. True, wenn es ging.

        Ohne Faden und ohne auf den Takt zu warten - das Fenster geht
        gleich zu, und eine gerade abgebrochene Runde soll nicht bis zum
        naechsten Start im Journal liegen. Klappt es nicht, ist nichts
        verloren: das Journal steht auf der Platte, und beim naechsten
        Start geht es hoch wie immer.

        Kurz gehalten (ablage.WARTEZEIT gilt je Anfrage, und es ist genau
        eine): ein Spiel, das sich beim Schliessen eine halbe Minute
        Zeit laesst, schliesst man das naechste Mal ueber den Taskmanager.
        """
        if not self.angemeldet or not self.mit_server:
            return False
        offen = self.journal.offen()
        if not offen:
            return True
        paket = []
        for e in offen:
            zeile = {k: v for k, v in e.items() if k != "abgeglichen"}
            zeile["konto"] = self.kennung
            paket.append(zeile)
        try:
            antwort = self.ablage.gefechte_senden(self.sitzung, paket)
        except Exception:                          # noqa: BLE001
            return False
        if not antwort:
            return False
        self.journal.abhaken(antwort.daten.get("genommen") or [])
        return True

    def schliessen(self) -> None:
        self.sitzung_speichern()
        if self._werk is not None:
            self._werk.schliessen()
