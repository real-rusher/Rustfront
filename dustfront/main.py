"""
DUSTFRONT - Einstieg
====================

    python -m dustfront                Spiel starten
    python -m dustfront --host ...     LAN-Runde aufmachen, siehe README
    python -m dustfront --join WOHIN   einer LAN-Runde beitreten
    python -m dustfront --vorlagen     jedes Bild als Vorlage herausschreiben
    python -m dustfront --assets       zeigen, was aus Dateien kommt
    python -m dustfront --konto ...    Konten anlegen und ansehen
    python -m dustfront --karten       zeigen, welche Karten es gibt
    python -m dustfront --kosmetik     Vorschaubilder fuer Kisten und Skins
    python -m dustfront --kontoseite   KONTO.html neu erzeugen

Bilder werden, falls vorhanden, aus dem Ordner `assets` neben dem Paket
geladen, Klaenge aus `assets/sfx`. Fehlt etwas, zeichnet und rechnet sich das
Spiel seine Platzhalter selbst.
"""

from __future__ import annotations

from pathlib import Path

from . import config as K
from .core import App
from .pfade import spielordner
from .play import Spiel


def asset_ordner() -> Path | None:
    p = spielordner() / K.ASSETS["ordner"]
    return p if p.is_dir() else None


def starten(headless: bool = False, beenden: bool = True,
            auftrag: dict | None = None) -> int:
    """Startet das Spiel.

    beenden=False laesst pygame stehen, wenn das Spiel endet - so ruft das
    Hauptmenue uns auf und macht danach weiter.

    auftrag ist das, was das Menue ausgewaehlt hat (Region, Schwierigkeit,
    Rufzeichen). Das Spiel legt es ab, ohne es heute schon auszuwerten:
    daran haengen spaeter die Sektoren, siehe docs/KARTE.md, M5 und M7.
    """
    app = App("DUSTFRONT", asset_ordner(), headless=headless)
    app.auftrag = dict(auftrag) if auftrag else {}
    app.schieben(Spiel(app))
    app.laufen(beenden=beenden)
    return 0


def aus_menue(auftrag: dict | None = None) -> int:
    """Einstieg fuer das Hauptmenue: spielen und danach zurueckkehren."""
    return starten(headless=False, beenden=False, auftrag=auftrag)


