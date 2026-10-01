"""
DUSTFRONT - Die Regeln einer Runde
==================================

Alles, was der Gastgeber fuer eine Runde einstellt, an einer Stelle.

Vorher stand jede Regel fuenfmal da: als Parameter des Gefechts, im
Wunschzettel des Pausenmenues, im Menue selbst, in der Willkommens-
nachricht und in deren Auswertung beim Gast. Eine neue Regel hiess fuenf
Stellen anfassen, und wer eine vergass, hatte eine Regel, die beim Gast
nicht ankam oder sich nicht verstellen liess. Hier steht sie einmal:
Name, erlaubte Werte, wann sie gilt. Das Menue, die Nachricht, die Lobby
und der Rundenplan lesen alle diese Tabelle.

Eine Regelsammlung ist ein schlichtes Woerterbuch. Das ist Absicht: es
geht unveraendert als JSON durchs Netz, laesst sich kopieren und in einen
Rundenplan legen, und `saeubern` macht aus allem, was von aussen kommt,
wieder eine gueltige Sammlung - eine kaputte Nachricht kostet hoechstens
die eine Regel, die kaputt ist.

    regeln.vorgabe()                  eine Sammlung mit allen Vorgaben
    regeln.saeubern(roh, umfeld)      aus beliebigem Input eine gueltige
    regeln.sichtbar(d)                welche Felder bei dieser Spielart gelten
    regeln.verstellen(d, k, +1)       einen Schritt weiter
    regeln.anzeige(d, k)              der Wert als Text fuer Menue und Lobby

`umfeld` sagt, was es nur beim Gastgeber gibt: seine Loadouts (fuer die
Regel "eines fuer alle") und die Karten auf seiner Platte.
"""

from __future__ import annotations

from . import config as K


def _modi(d, u):
    return [m for m in K.MODI if not K.MODI[m].get("lobby")]


def _karten(d, u):
    """Die eingebaute Karte (leerer Name) und alle aus dem Ordner.

    Ohne Umfeld von der Platte gelesen: auch ein Gast muss eine Karte
    annehmen koennen, die der Gastgeber waehlt - er hat sie ja auch.
    """
    if u and "karten" in u:
        liste = list(u["karten"])
    else:
        from . import world
        liste = list(world.karten_liste())
    # Die Lobby ist kein Schauplatz fuer eine Runde - sie ist der Ort
    # dazwischen. Gueltig ist sie trotzdem (siehe `erlaubt`).
    return [""] + [k for k in liste if k != K.LOBBY["karte"]]


def _abschuesse_werte():
    return [1, 2, 3, 5, 8, 10, 15, 20, 25, 30, 40, 50, 60, 75, 100, 150, 200]


def _ende_werte(d, u):
    if d.get("ende_art") == "abschuesse":
        return _abschuesse_werte()
    return [60 * m for m in range(1, 31)]


def _loadout_nummern(d, u):
    """Ohne Umfeld jede vernuenftige Nummer: der Gast kennt die Loadouts
    des Gastgebers nicht und soll die Nummer trotzdem stehen lassen."""
    if u is None or "loadouts" not in u:
        return list(range(16))
    return list(range(len(u["loadouts"]) or 1))


def _loadout_name(v, d, u):
    liste = (u or {}).get("loadouts", ())
    if 0 <= v < len(liste):
        return str(liste[v].get("name", "LOADOUT %d" % (v + 1))).upper()
    return "LOADOUT %d" % (v + 1)


def _an_aus(v, d, u):
    return "AN" if v else "AUS"


def _regeln(d):
    return K.MODI.get(d.get("modus"), K.MODI[K.MODUS_VORGABE])


def _endet_selbst(d):
    """Ob die Spielart eine eigene Endbedingung hat.

    Versus endet nach Runden, Huegel am vollen Kreis, alles mit Aufhelfen
    (pve), wenn niemand mehr steht. Nur die anderen fragen, wann Schluss ist.
    """
    r = _regeln(d)
    return r["zone"] or r["revive"] or r["runden"]