def gefecht(gastgeber: bool, wohin: str = "", name: str = "",
            port: int = 0, headless: bool = False,
            modus: str = K.MODUS_VORGABE, ende_art: str = "zeit",
            ende_wert: float = 0.0, knapp: bool = False,
            schutz: bool | None = None, medkits: int | None = None,
            medkit_spawn: bool | None = None, runden: int | None = None,
            team: int | None = None, online: bool = False,
            passwort: str = "", loadouts: str | None = None,
            karte: str = "") -> int:
    """LAN-Test: als Gastgeber aufmachen oder als Gast verbinden.

    Die Spielart bestimmt allein der Gastgeber. Ein Gast bekommt sie mit
    dem Willkommen zugeschickt - sonst spielen zwei Leute mit verschiedenen
    Regeln auf derselben Karte.
    """
    from . import netz
    from .mehrspieler import Gefecht

    app = App("DUSTFRONT - GEFECHT", asset_ordner(), headless=headless)
    wirt = gast = None
    try:
        if gastgeber:
            wirt = netz.Gastgeber(port or None, online=online)
            regeln = K.MODI.get(modus, K.MODI[K.MODUS_VORGABE])
            print("Gastgeber laeuft: %s - %s" % (regeln["name"], regeln["hinweis"]))
            if regeln["teams"]:
                print("Mannschaften: %s gegen %s, neue Leute gehen in die "
                      "kleinere." % K.TEAMS["namen"])
            if regeln["zone"]:
                print("Der Kreis liegt in der Kartenmitte, Ebene %d. Wer dort "
                      "die Mehrheit hat, laedt bis %d."
                      % (K.ZONE["ebene"], int(K.ZONE["bis"])))
            elif regeln["runden"]:
                print("Ein Leben je Runde, %d Rundensiege entscheiden. "
                      "Aufhelfen geht nur in der eigenen Mannschaft."
                      % (K.VERSUS["runden_bis"] if runden is None else runden))
            elif not regeln["revive"]:
                print("Endet nach %s" % ("Zeit" if ende_art == "zeit"
                                         else "Abschuessen"))
            if knapp:
                print("Munition ist knapp, es gibt Nachschubkisten.")
            print("Einstiegsschutz: %s"
                  % ("%.0f Sekunden" % K.GEFECHT["schutz"]
                     if (K.GEFECHT["schutz_an"] if schutz is None else schutz)
                     else "aus"))
            wieviele = (K.GEFECHT["start_medkits"] if medkits is None
                        else medkits)
            print("Medkits beim Einstieg: %d" % wieviele)
            print("Medkits auf der Karte: %s"
                  % ("alle %.0f Sekunden" % K.GEFECHT["medkit_takt"]
                     if (K.GEFECHT["medkits_spawnen"] if medkit_spawn is None
                         else medkit_spawn) else "keine"))
            if karte:
                from . import world as W
                print("Karte: %s" % karte)
                if W.karte_lesen(karte)[0] is None:
                    print("  gibt es nicht - moeglich: %s"
                          % (", ".join(W.karten_liste()) or "keine"))
            print("Ausruestung: %s"
                  % ("jeder traegt sein eigenes Loadout"
                     if (loadouts or K.GEFECHT["loadouts"]) == "eigenes"
                     else "jeder hat alles"))
            if passwort:
                print("Kennwort: %s" % netz.passwort_saeubern(passwort))
            print("Im eigenen Netz verbinden sich Mitspieler mit:")
            print("   %s" % wirt.adresse)
            if online and wirt.freigabe is not None:
                print()
                for zeile in wirt.freigabe.bericht():
                    print(zeile)
                print()
                print("Ueber das Internet ist die Verzoegerung so gross wie")
                print("die Leitung: der Gastgeber rechnet alles, ein Gast")
                print("sieht seine Figur erst nach einem Hin- und Rueckweg.")
                if not passwort:
                    print("Ohne Kennwort (--passwort) kann jeder mitspielen,")
                    print("der die Adresse kennt.")
        else:
            gast = netz.Gast(wohin)
            if not gast.offen:
                print("Keine Verbindung zu %s: %s" % (wohin, gast.fehler))
                return 1
            print("Verbunden mit %s" % wohin)
    except OSError as grund:
        print("Konnte nicht aufmachen: %s" % grund)
        return 1

    app.schieben(Gefecht(app, name or "GAST", gastgeber=wirt, gast=gast,
                         modus=modus, ende_art=ende_art,
                         ende_wert=ende_wert, knapp=knapp, schutz=schutz,
                         medkits=medkits, medkit_spawn=medkit_spawn,
                         runden=runden, team=team, passwort=passwort,
                         loadouts=loadouts, karte=karte))
    app.laufen()
    return 0


def konten(argumente: list[str], wert) -> int:
    """Konten im Terminal anlegen und ansehen.

        python -m dustfront --konto liste
        python -m dustfront --konto neu   --name MEISTER [--wort GEHEIM123]
        python -m dustfront --konto pruef --name MEISTER --wort GEHEIM123

    Damit kann der Gastgeber einer LAN-Runde seinen Gaesten Konten
    anlegen, ohne dass irgendwo ein Server laufen muss. Das war
    ausdruecklich gewuenscht: im Keller mit vier Leuten und ohne
    Internet soll jeder trotzdem seine Zahlen und seine Loadouts haben.

    Das Kennwort laesst sich weglassen; dann wird es abgefragt und
    dabei nicht angezeigt. Auf der Kommandozeile stuende es sonst
    hinterher in der Verlaufsdatei der Shell.
    """
    import getpass

    from . import ablage as A

    was = wert("--konto", "liste").strip().lower()
    lokal = A.LokaleAblage()
    if was in ("liste", "zeigen", ""):
        namen = lokal.namen()
        print("Konten auf diesem Rechner: %s" % (pfade_text() or "nirgends"))
        if not namen:
            print("  noch keines - anlegen mit --konto neu --name <name>")
        for n in namen:
            print("  %s" % n)
        netz_ablage = A.NetzAblage()
        print("Server: %s" % (netz_ablage.url if netz_ablage.eingerichtet
                              else "keiner eingetragen, siehe docs/KONTO.md"))
        if netz_ablage.eingerichtet:
            print("  ob er wirklich geht, sagt --konto server")
        return 0
    if was in ("server", "pruefserver", "selbsttest"):
        return konto_server_pruefen(A, wert)

    name = A.name_saeubern(wert("--name", ""))
    fehler = A.name_pruefen(name)
    if fehler:
        print(fehler.capitalize())
        return 1
    wort = wert("--wort", "")
    if not wort:
        try:
            wort = getpass.getpass("Kennwort fuer %s: " % name)
        except (EOFError, KeyboardInterrupt):
            print()
            return 1

    if was == "neu":
        antwort = lokal.anlegen(name, wort)
        if not antwort:
            print(antwort.fehler.capitalize())
            return 1
        print("Konto %s angelegt." % name)
        print("Es gilt auf diesem Rechner. Mit einem eingetragenen Server")
        print("gilt es ueberall - siehe docs/KONTO.md.")
        return 0
    if was in ("pruef", "pruefen", "test"):
        antwort = lokal.anmelden(name, wort)
        print("In Ordnung." if antwort else antwort.fehler.capitalize())
        return 0 if antwort else 1
    print("Unbekannt: --konto %s. Moeglich: liste, neu, pruef, server" % was)
    return 1