def _mit_notbremse(d):
    """Versus und Huegel enden selbst, haben aber eine Hoechstdauer.

    Ohne sie liefe ein Huegel, den keiner nimmt, ewig. Pve hat keine:
    dort ist Schluss, wenn keiner mehr steht, und eine Uhr, die eine
    gute Runde abpfeift, waere eine Strafe fuers Gutsein.
    """
    r = _regeln(d)
    return r["zone"] or r["runden"]


class Feld:
    """Eine einstellbare Regel.

    werte(d, umfeld) gibt die erlaubten Werte in ihrer Reihenfolge.
    text(v, d, umfeld) macht daraus, was im Menue steht.
    gilt(d) sagt, ob die Regel bei dieser Sammlung ueberhaupt zaehlt -
    eine Haltezeit hat in pvp nichts zu suchen.
    rund: am Ende wieder vorn anfangen (Aufzaehlungen) oder stehen
    bleiben (Zahlen - von 15 Runden auf 1 zu springen, ueberrascht).
    zahl: auch Werte zwischen den Stufen annehmen, solange sie im
    Rahmen liegen. Die Kommandozeile darf "--wert 7" sagen, obwohl das
    Menue in anderen Schritten zaehlt.
    einfach: steht auch in der einfachen Ansicht der Rundentafel
    (seit 0.32, siehe EINFACH).
    """

    def __init__(self, schluessel, name, gruppe, vorgabe, werte, text=None,
                 gilt=None, rund=False, zahl=False, schalter=False,
                 einzug=False, hilfe="", erlaubt=None):
        self.schluessel = schluessel
        self.einfach = False        # gesetzt nach FELDER, aus EINFACH
        self._name = name
        self.gruppe = gruppe
        self._vorgabe = vorgabe
        self._werte = werte
        self._text = text
        self._gilt = gilt
        self.rund = rund
        self.zahl = zahl
        self.schalter = schalter
        self._einzug = einzug
        self.hilfe = hilfe
        # Gueltig, aber nicht waehlbar: die Lobby als Spielart und als
        # Karte. Sie muss durchs Netz und durch `saeubern`, im Menue
        # durchblaettern soll man sie aber nicht.
        self._erlaubt = erlaubt

    def name(self, d) -> str:
        """Die Beschriftung. Bei manchen Regeln haengt sie an der Spielart:
        der Endwert heisst in versus Hoechstdauer, sonst "und zwar bei"."""
        return self._name(d) if callable(self._name) else self._name

    def einzug(self, d) -> bool:
        """Eingerueckt, wenn die Zeile zur vorigen gehoert."""
        return bool(self._einzug(d) if callable(self._einzug) else self._einzug)

    def vorgabe(self, d=None):
        return self._vorgabe(d or {}) if callable(self._vorgabe) else self._vorgabe

    def werte(self, d, umfeld=None) -> list:
        if self.schalter:
            return [True, False]
        w = self._werte(d, umfeld) if callable(self._werte) else self._werte
        return list(w)

    def text(self, v, d, umfeld=None) -> str:
        if self._text is not None:
            return self._text(v, d, umfeld)
        if self.schalter:
            return _an_aus(v, d, umfeld)
        return str(v)

    def gilt(self, d) -> bool:
        return True if self._gilt is None else bool(self._gilt(d))


def _ende_vorgabe(d):
    """Zeit wie immer; Abschuesse je nachdem, ob ein Konto oder sechs.

    Als Hoechstdauer (versus, huegel) zehn Minuten - so stand es im
    Startskript, und fuenf reichen fuer fuenf Versusrunden nicht.
    """
    if _mit_notbremse(d):
        return 600
    if d.get("ende_art", "zeit") == "zeit":
        return int(K.GEFECHT["rundenzeit"])
    if _regeln(d)["teams"]:
        return int(K.GEFECHT["team_abschuesse"])
    return int(K.GEFECHT["abschuesse_ziel"])


FELDER = (
    # ── Die Runde
    Feld("modus", "SPIELART", "RUNDE", K.MODUS_VORGABE, _modi,
         text=lambda v, d, u: K.MODI[v]["name"], rund=True,
         erlaubt=lambda v: v in K.MODI,
         hilfe="WIE GESPIELT WIRD."),
    Feld("karte", "KARTE", "RUNDE", "", _karten,
         text=lambda v, d, u: (v or "TESTKARTE").upper(), rund=True,
         erlaubt=lambda v: v == K.LOBBY["karte"],
         hilfe="AUF WELCHER KARTE."),
    Feld("runden", "GESPIELTE RUNDEN", "RUNDE", K.VERSUS["runden"],
         lambda d, u: range(K.VERSUS["runden_grenzen"][0],
                            K.VERSUS["runden_grenzen"][1] + 1),
         gilt=lambda d: _regeln(d)["runden"], zahl=True,
         hilfe="BEI GLEICHSTAND KOMMT EINE RUNDE ALS MATCHPOINT DAZU."),
    Feld("ende_art", "RUNDE ENDET NACH", "RUNDE", "zeit",
         lambda d, u: K.ENDE_ARTEN,
         text=lambda v, d, u: "ZEIT" if v == "zeit" else "ABSCHÜSSEN",
         gilt=lambda d: not _endet_selbst(d), rund=True),
    Feld("ende_wert",
         lambda d: "HÖCHSTDAUER" if _mit_notbremse(d) else "UND ZWAR BEI",
         "RUNDE", _ende_vorgabe, _ende_werte,
         text=lambda v, d, u: ("%d MIN" % round(v / 60)
                               if d.get("ende_art") == "zeit" else "%d" % v),
         gilt=lambda d: not _endet_selbst(d) or _mit_notbremse(d), zahl=True,
         einzug=lambda d: not _mit_notbremse(d)),
    Feld("huegel_zeit", "HALTEZEIT", "RUNDE", K.ZONE["haltezeit"],
         lambda d, u: K.ZONE["haltezeiten"],
         text=lambda v, d, u: "%d S" % v,
         gilt=lambda d: _regeln(d)["zone"], zahl=True,
         hilfe="SO LANGE MUSS EINER DEN KREIS ALLEIN HALTEN."),
    Feld("huegel_verfall", "FORTSCHRITT VERFÄLLT", "RUNDE",
         K.ZONE["verfall_an"], None, schalter=True, einzug=True,
         gilt=lambda d: _regeln(d)["zone"],
         hilfe="SINKT DER STAND, WENN KEINER HÄLT?"),
    # ── Die Gegner
    Feld("schwierigkeit", "SCHWIERIGKEIT", "GEGNER", K.SCHWIERIGKEIT_VORGABE,
         lambda d, u: K.SCHWIERIGKEIT,
         text=lambda v, d, u: K.SCHWIERIGKEIT[v]["name"],
         gilt=lambda d: _regeln(d)["gegner"],
         hilfe="WIE VIELE, WIE ZÄH UND WIE HART DIE WELLEN SIND."),
    Feld("bosse", "BOSSE", "GEGNER", True, None, schalter=True,
         gilt=lambda d: _regeln(d)["gegner"],
         hilfe="JEDE FÜNFTE WELLE EIN BOSS - ODER KEINER."),
    # ── Die Ausruestung
    Feld("loadouts", "AUSRÜSTUNG", "AUSRÜSTUNG", K.GEFECHT["loadouts"],
         lambda d, u: K.GEFECHT["loadout_arten"],
         text=lambda v, d, u: {"alles": "JEDER HAT ALLES",
                               "eigenes": "EIGENES LOADOUT",
                               "gleich": "EINES FÜR ALLE"}[v], rund=True),
    Feld("loadout_nr", "LOADOUT", "AUSRÜSTUNG", 0, _loadout_nummern,
         text=_loadout_name, gilt=lambda d: d.get("loadouts") == "gleich",
         rund=True, einzug=True,
         hilfe="EINES DEINER LOADOUTS - DAS TRAGEN ALLE."),
    Feld("knapp", "MUNITION KNAPP", "AUSRÜSTUNG", False, None, schalter=True),
    Feld("medkits", "MEDKITS BEIM EINSTIEG", "AUSRÜSTUNG",
         K.GEFECHT["start_medkits"],
         lambda d, u: range(0, K.GEFECHT["start_medkits_hoechstens"] + 1),
         zahl=True),
    Feld("medkit_spawn", "MEDKITS AUF DER KARTE", "AUSRÜSTUNG",
         K.GEFECHT["medkits_spawnen"], None, schalter=True),
    Feld("rpg", "RAKETENWERFER", "AUSRÜSTUNG", K.GEFECHT["rpg"], None,
         schalter=True),
    Feld("rpg_lenkung", "MIT ZIELERFASSUNG", "AUSRÜSTUNG",
         K.GEFECHT["rpg_lenkung"], None, schalter=True, einzug=True,
         gilt=lambda d: bool(d.get("rpg"))),
    Feld("mg_schub", "MG-RÜCKSTOSS SCHIEBT", "AUSRÜSTUNG", False, None,
         schalter=True,
         hilfe="AUS: DAS MG MACHT NUR LANGSAM. AN: JEDER SCHUSS SCHIEBT ZURÜCK."),
    # ── Der Einstieg
    Feld("schutz", "EINSTIEGSSCHUTZ", "EINSTIEG", K.GEFECHT["schutz_an"],
         None, schalter=True),
    # ── Spielerkosmetik (spielerkosmetik.py). Steht in keinem Menue: der
    # Gastgeber entscheidet es beim Start - MIT oder OHNE KOSMETIK -, und
    # mit Kosmetik geht es erst, wenn alle alles geladen haben. Hier steht
    # es nur, damit die Entscheidung mit den Regeln zu den Gaesten kommt.
    Feld("kosmetik", "SPIELERKOSMETIK", "AUSRÜSTUNG", False, None,
         schalter=True, gilt=lambda d: False),
)