def konto_server_pruefen(A, wert) -> int:
    """Der Selbsttest gegen den eingetragenen Supabase-Zugang.

    Er beantwortet die einzige Frage, die zaehlt: **geht es wirklich?**
    Ein eingetragener Server ist noch kein funktionierender Server - die
    Tabellen koennen fehlen, der Zeilenschutz kann falschherum stehen,
    die Bestaetigung per Post kann noch anstehen, und die Adresse
    `<name>@spieler.dustfront` kann abgelehnt werden. Jedes davon faellt
    erst beim ersten echten Spieler auf, wenn man es nicht vorher prueft.

    Darum wird hier nicht "angepingt", sondern der ganze Weg gegangen,
    den ein Spieler auch geht: Konto anlegen, anmelden, Profil lesen,
    Profil schreiben, eine Runde buchen, **dieselbe Runde noch einmal
    buchen** und nachsehen, dass sie nur einmal dasteht. Der vorletzte
    Schritt ist der wichtigste - er prueft die Regel, an der die ganze
    Statistik haengt (`docs/KONTO.md`, Abschnitt 3).

    Angelegt wird dabei ein Wegwerfkonto mit gewuerfeltem Namen. Es
    bleibt stehen; loeschen kann nur, wer die Datenbank aufmacht, und
    dafuer ist ein Selbsttest der falsche Ort.
    """
    import time

    netz = A.NetzAblage()
    if not netz.eingerichtet:
        print("Kein Server eingetragen.")
        print("Was einzutragen ist und wo es steht: docs/KONTO.md, 5.4.")
        return 1
    print("Server: %s" % netz.url)
    print("Schluessel: %s...%s (%d Zeichen)"
          % (netz.schluessel[:12], netz.schluessel[-4:], len(netz.schluessel)))
    print()

    name = A.name_saeubern(wert("--name", "")) or ("PRUEF" + A.kennung()[:7])
    wort = wert("--wort", "") or ("P" + A.kennung()[:16])
    schritte, fehler = [], []

    def schritt(titel, antwort, zusatz=""):
        ok = bool(antwort)
        schritte.append(ok)
        print(("  ok    " if ok else "FEHLER  ") + titel
              + (("   " + zusatz) if zusatz else "")
              + ("" if ok else "   " + antwort.fehler))
        if not ok:
            fehler.append((titel, antwort.fehler))
        return ok

    angelegt = netz.anlegen(name, wort)
    if not schritt("Konto anlegen", angelegt, name):
        # Ohne Konto hat der Rest keinen Sinn. Der haeufigste Grund
        # steht dann gleich dabei, statt dass jemand danach sucht.
        grund = angelegt.fehler
        print()
        # Die Reihenfolge ist Absicht. Mehrere dieser Meldungen enthalten
        # das Wort EMAIL, und die Ursachen dahinter sind voellig
        # verschieden - wer zuerst auf EMAIL prueft, schickt jeden in die
        # falsche Ecke. Vom Engsten zum Weitesten also.
        if "DISABLED" in grund or "NOT ALLOWED" in grund or "SIGNUP" in grund:
            print("Der Anmeldedienst nimmt gar keine neuen Konten an.")
            print("Das ist nicht die Bestaetigung per Post, sondern ein")
            print("Schalter davor - einer von zweien:")
            print("  Authentication -> Sign In / Providers -> Email")
            print("  muss ueberhaupt eingeschaltet sein (der Schalter am")
            print("  Anbieter selbst, nicht 'Confirm email' darin), und")
            print("  'Allow new users to sign up' muss an sein.")
            print("Siehe docs/KONTO.md, 5.3.")
        elif "CONFIRM" in grund or "BESTAET" in grund:
            print("Die Bestaetigung per Post steht noch an.")
            print("Authentication -> Sign In / Providers -> Email:")
            print("'Confirm email' ausschalten. Siehe docs/KONTO.md, 5.3.")
        elif "API KEY" in grund or "JWT" in grund or "401" in grund:
            print("Der Schluessel stimmt nicht.")
            print("Settings -> API Keys, der 'publishable key'.")
        elif "DATABASE ERROR" in grund:
            print("Der Anmeldedienst kommt bis zur Datenbank und scheitert")
            print("dort. Das ist fast immer der Ausloeser, der beim Anlegen")
            print("eines Kontos das Profil dazulegt: ohne 'set search_path'")
            print("und den vollen Namen 'public.profil' findet er die")
            print("Tabelle nicht, und mehr als diese Meldung kommt nicht")
            print("zurueck. Das Stueck ab 'Beim Anlegen eines Kontos' aus")
            print("docs/KONTO.md 5.2 noch einmal ausfuehren.")
        elif "INVALID" in grund and "EMAIL" in grund:
            print("Der Anmeldedienst lehnt die Adresse ab.")
            print("Das Spiel meldet sich als <name>@spieler.dustfront an.")
            print("Abhilfe: in SERVER eine Domaene eintragen, die er")
            print("annimmt - siehe docs/KONTO.md, 5.4.")
        else:
            print("Weder Tabellen noch Zeilenschutz sind bis hierhin im")
            print("Spiel - das ist noch der Anmeldedienst allein.")
        return 1
    sitzung = str(angelegt.daten.get("sitzung", ""))
    kennung = str(angelegt.daten.get("kennung", ""))

    schritt("Anmelden", netz.anmelden(name, wort))
    gelesen = netz.profil_lesen(sitzung)
    schritt("Profil lesen", gelesen,
            "Fassung %s" % (gelesen.daten.get("fassung") if gelesen else "-"))
    if gelesen:
        profil = dict(gelesen.daten)
        profil["werte"] = {"selbsttest": 1}
        geschrieben = netz.profil_schreiben(sitzung, profil)
        schritt("Profil schreiben", geschrieben,
                "Fassung %s" % (geschrieben.daten.get("fassung")
                                if geschrieben else "-"))

    # Die Zeile muss genauso aussehen wie die, die das Spiel schickt -
    # `konto` eingeschlossen (konto.py setzt es beim Abgleich). Ein
    # Selbsttest, der eine andere Zeile schickt als der Spielcode,
    # prueft etwas, das es nicht gibt.
    partie = "selbsttest-" + A.kennung()
    runde = [{"partie": partie, "konto": kennung, "gespielt": int(time.time()),
              "modus": "pruef", "team": 0, "gewonnen": True,
              "gastgeber": True, "werte": {"abschuesse": 1}, "waffen": {}}]
    gebucht = schritt("Runde buchen", netz.gefechte_senden(sitzung, runde),
                      partie[:20])
    schritt("Dieselbe Runde noch einmal buchen",
            netz.gefechte_senden(sitzung, runde))

    # Und dieselbe Runde auf fremden Namen. Das ist der Versuch, den ein
    # veraenderter Klient machen wuerde: Zahlen fuer ein anderes Konto
    # schreiben. Er muss scheitern, und zwar am Server.
    fremd = [dict(runde[0], partie=partie + "-fremd",
                  konto="00000000-0000-0000-0000-000000000001")]
    abgelehnt = not netz.gefechte_senden(sitzung, fremd)
    schritte.append(abgelehnt)
    print(("  ok    " if abgelehnt else "FEHLER  ")
          + "Eine Runde auf fremden Namen wird abgelehnt")
    if not abgelehnt:
        fehler.append(("Zeilenschutz", "fremde Zeile angenommen"))
        print()
        print("Der Server nimmt Zahlen fuer ein fremdes Konto an. Damit")
        print("kann jeder jedem alles anschreiben. Die Regel 'eigene")
        print("gefechte anlegen' aus docs/KONTO.md 5.2 fehlt oder passt")
        print("nicht.")

    zurueck = netz.gefechte_lesen(sitzung)
    if schritt("Runden zurueklesen", zurueck) and gebucht:
        # Nur pruefen, wenn das Buchen ueberhaupt durchkam. Sonst steht
        # dort 0x, und die Meldung schoebe es auf den fehlenden Index -
        # also auf etwas, das gar nicht dran war.
        wie_oft = sum(1 for z in zurueck.daten.get("gefechte", [])
                      if z.get("partie") == partie)
        doppelt = (wie_oft == 1)
        schritte.append(doppelt)
        print(("  ok    " if doppelt else "FEHLER  ")
              + "Sie steht genau einmal da   %dx" % wie_oft)
        if not doppelt:
            fehler.append(("Doppelschutz", "%dx statt 1x" % wie_oft))
            print()
            print("Der eindeutige Index auf (partie, konto) fehlt. Ohne ihn")
            print("zaehlt jeder Wiederholungsversuch noch einmal. Das SQL")
            print("aus docs/KONTO.md 5.2 noch einmal ausfuehren.")

    # Der Zeilenschutz. Er ist die einzige Zusage in docs/KONTO.md, die
    # nicht davon abhaengt, dass sich der Klient benimmt - und genau
    # darum muss sie geprueft werden. Gelesen wird hier mit dem
    # oeffentlichen Schluessel allein, ohne Sitzung: so weit kommt jeder,
    # der das Spiel herunterlaedt. Was dabei zu sehen ist, ist das, was
    # ein veraenderter Klient sehen koennte.
    ohne = netz.gefechte_lesen("")
    sichtbar = len(ohne.daten.get("gefechte", [])) if ohne else -1
    dicht = (sichtbar == 0)
    schritte.append(dicht)
    print(("  ok    " if dicht else "FEHLER  ")
          + "Ohne Anmeldung ist nichts zu sehen   %s"
          % ("nichts" if dicht else "%d Zeilen" % sichtbar))
    if not dicht:
        fehler.append(("Zeilenschutz", "%d Zeilen ohne Anmeldung" % sichtbar))
        print()
        print("Der Zeilenschutz steht nicht. Ohne ihn kann jeder, der das")
        print("Spiel herunterlaedt, alle Zahlen aller Spieler lesen - der")
        print("Schluessel liegt ja im Quelltext. Das SQL aus docs/KONTO.md")
        print("5.2 ab 'alter table ... enable row level security' noch")
        print("einmal ausfuehren.")

    print()
    if fehler:
        print("FEHLER: %d von %d Schritten" % (len(fehler), len(schritte)))
        return 1
    print("Alle %d Schritte in Ordnung. Der Server traegt." % len(schritte))
    print("Das Wegwerfkonto %s bleibt stehen." % name)
    return 0