NACH_NAME = {f.schluessel: f for f in FELDER}

# Was die einfache Ansicht der Rundentafel zeigt (seit 0.32). Gemeldet:
# "Menues fuer neue Spieler: Rundeneinstellungen in einfach und
# erweitert." Wer zum ersten Mal eine Runde aufmacht, soll Spielart,
# Karte, Dauer und Ausruestung sehen und nicht sechzehn Zeilen. Alles
# andere steht unter ERWEITERT und behaelt dort seinen Wert, auch wenn
# es gerade nicht zu sehen ist.
EINFACH = ("modus", "karte", "runden", "ende_art", "ende_wert",
           "huegel_zeit", "schwierigkeit", "loadouts", "loadout_nr")
for _f in FELDER:
    _f.einfach = _f.schluessel in EINFACH
GRUPPEN = ("RUNDE", "GEGNER", "AUSRÜSTUNG", "EINSTIEG")


def vorgabe(**ueber) -> dict:
    """Eine Sammlung mit allen Vorgaben; `ueber` setzt einzelne davon."""
    d = {}
    for f in FELDER:
        d[f.schluessel] = f.vorgabe(dict(d, **ueber))
    d.update(ueber)
    return saeubern(d)


def _passend(f: Feld, v, d, umfeld):
    """v, wenn es erlaubt ist - sonst None."""
    if f._erlaubt is not None:
        try:
            if f._erlaubt(v):
                return v
        except TypeError:          # eine Liste als Spielart, von aussen
            return None
    werte = f.werte(d, umfeld)
    if f.schalter:
        return v if isinstance(v, bool) else None
    if f.zahl and werte:
        if isinstance(v, bool) or not isinstance(v, (int, float)):
            return None
        v = max(min(werte), min(max(werte), v))
        return int(v) if float(v).is_integer() else float(v)
    return v if v in werte else None


def saeubern(roh, umfeld=None) -> dict:
    """Aus beliebigem Input eine gueltige Sammlung.

    Der Reihe nach, weil manche Werte von frueheren abhaengen: welche
    Endwerte erlaubt sind, haengt an der Endart, und die Vorgabe dafuer
    an der Spielart. Was fehlt oder nicht passt, bekommt die Vorgabe -
    auch dann, wenn die Regel bei dieser Spielart gar nicht gilt: wer
    danach die Spielart wechselt, soll einen vernuenftigen Wert
    vorfinden und keinen leeren.
    """
    roh = roh if isinstance(roh, dict) else {}
    d = {}
    for f in FELDER:
        v = _passend(f, roh.get(f.schluessel), d, umfeld)
        if f.schluessel == "ende_art" and _mit_notbremse(d):
            v = "zeit"          # eine Hoechstdauer ist eine Zeit
        if v is None:
            v = f.vorgabe(d)
            v = _passend(f, v, d, umfeld)
            if v is None:
                werte = f.werte(d, umfeld)
                v = werte[0] if werte else f.vorgabe(d)
        d[f.schluessel] = v
    return d