def pfade_text() -> str:
    from . import pfade
    return pfade.beschreibung()


def team_lesen(text: str) -> int | None:
    """"rot", "blau" oder "auto" in eine Mannschaftsnummer uebersetzen."""
    text = (text or "").strip().lower()
    if not text or text in ("auto", "egal", "-"):
        return None
    for i, name in enumerate(K.TEAMS["namen"]):
        if text == name.lower() or text == str(i + 1):
            return i
    return None


def aus_argumenten(argumente: list[str]) -> int:
    """Wertet die Kommandozeile aus. Ohne Schalter startet das Spiel."""
    def wert(schalter, vorgabe=""):
        if schalter in argumente:
            i = argumente.index(schalter)
            if i + 1 < len(argumente):
                return argumente[i + 1]
        return vorgabe

    if "--host" in argumente:
        modus = wert("--modus", K.MODUS_VORGABE).strip().lower()
        if modus not in K.MODI:
            print("Unbekannte Spielart %r. Moeglich: %s"
                  % (modus, ", ".join(K.MODI)))
            return 1
        ende_art = wert("--ende", "zeit").strip().lower()
        if ende_art not in K.ENDE_ARTEN:
            print("Unbekanntes Ende %r. Moeglich: %s"
                  % (ende_art, ", ".join(K.ENDE_ARTEN)))
            return 1
        try:
            ende_wert = float(wert("--wert", "0") or 0)
        except ValueError:
            print("--wert braucht eine Zahl.")
            return 1
        try:
            medkits = int(wert("--medkits", str(K.GEFECHT["start_medkits"])))
        except ValueError:
            print("--medkits braucht eine ganze Zahl.")
            return 1
        try:
            runden = int(wert("--runden", str(K.VERSUS["runden_bis"])))
        except ValueError:
            print("--runden braucht eine ganze Zahl.")
            return 1
        return gefecht(True, name=wert("--name", "GASTGEBER"),
                       port=int(wert("--port", "0") or 0),
                       modus=modus, ende_art=ende_art, ende_wert=ende_wert,
                       knapp="--knapp" in argumente,
                       schutz="--kein-schutz" not in argumente,
                       medkits=medkits, runden=runden,
                       team=team_lesen(wert("--team", "")),
                       online="--online" in argumente,
                       passwort=wert("--passwort", ""),
                       loadouts=("eigenes" if "--loadouts" in argumente
                                 else None),
                       karte=wert("--karte", ""),
                       medkit_spawn="--keine-medkits" not in argumente)
    if "--join" in argumente:
        return gefecht(False, wohin=wert("--join"),
                       name=wert("--name", "GAST"),
                       passwort=wert("--passwort", ""),
                       team=team_lesen(wert("--team", "")))
    if "--bestenliste" in argumente:
        from . import bestenliste
        daten = bestenliste.laden()
        print("Bestenliste: %s" % bestenliste.beschreibung())
        if not daten["eintraege"]:
            print("  noch leer")
        for platz, e in enumerate(daten["eintraege"], 1):
            print("  %2d. %-12s %4d Abschuesse  %4d Tode  %3d Runden"
                  % (platz, e["name"], e["abschuesse"], e["tode"], e["runden"]))
        return 0
    if "--kosmetik" in argumente:
        from .core import Bilder
        from .kosmetik import schreiben
        import pygame
        pygame.init()
        pygame.display.set_mode((64, 64))
        pfade = schreiben(Bilder(asset_ordner()))
        print("Vorschau geschrieben - eingebaut ist davon nichts:")
        for p in pfade:
            print("  %s" % p)
        pygame.quit()
        return 0
    if "--kontoseite" in argumente:
        # Das Werkzeug liegt im Wurzelverzeichnis, nicht im Paket: es
        # gehoert nicht zum Spiel, es baut nur eine Datei daneben.
        import sys as _sys
        from pathlib import Path as _Path
        _sys.path.insert(0, str(_Path(__file__).resolve().parent.parent))
        import werkzeug_kontoseite
        ziel = werkzeug_kontoseite.schreiben(wert("--kontoseite", "")
                                             or werkzeug_kontoseite.ZIEL)
        print("Kontoseite geschrieben: %s (%.0f KB)"
              % (ziel, ziel.stat().st_size / 1024.0))
        print("Zum Ansehen die Datei doppelklicken.")
        return 0
    if "--karten" in argumente:
        from . import world as W
        namen = W.karten_liste()
        print("Karten in %s:" % W.kartenordner())
        if not namen:
            print("  keine - das Spiel nimmt dann seine Testkarte")
        for n in namen:
            welt, kopf = W.karte_lesen(n)
            if welt is None:
                print("  %-14s KAPUTT" % n)
                continue
            e = welt.ebene(0)
            print("  %-14s %s, %d Ebenen, %d x %d Kacheln"
                  % (n, kopf.get("name", n), len(welt.ebenen), e.breite, e.hoehe))
        return 0
    if "--konto" in argumente:
        return konten(argumente, wert)
    if "--vorlagen" in argumente:
        from .vorlagen import schreiben
        schreiben()
        return 0
    if "--assets" in argumente:
        from .vorlagen import bestand
        return bestand()
    return starten()