def sichtbar(d, erweitert: bool = True) -> list:
    """Die Felder, die bei dieser Sammlung zaehlen, in Menuereihenfolge.

    erweitert=False: nur die aus EINFACH.
    """
    return [f for f in FELDER if f.gilt(d) and (erweitert or f.einfach)]


def verborgen_geaendert(d, umfeld=None) -> list:
    """Erweiterte Regeln, die gelten und nicht auf der Standardrunde stehen.

    Fuer die einfache Ansicht: wer dort nur Spielart und Karte sieht,
    soll trotzdem erfahren, dass unter ERWEITERT etwas verstellt ist -
    sonst wundert er sich, warum die Munition knapp ist.
    """
    standard = standardrunde(umfeld)
    raus = []
    for f in FELDER:
        if f.einfach or not f.gilt(d):
            continue
        # Verglichen mit der Vorgabe *dieser* Spielart, nicht mit der
        # Standardrunde: deren Spielart hat andere Vorgaben.
        if d.get(f.schluessel) != f.vorgabe(d) and \
                d.get(f.schluessel) != standard.get(f.schluessel):
            raus.append(f)
    return raus


def standardrunde(umfeld=None) -> dict:
    """Die Runde, die eine frische Lobby plant (K.STANDARDRUNDE).

    Fehlt die Karte auf dieser Platte, die eingebaute: eine Standardrunde,
    die nicht startet, waere das Gegenteil von dem, wofuer sie da ist.
    """
    d = dict(K.STANDARDRUNDE)
    if d.get("karte") and d["karte"] not in _karten(d, umfeld):
        d["karte"] = ""
    return saeubern(d, umfeld)


def verstellen(d: dict, schluessel: str, schritt: int = 1,
               umfeld=None) -> None:
    """Eine Regel einen Schritt weiter oder zurueck, an Ort und Stelle.

    Liegt der Wert zwischen zwei Stufen (von der Kommandozeile), geht es
    zur naechsten Stufe in der gewuenschten Richtung, nicht zwei weiter.
    Wechselt die Endart, bekommt der Endwert die Vorgabe der neuen: fuenf
    Minuten sind nicht fuenf Abschuesse.
    """
    f = NACH_NAME.get(schluessel)
    if f is None:
        return
    werte = f.werte(d, umfeld)
    if not werte:
        return
    jetzt = d.get(schluessel)
    if jetzt in werte:
        i = werte.index(jetzt) + schritt
    elif f.zahl and isinstance(jetzt, (int, float)):
        if schritt > 0:
            groesser = [i for i, w in enumerate(werte) if w > jetzt]
            i = groesser[0] if groesser else len(werte) - 1
        else:
            kleiner = [i for i, w in enumerate(werte) if w < jetzt]
            i = kleiner[-1] if kleiner else 0
    else:
        i = 0
    if f.rund or f.schalter:
        i %= len(werte)
    else:
        i = max(0, min(len(werte) - 1, i))
    d[schluessel] = werte[i]
    if schluessel in ("ende_art", "modus"):
        d["ende_wert"] = _ende_vorgabe(d)
    neu = saeubern(d, umfeld)
    d.clear()
    d.update(neu)


def anzeige(d: dict, schluessel: str, umfeld=None) -> str:
    f = NACH_NAME[schluessel]
    return f.text(d.get(schluessel, f.vorgabe(d)), d, umfeld)


def kurz(d: dict, umfeld=None) -> str:
    """Eine Zeile fuer den Rundenplan: Spielart, Karte, das Wichtigste."""
    teile = [anzeige(d, "modus", umfeld), anzeige(d, "karte", umfeld)]
    r = _regeln(d)
    if r["runden"]:
        teile.append("%d RUNDEN" % d["runden"])
    elif r["zone"]:
        teile.append("%d S" % d["huegel_zeit"])
    elif not _endet_selbst(d):
        teile.append(anzeige(d, "ende_wert", umfeld)
                     + ("" if d["ende_art"] == "zeit" else " ABSCH."))
    if r["gegner"]:
        teile.append(anzeige(d, "schwierigkeit", umfeld))
    return "  ".join(teile)
