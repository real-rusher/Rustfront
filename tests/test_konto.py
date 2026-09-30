"""
DUSTFRONT - Pruefungen fuer Konto, Loadouts und Journal
=======================================================

Gemessen wird das, worauf es bei diesem Teil ankommt: dass **keine Zahl
verschwindet und keine doppelt zaehlt**, auch dann nicht, wenn das Netz
mitten im Satz aufhoert. Dafuer gibt es hier eine Steckdose, die genau
das tut - sie bestaetigt und antwortet dann nicht.

Nichts davon braucht ein Netz oder einen Server. Die Netzablage wird
gegen eine nachgebaute HTTP-Schicht geprueft, die lokale gegen einen
Ordner in `tempfile`.
"""
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dustfront import ablage
from dustfront import config as K
from dustfront import konto as konto_modul

fails = []


def pruef(text, bedingung, zusatz=""):
    if bedingung:
        print("  ok  %s%s" % (text, "   " + zusatz if zusatz else ""))
    else:
        print("FAIL  %s%s" % (text, "   " + zusatz if zusatz else ""))
        fails.append(text)


arbeitsordner = Path(tempfile.mkdtemp(prefix="dustfront-konto-"))


def frischer_ordner(name):
    ziel = arbeitsordner / name
    ziel.mkdir(parents=True, exist_ok=True)
    return ziel


# ══════════════════════════════════════════════════ Namen und Kennwoerter
print("\n-- Namen und Kennwoerter --")
pruef("Ein Name wird auf Erlaubtes zusammengestrichen",
      ablage.name_saeubern("  Der Meister!! <3 ") == "DerMeister3",
      ablage.name_saeubern("  Der Meister!! <3 "))
pruef("Zu kurze Namen werden abgelehnt",
      ablage.name_pruefen("ab") != "" and ablage.name_pruefen("abc") == "")
pruef("Ein Name muss mit Buchstabe oder Ziffer anfangen",
      ablage.name_pruefen("-abc") != "")
pruef("Zu kurze Kennwoerter werden abgelehnt",
      ablage.wort_pruefen("kurz") != "" and ablage.wort_pruefen("langgenug") == "")
pruef("Kennwortlaenge ist die einzige Regel",
      "SONDERZEICHEN" not in ablage.wort_pruefen("kurz").upper())
kennungen = {ablage.kennung() for _ in range(2000)}
pruef("Kennungen kommen nicht zweimal vor", len(kennungen) == 2000,
      "%d von 2000" % len(kennungen))

# ══════════════════════════════════════════════════ Lokale Ablage
print("\n-- Lokale Ablage --")
lok = ablage.LokaleAblage(ordner=frischer_ordner("lokal"))
pruef("Ein Konto laesst sich anlegen", bool(lok.anlegen("Meister", "geheim12345")))
pruef("Derselbe Name nicht zweimal",
      not lok.anlegen("meister", "anderes12345"),
      lok.anlegen("meister", "anderes12345").fehler)
pruef("Ein zu kurzes Kennwort kommt nicht durch",
      not lok.anlegen("Zweiter", "kurz"))
an = lok.anmelden("MEISTER", "geheim12345")
pruef("Anmelden klappt, Gross- und Kleinschreibung egal", bool(an), an.fehler)
pruef("Mit falschem Kennwort nicht",
      not lok.anmelden("Meister", "falsch12345"))
pruef("Und die Auskunft verraet nicht, welche Namen es gibt",
      lok.anmelden("Meister", "falsch12345").fehler
      == lok.anmelden("GibtEsNicht", "falsch12345").fehler)

# Das Kennwort darf nirgends im Klartext stehen. Das ist keine Formalie:
# eine Datei im Benutzerordner liest jeder, der am Rechner sitzt.
roh = (arbeitsordner / "lokal" / ablage.KONTEN_DATEI).read_text(encoding="utf-8")
pruef("Kein Kennwort liegt im Klartext auf der Platte",
      "geheim12345" not in roh)
eintrag = json.loads(roh)["konten"]["meister"]
pruef("Stattdessen ein Hash mit eigenem Salz",
      len(eintrag["hash"]) > 20 and len(eintrag["salz"]) > 10)
zweiter = ablage.LokaleAblage(ordner=frischer_ordner("lokal2"))
zweiter.anlegen("Meister", "geheim12345")
zweit_hash = json.loads(
    (arbeitsordner / "lokal2" / ablage.KONTEN_DATEI).read_text(
        encoding="utf-8"))["konten"]["meister"]["hash"]
pruef("Gleiches Kennwort ergibt zwei verschiedene Hashes",
      zweit_hash != eintrag["hash"])

sitzung = an.daten["sitzung"]
pruef("Eine Sitzung laesst sich pruefen", bool(lok.sitzung_pruefen(sitzung)))
pruef("Eine erfundene Sitzung nicht", not lok.sitzung_pruefen("lokal:niemand"))

# ══════════════════════════════════════════════════ Profil und Fassungen
print("\n-- Profil: zwei Rechner ueberschreiben sich nicht --")
p = lok.profil_lesen(sitzung)
pruef("Ein neues Profil ist leer und hat Fassung 0",
      p and p.daten["fassung"] == 0 and p.daten["loadouts"] == [])
erst = lok.profil_schreiben(sitzung, {"fassung": 0, "werte": {"a": 1},
                                      "loadouts": [{"name": "EINS"}]})
pruef("Schreiben erhoeht die Fassung",
      erst and erst.daten["fassung"] == 1, str(erst.daten.get("fassung")))
# Jetzt kommt ein zweiter Rechner mit einem veralteten Stand.
alt = lok.profil_schreiben(sitzung, {"fassung": 0, "werte": {"a": 999},
                                     "loadouts": [{"name": "FALSCH"}]})
pruef("Ein veralteter Stand wird abgelehnt", not alt, alt.fehler)
pruef("Und die Ablehnung bringt den neuen Stand mit",
      alt.daten.get("fassung") == 1 and alt.daten["werte"] == {"a": 1},
      str(alt.daten))
jetzt = lok.profil_lesen(sitzung)
pruef("Der erste Stand steht unveraendert da",
      jetzt.daten["werte"] == {"a": 1}, str(jetzt.daten["werte"]))

# ══════════════════════════════════════════════════ Loadouts
print("\n-- Loadouts --")
lo = K.LOADOUT
pruef("Ein leeres Loadout wird auf volle Laenge gebrac",
      len(konto_modul.loadouts_saeubern([])) == lo["plaetze"])
sauber = konto_modul.loadout_saeubern(
    {"name": "  mein satz!! ", "waffen": ["sturm", "sturm", "gibtsnicht",
                                          "schrot", "scharf"],
     "wuerfe": ["rauch", "granate", "unsinn"]})
pruef("Doppelte, unbekannte und zu viele Waffen fliegen raus",
      sauber["waffen"] == ["sturm", "schrot"]
      and sauber["wuerfe"] == ["rauch"], str(sauber))
pruef("Der Name wird gesaeubert und gekuerzt",
      sauber["name"] == "MEIN SATZ" and len(sauber["name"]) <= lo["namenslaenge"],
      sauber["name"])
leer = konto_modul.loadout_saeubern({"name": "", "waffen": [], "wuerfe": []})
pruef("Ein leeres wird aufgefuellt statt abgelehnt",
      len(leer["waffen"]) == lo["waffen"] and len(leer["wuerfe"]) == lo["wuerfe"],
      str(leer))
pruef("Unsinn ergibt None", konto_modul.loadout_saeubern("kein dict") is None)
pruef("Jede Vorlage ist gueltig",
      all(len(v["waffen"]) == lo["waffen"] and len(v["wuerfe"]) == lo["wuerfe"]
          for v in konto_modul.loadout_vorlagen()))
hb = konto_modul.hotbar_aus_loadout({"waffen": ["scharf", "sturm"],
                                     "wuerfe": ["rauch"]})
pruef("Die Hotbar folgt der gewohnten Reihenfolge",
      hb == ["sturm", "scharf", "rauch"], str(hb))
pruef("Und traegt genau die gewaehlten Plaetze",
      len(hb) == lo["waffen"] + lo["wuerfe"])

# ══════════════════════════════════════════════════ Journal
print("\n-- Journal: keine Runde verloren, keine doppelt --")
jo = konto_modul.Journal(ordner=frischer_ordner("journal"))
jo.dazu({"partie": "a", "werte": {"abschuesse": 3, "tode": 1}})
jo.dazu({"partie": "b", "werte": {"abschuesse": 5, "tode": 2}})
pruef("Zwei Runden liegen im Journal", len(jo.eintraege) == 2)
pruef("Und beide sind offen", len(jo.offen()) == 2)
jo.dazu({"partie": "a", "werte": {"abschuesse": 3, "tode": 1}})
pruef("Dieselbe Partie zweimal bleibt eine", len(jo.eintraege) == 2)
summe = jo.summe()
pruef("Die Uebersicht rechnet zusammen",
      summe["abschuesse"] == 8 and summe["tode"] == 3,
      "%s Abschuesse, %s Tode" % (summe["abschuesse"], summe["tode"]))
pruef("Ganze Zahlen bleiben ganz", isinstance(summe["abschuesse"], int))
jo.dazu({"partie": "c", "werte": {"abschuesse_r": 7}})
jo.dazu({"partie": "d", "werte": {"abschuesse_r": 4}})
pruef("Ein Bestwert wird nicht addiert, sondern verglichen",
      jo.summe()["abschuesse_r"] == 7, str(jo.summe()["abschuesse_r"]))
jo.abhaken(["a", "b"])
pruef("Bestaetigte Runden sind abgehakt", len(jo.offen()) == 2)
pruef("Und bleiben trotzdem in der Uebersicht",
      jo.summe()["abschuesse"] == 8)
jo.dazu({"partie": "a", "werte": {"abschuesse": 3}})
pruef("Eine abgehakte Runde wird durch eine zweite Meldung nicht wieder offen",
      len([e for e in jo.eintraege
           if e["partie"] == "a" and not e["abgeglichen"]]) == 0)
# Und der Neustart: was auf der Platte liegt, muss wieder hochkommen.
noch = konto_modul.Journal(ordner=arbeitsordner / "journal")
pruef("Nach einem Neustart steht alles wieder da",
      len(noch.eintraege) == 4 and noch.summe()["abschuesse"] == 8,
      "%d Eintraege" % len(noch.eintraege))
pruef("Auch die Haken",
      len(noch.offen()) == 2, "%d offen" % len(noch.offen()))

# Eine kaputte Datei darf nichts umwerfen.
(arbeitsordner / "journal" / konto_modul.JOURNAL_DATEI).write_text(
    "{kein json", encoding="utf-8")
kaputt = konto_modul.Journal(ordner=arbeitsordner / "journal")
pruef("Eine beschaedigte Journaldatei kostet nur das Journal",
      kaputt.eintraege == [])

# ══════════════════════════════════════════════════ Konto im Ganzen
print("\n-- Konto: anmelden, spielen, abgleichen --")
ordner_k = frischer_ordner("konto")
abl = ablage.LokaleAblage(ordner=ordner_k)
# mit_faden=False: die Pruefungen sollen nicht auf einen Thread warten.
kt = konto_modul.Konto(ablage_=abl, ordner=ordner_k, mit_faden=False)
pruef("Ohne Anmeldung ist niemand angemeldet", not kt.angemeldet)
pruef("Trotzdem stehen drei Loadouts bereit",
      len(kt.loadouts) == lo["plaetze"])
pruef("Und die Anmeldemaske sagt, wo das Konto gilt",
      "RECHNER" in kt.beschreibung(), kt.beschreibung())

# Ohne Anmeldung gespielt: die Runde muss trotzdem gezaehlt werden.
kt.runde_eintragen({"modus": "pvp", "werte": {"abschuesse": 4, "tode": 1}})
pruef("Eine Runde ohne Anmeldung landet trotzdem im Journal",
      kt.uebersicht()["abschuesse"] == 4)

kt.anlegen("Meister", "geheim12345")
pruef("Anlegen meldet gleich an", kt.angemeldet and kt.name == "Meister",
      kt.fehler or kt.name)
pruef("Die frueher gespielte Runde gehoert jetzt zum Konto",
      all(e.get("konto") == kt.kennung for e in kt.journal.eintraege))
pruef("Und zaehlt nur einmal", kt.uebersicht()["abschuesse"] == 4)

kt.loadout_setzen(0, {"name": "MEIN", "waffen": ["scharf", "schrot"],
                      "wuerfe": ["rauch"]})
pruef("Ein Loadout laesst sich aendern",
      kt.loadouts[0]["name"] == "MEIN"
      and kt.loadouts[0]["waffen"] == ["scharf", "schrot"])
pruef("Das Profil steht danach in Fassung 1 oder hoeher",
      kt.profil_fassung >= 1, str(kt.profil_fassung))
kt.loadout_waehlen(2)
pruef("Und eines laesst sich waehlen", kt.loadout is kt.loadouts[2])
pruef("Beim ersten Mal wird nach einem Loadout gefragt",
      not kt.loadout_gewaehlt_je)
kt.loadout_bestaetigen()
pruef("Danach nicht mehr", kt.loadout_gewaehlt_je)

kt.abgleichen()
pruef("Der Abgleich hakt die Runde ab", len(kt.journal.offen()) == 0,
      "%d offen" % len(kt.journal.offen()))
kt.runde_eintragen({"modus": "pvp", "werte": {"abschuesse": 2}})
kt.abgleichen()
kt.abgleichen()
kt.abgleichen()
beim_server = abl.gefechte_lesen(kt.sitzung).daten["gefechte"]
pruef("Dreimal abgleichen speichert nicht dreimal",
      len(beim_server) == 2, "%d Zeilen beim Server" % len(beim_server))
pruef("Die Summe stimmt weiterhin", kt.uebersicht()["abschuesse"] == 6,
      str(kt.uebersicht()["abschuesse"]))

# Neustart: Sitzung, Loadouts und Journal muessen wieder da sein.
kt.schliessen()
neu = konto_modul.Konto(ablage_=abl, ordner=ordner_k, mit_faden=False)
pruef("Nach einem Neustart ist man noch angemeldet",
      neu.angemeldet and neu.name == "Meister")
pruef("Die Loadouts sind noch da", neu.loadouts[0]["name"] == "MEIN",
      neu.loadouts[0]["name"])
pruef("Das gewaehlte auch", neu.gewaehlt == 2, str(neu.gewaehlt))
pruef("Und die Runden", neu.uebersicht()["abschuesse"] == 6)
neu.abmelden()
pruef("Abmelden loest die Sitzung", not neu.angemeldet)
pruef("Laesst die Runden aber stehen", neu.uebersicht()["abschuesse"] == 6)

# ══════════════════════════════════════════════════ Netz, ohne Netz
print("\n-- Netzablage gegen eine nachgebaute Leitung --")


class FalscherServer:
    """Ein Supabase, das es nicht gibt. Nur so viel, wie geprueft wird.

    Der Sinn: die Netzablage muss vollstaendig geprueft werden koennen,
    ohne dass irgendwo ein Projekt laeuft. Und der Aussetzer weiter unten
    - bestaetigen und dann die Verbindung fallen lassen - ist der Fall,
    auf den es bei "keine Zahl doppelt" wirklich ankommt.
    """

    def __init__(self):
        self.konten = {}
        self.profile = {}
        self.gefechte = {}          # (partie, konto) -> Zeile
        self.aussetzen = 0          # so viele Antworten fallen noch aus
        self.anfragen = []

    def __call__(self, anfrage, timeout=None):
        import io
        import urllib.error
        weg = anfrage.full_url
        koerper = json.loads(anfrage.data.decode()) if anfrage.data else None
        token = (anfrage.get_header("Authorization") or "")[7:]
        self.anfragen.append((anfrage.get_method(), weg))
        antwort, code = self._bearbeiten(anfrage.get_method(), weg, koerper, token)
        if self.aussetzen > 0:
            # Geschrieben ist geschrieben - nur die Antwort kommt nicht
            # an. Genau so verliert ein Klient die Gewissheit.
            self.aussetzen -= 1
            raise urllib.error.URLError("Leitung weg")
        if code >= 400:
            raise urllib.error.HTTPError(
                weg, code, "Fehler", {},
                io.BytesIO(json.dumps(antwort).encode()))

        class Fenster:
            def __enter__(self_inner):
                return self_inner

            def __exit__(self_inner, *a):
                return False

            def read(self_inner):
                return json.dumps(antwort).encode()

        return Fenster()

    def _bearbeiten(self, methode, weg, koerper, token):
        if "/auth/v1/signup" in weg:
            post = koerper["email"]
            if post in self.konten:
                return {"msg": "User already registered"}, 400
            wer = "id-%d" % (len(self.konten) + 1)
            self.konten[post] = (wer, koerper["password"])
            self.profile[wer] = {"fassung": 0, "werte": {}, "loadouts": []}
            return {"access_token": "tok-" + wer, "refresh_token": "ern",
                    "user": {"id": wer,
                             "user_metadata": {"name": koerper["data"]["name"]}}}, 200
        if "grant_type=password" in weg:
            eintrag = self.konten.get(koerper["email"])
            if eintrag is None or eintrag[1] != koerper["password"]:
                return {"msg": "Invalid login credentials"}, 400
            return {"access_token": "tok-" + eintrag[0], "refresh_token": "ern",
                    "user": {"id": eintrag[0]}}, 200
        if "/auth/v1/user" in weg:
            wer = token[4:]
            if wer not in self.profile:
                return {"msg": "bad jwt"}, 401
            return {"id": wer, "user_metadata": {"name": "Meister"}}, 200
        if "/auth/v1/logout" in weg:
            return {}, 200
        wer = token[4:]
        if "/rest/v1/profil" in weg:
            if methode == "GET":
                p = self.profile.get(wer)
                return ([dict(p)] if p else []), 200
            if methode == "POST":
                self.profile.setdefault(wer, {"fassung": 0, "werte": {},
                                              "loadouts": []})
                return {}, 201
            if methode == "PATCH":
                erwartet = int(weg.split("fassung=eq.")[1].split("&")[0])
                p = self.profile.get(wer) or {"fassung": 0}
                if int(p["fassung"]) != erwartet:
                    return [], 200          # nichts getroffen
                p = {"fassung": erwartet + 1,
                     "werte": koerper["werte"], "loadouts": koerper["loadouts"]}
                self.profile[wer] = p
                return [dict(p)], 200
        if "/rest/v1/gefecht" in weg:
            if methode == "GET":
                return [z for (p, k), z in self.gefechte.items() if k == wer], 200
            for zeile in koerper:
                # Der Zeilenschutz, nachgebaut: `with check (auth.uid() =
                # konto)`. Wer eine Zeile auf fremden Namen schickt,
                # bekommt sie zurueck. Ohne das hier haette der
                # nachgebaute Server eine Luecke, die der echte nicht
                # hat - und dann prueft der Test etwas Schwaecheres.
                if str(zeile.get("konto") or wer) != wer:
                    return {"message": "new row violates row-level security"
                                       " policy for table \"gefecht\""}, 403
                schluessel = (str(zeile.get("partie")), wer)
                # ignore-duplicates: was schon da ist, bleibt, wie es ist.
                self.gefechte.setdefault(schluessel, zeile)
            return {}, 201
        return {"msg": "unbekannt"}, 404


import urllib.request

server = FalscherServer()
echt_urlopen = urllib.request.urlopen
urllib.request.urlopen = server

netz = ablage.NetzAblage(url="https://test.supabase.co", schluessel="anon")
pruef("Eine Netzablage mit Zugang gilt als eingerichtet", netz.eingerichtet)
# Leere Angaben heissen "nimm den eingetragenen Zugang", nicht "keiner".
# Solange in SERVER nichts stand, war das dasselbe; seit dort ein echtes
# Projekt steht, ist es das nicht mehr. Fuer "kein Zugang" muss also der
# eingetragene weg - so, wie es bei jemandem aussieht, der das Spiel ohne
# Server benutzt.
_zugang_vorher = dict(ablage.SERVER)
ablage.SERVER.update(url="", schluessel="")
pruef("Ohne Zugang gilt eine Netzablage als nicht eingerichtet",
      not ablage.NetzAblage(url="", schluessel="").eingerichtet)
pruef("Und antwortet dann sauber statt zu werfen",
      not ablage.NetzAblage(url="", schluessel="").anmelden("a", "b"))
ablage.SERVER.clear()
ablage.SERVER.update(_zugang_vorher)
pruef("Leere Angaben nehmen sonst den eingetragenen Zugang",
      ablage.NetzAblage(url="", schluessel="").url == ablage.SERVER["url"])

an = netz.anlegen("Meister", "geheim12345")
pruef("Ein Konto laesst sich auf dem Server anlegen", bool(an), an.fehler)
pruef("Zweimal derselbe Name nicht",
      not netz.anlegen("Meister", "geheim12345"))
pruef("Das Kennwort geht nur an den Anmeldedienst",
      all("/auth/" in weg for methode, weg in server.anfragen
          if methode == "POST" and "signup" in weg))
tok = an.daten["sitzung"]
wer = an.daten["kennung"]          # die Kennung des Kontos, wie im Spiel
pruef("Anmelden klappt", bool(netz.anmelden("Meister", "geheim12345")))
pruef("Mit falschem Kennwort nicht",
      not netz.anmelden("Meister", "falsch12345"))
pruef("Die Auskunft nennt keinen Grund",
      netz.anmelden("Meister", "falsch12345").fehler == "NAME ODER KENNWORT FALSCH")
pruef("Eine Sitzung laesst sich pruefen", bool(netz.sitzung_pruefen(tok)))
pruef("Eine erfundene nicht", not netz.sitzung_pruefen("tok-niemand"))

erst = netz.profil_schreiben(tok, {"fassung": 0, "werte": {"a": 1},
                                   "loadouts": [{"name": "EINS"}]})
pruef("Ein Profil laesst sich schreiben",
      erst and erst.daten["fassung"] == 1, str(erst.daten.get("fassung")))
alt = netz.profil_schreiben(tok, {"fassung": 0, "werte": {"a": 9},
                                  "loadouts": []})
pruef("Ein veralteter Stand wird auch hier abgelehnt", not alt, alt.fehler)
pruef("Und der neue Stand kommt mit",
      alt.daten.get("fassung") == 1, str(alt.daten))

# Der eigentliche Punkt: ein Aussetzer nach dem Schreiben.
# `konto` ist die eigene Kennung, nicht irgendein Platzhalter: der
# Server laesst seit dem Zeilenschutz nichts anderes durch, und der
# Spielcode setzt es in konto.py genauso.
zeile = {"partie": "p1", "konto": wer, "gespielt": 1,
         "modus": "pvp", "werte": {"abschuesse": 3}}
server.aussetzen = 1
erster = netz.gefechte_senden(tok, [zeile])
pruef("Ein Aussetzer wird als Fehler gemeldet, nicht verschluckt",
      not erster, erster.fehler)
pruef("Geschrieben hat der Server trotzdem", len(server.gefechte) == 1)
zweiter = netz.gefechte_senden(tok, [zeile])
pruef("Der Wiederholungsversuch geht durch", bool(zweiter), zweiter.fehler)
pruef("Und die Runde steht genau einmal da", len(server.gefechte) == 1,
      "%d Zeilen" % len(server.gefechte))
gelesen = netz.gefechte_lesen(tok)
pruef("Sie laesst sich wieder lesen",
      gelesen and len(gelesen.daten["gefechte"]) == 1)

# Und dasselbe durch das ganze Konto hindurch, mit Aussetzer in der Mitte.
print("\n-- Konto gegen den Server, mit Aussetzer --")
ordner_n = frischer_ordner("netzkonto")
kn = konto_modul.Konto(ablage_=netz, ordner=ordner_n, mit_faden=False)
kn.anmelden("Meister", "geheim12345")
pruef("Angemeldet ueber den Server", kn.angemeldet, kn.fehler)
pruef("Das Konto weiss, dass es am Server haengt", kn.mit_server)
kn.runde_eintragen({"modus": "pvp", "werte": {"abschuesse": 7, "tode": 2}})
server.aussetzen = 1
kn._ruhe = 0.0
kn.abgleichen()
pruef("Nach einem Aussetzer bleibt die Runde offen",
      len(kn.journal.offen()) == 1)
pruef("Und die Anzeige stimmt trotzdem sofort",
      kn.uebersicht()["abschuesse"] == 7)
kn._ruhe = 0.0
kn.abgleichen()
pruef("Der naechste Versuch hakt sie ab", len(kn.journal.offen()) == 0)
# Nur die Partien dieses Kontos zaehlen - die Zeile "p1" weiter oben
# wurde von Hand geschickt und gehoert nicht zum Journal.
meine = {str(e["partie"]) for e in kn.journal.eintraege}
eigene = [z for (p, k), z in server.gefechte.items()
          if k == kn.kennung and p in meine]
pruef("Beim Server steht sie einmal", len(eigene) == 1,
      "%d Zeilen" % len(eigene))
pruef("Und mit den richtigen Zahlen",
      eigene and eigene[0]["werte"]["abschuesse"] == 7)
pruef("Das Merkzeichen des Journals geht nicht mit hoch",
      eigene and "abgeglichen" not in eigene[0])

# Nach einem Fehler wird nicht im Sekundentakt weitergefragt.
server.aussetzen = 1
kn.runde_eintragen({"modus": "pvp", "werte": {"abschuesse": 1}})
kn._ruhe = 0.0
kn.abgleichen()
pruef("Nach einem Fehler gibt es kurz Ruhe", kn._ruhe > 0.0)
pruef("Und in dieser Ruhe wird nicht gefragt", not kn.abgleichen())
kn.schritt(K.KONTO["ruhe_nach_fehler"] + 1.0)
pruef("Danach wieder", len(kn.journal.offen()) == 0,
      "%d offen" % len(kn.journal.offen()))
kn.schliessen()

# ─────────────────────────────────────────────────────────────────────
# Der Selbsttest --konto server.
#
# Er ist das Werkzeug, mit dem ein frisch aufgesetztes Supabase-Projekt
# abgenommen wird. Also muss er selbst geprueft sein, und zwar in beide
# Richtungen: er muss ein gutes Projekt durchwinken **und** ein kaputtes
# durchfallen lassen. Ein Selbsttest, der immer "in Ordnung" sagt, ist
# schlimmer als keiner.
print("\n-- Der Selbsttest fuer den Server --")
from dustfront import main as main_modul

def _wert_aus(paare):
    return lambda name, vorgabe="": paare.get(name, vorgabe)

class GuterZugang(ablage.NetzAblage):
    def __init__(self, *a, **k):
        super().__init__(url="https://test.supabase.co", schluessel="anon")

_echte_netzablage = ablage.NetzAblage
ablage.NetzAblage = GuterZugang
_rueck = main_modul.konto_server_pruefen(ablage, _wert_aus({}))
pruef("Der Selbsttest winkt ein heiles Projekt durch", _rueck == 0,
      "Rueckgabe %d" % _rueck)

# Und jetzt dasselbe mit einem Server, dem der eindeutige Index fehlt -
# der eine Fehler, der im Betrieb niemandem auffaellt und trotzdem alle
# Zahlen verdirbt. Der Selbsttest muss ihn finden.
class ServerOhneIndex(FalscherServer):
    """Genau ein Mangel: kein eindeutiger Index. Alles andere heil.

    Das ist Absicht. Wer hier mehr kaputtmacht, prueft nicht mehr, ob
    der Selbsttest *diesen* Mangel findet, sondern nur noch, ob er
    irgendetwas findet.
    """

    def _bearbeiten(self, methode, weg, koerper, token):
        if "/rest/v1/gefecht" in weg and methode == "POST":
            for zeile in koerper:
                if str(zeile.get("konto") or token[4:]) != token[4:]:
                    return {"message": "new row violates row-level security"
                                       " policy for table \"gefecht\""}, 403
                # kein setdefault: jede Sendung haengt eine Zeile an
                self.gefechte[(str(zeile.get("partie")),
                               token[4:], len(self.gefechte))] = zeile
            return {}, 201
        if "/rest/v1/gefecht" in weg and methode == "GET":
            return [z for s, z in self.gefechte.items()
                    if s[1] == token[4:]], 200
        return super()._bearbeiten(methode, weg, koerper, token)

urllib.request.urlopen = ServerOhneIndex()
_rueck = main_modul.konto_server_pruefen(ablage, _wert_aus({}))
pruef("Und laesst ein Projekt ohne Doppelschutz durchfallen", _rueck == 1,
      "Rueckgabe %d" % _rueck)

ablage.NetzAblage = _echte_netzablage
urllib.request.urlopen = echt_urlopen

# Ohne eingetragenen Server sagt er das und faellt nicht um.
#
# **Der Zugang muss dafuer wirklich weg.** Seit in SERVER ein echtes
# Projekt steht, wuerde dieser Aufruf sonst hinausgehen und dort ein
# Wegwerfkonto anlegen - eine Testreihe, die das Netz anfasst, ist keine
# Testreihe mehr. Genau das ist hier einmal passiert.
_zugang_vorher = dict(ablage.SERVER)
ablage.SERVER.update(url="", schluessel="")
pruef("Ohne Zugang sagt der Selbsttest das",
      main_modul.konto_server_pruefen(ablage, _wert_aus({})) == 1)
ablage.SERVER.clear()
ablage.SERVER.update(_zugang_vorher)

# ══════════════════════════════════════════════════ Der Faden
print("\n-- Der Faden fuer das Netz --")
werk = konto_modul.Werk()
werk.auftrag("a", lambda: ablage.gut({"x": 1}))


def krachen():
    raise RuntimeError("absichtlich")


werk.auftrag("b", krachen)
import time as _t
for _ in range(200):
    fertig = werk.fertig()
    if len(fertig) >= 1:
        break
    _t.sleep(0.01)
gesammelt = list(fertig)
for _ in range(200):
    if len(gesammelt) >= 2:
        break
    gesammelt += werk.fertig()
    _t.sleep(0.01)
marken = {m for m, _e in gesammelt}
pruef("Ein Auftrag kommt zurueck", "a" in marken, str(marken))
pruef("Ein Auftrag, der kracht, auch - als Fehlantwort",
      any(m == "b" and not e for m, e in gesammelt), str(gesammelt))
werk.auftrag("c", lambda: ablage.gut({"x": 2}))
for _ in range(200):
    weiter = werk.fertig()
    if weiter:
        break
    _t.sleep(0.01)
pruef("Und der Faden lebt danach weiter", bool(weiter), str(weiter))
werk.schliessen()

# ══════════════════════════════════════════════════ Nichts Persoenliches
print("\n-- Was gespeichert wird --")
verboten = ("adresse", "ip", "email", "mail", "geraet", "hostname", "pfad",
            "benutzer", "uhrzeit")
schluessel = [s for s, _t, _a in K.WERTE]
pruef("Die Werteliste enthaelt nichts Persoenliches",
      not any(v in s for s in schluessel for v in verboten),
      ", ".join(schluessel[:4]) + " ...")
pruef("Jeder Wert hat eine Aufschrift und eine Art",
      all(len(e) == 3 and e[2] in ("summe", "bestes") for e in K.WERTE))
pruef("Die Schluessel kommen nicht doppelt vor",
      len(set(schluessel)) == len(schluessel))

# ══════════════════════════════════════════════════ Eine echte Runde
#
# Der Weg von Anfang bis Ende, ueber richtige Steckdosen: zwei Spieler,
# eine Runde, und danach genau **ein** Eintrag je Rechner - mit
# derselben Partiekennung. Das ist der Punkt, an dem sich entscheidet,
# ob die Zahlen zueinander passen.
print("\n-- Eine gespielte Runde, Gastgeber und Gast --")
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
import pygame
pygame.init()
pygame.display.set_mode((64, 64))

from dustfront import netz
from dustfront.core import App
from dustfront.mehrspieler import Gefecht

app_w = App("W", headless=True)
app_g = App("G", headless=True)
abl_w = ablage.LokaleAblage(ordner=frischer_ordner("runde_w"))
abl_g = ablage.LokaleAblage(ordner=frischer_ordner("runde_g"))
app_w._konto = konto_modul.Konto(ablage_=abl_w,
                                 ordner=arbeitsordner / "runde_w",
                                 mit_faden=False)
app_g._konto = konto_modul.Konto(ablage_=abl_g,
                                 ordner=arbeitsordner / "runde_g",
                                 mit_faden=False)
app_w.konto.anlegen("Wirt", "geheim12345")
app_g.konto.anlegen("Gast", "geheim12345")

wirt_n = netz.Gastgeber(53901)
w = Gefecht(app_w, "WIRT", gastgeber=wirt_n, modus="pvp",
            ende_art="abschuesse", ende_wert=1, seed=99)
g = Gefecht(app_g, "BESUCH", gast=netz.Gast("127.0.0.1:53901"))
for _ in range(60):
    w.schritt(K.FIXED_DT)
    g.schritt(K.FIXED_DT)

wk = w.kaempfer[0]
gk = w.kaempfer[g.meine_nummer]
wk.pos.update(300, 300); wk.vorher.update(wk.pos)
gk.pos.update(360, 300); gk.vorher.update(gk.pos)
gk.unverwundbar = 0.0
# Geschossen wird von der Figur des Gastes: der Gastgeber ueberschreibt
# seine eigene Eingabe in jedem Schritt selbst, ein Gast kommt dagegen
# ueber _anwenden herein - genau wie im Spiel.
gk.waffe_waehlen(gk.waffen.index("sturm"))
wk.unverwundbar = 0.0
for _ in range(int(12.0 / K.FIXED_DT)):
    if w.vorbei:
        break
    w._anwenden(gk, {"will": [0, 0], "ziel": [wk.pos.x, wk.pos.y],
                     "feuert": True})
    gk.magazin["sturm"] = 999
    wk.unverwundbar = 0.0
    w.schritt(K.FIXED_DT)
    g.schritt(K.FIXED_DT)
for _ in range(20):
    w.schritt(K.FIXED_DT)
    g.schritt(K.FIXED_DT)

pruef("Die Runde ist zu Ende", w.vorbei and g.vorbei)
pruef("Der Gastgeber hat eine Partiekennung vergeben", bool(w.partie), w.partie)
pruef("Und der Gast hat dieselbe", g.partie == w.partie,
      "%r gegen %r" % (g.partie, w.partie))
wj = app_w.konto.journal.eintraege
gj = app_g.konto.journal.eintraege
pruef("Beim Gastgeber steht genau ein Eintrag", len(wj) == 1,
      "%d Eintraege" % len(wj))
pruef("Beim Gast auch", len(gj) == 1, "%d Eintraege" % len(gj))
if wj and gj:
    pruef("Und beide unter derselben Partie",
          wj[0]["partie"] == gj[0]["partie"] == w.partie)
    pruef("Der Gast hat die Abschuesse",
          gj[0]["werte"]["abschuesse"] >= 1,
          str(gj[0]["werte"]["abschuesse"]))
    pruef("Der Gastgeber die Tode", wj[0]["werte"]["tode"] >= 1,
          str(wj[0]["werte"]["tode"]))
    pruef("Schuesse und Treffer wurden gezaehlt",
          gj[0]["werte"].get("schuesse", 0) > 0
          and gj[0]["werte"].get("treffer", 0) > 0,
          "%s Schuesse, %s Treffer" % (gj[0]["werte"].get("schuesse"),
                                       gj[0]["werte"].get("treffer")))
    pruef("Und getrennt je Waffe",
          gj[0]["waffen"].get("sturm", {}).get("schuesse", 0) > 0,
          str(gj[0]["waffen"]))
    pruef("Der Schaden auch",
          gj[0]["werte"].get("schaden", 0) > 0
          and wj[0]["werte"].get("schaden_ein", 0) > 0,
          "%s gemacht, %s eingesteckt" % (gj[0]["werte"].get("schaden"),
                                          wj[0]["werte"].get("schaden_ein")))
    pruef("Die Runde selbst zaehlt einmal",
          wj[0]["werte"]["runden"] == 1 and wj[0]["werte"]["spielzeit"] > 0,
          "%.1f s" % wj[0]["werte"]["spielzeit"])
    pruef("Jeder hat nur seine eigenen Zahlen",
          wj[0]["werte"].get("schuesse", 0) == 0,
          str(wj[0]["werte"].get("schuesse")))

# ── Loadouts im Gefecht ──────────────────────────────────────────────
print("\n-- Loadouts im Gefecht --")
app_w.konto.loadout_setzen(0, {"name": "SCHARF", "waffen": ["scharf", "schrot"],
                               "wuerfe": ["rauch"]})
app_w.konto.loadout_waehlen(0)
app_g.konto.loadout_setzen(0, {"name": "STURM", "waffen": ["sturm", "repetierer"],
                               "wuerfe": ["granate"]})
app_g.konto.loadout_waehlen(0)

wirt2 = netz.Gastgeber(53902)
w2 = Gefecht(app_w, "WIRT", gastgeber=wirt2, modus="pvp", seed=7,
             loadouts="eigenes")
g2 = Gefecht(app_g, "BESUCH", gast=netz.Gast("127.0.0.1:53902"))
for _ in range(60):
    w2.schritt(K.FIXED_DT)
    g2.schritt(K.FIXED_DT)
pruef("Der Gastgeber spielt mit Loadouts", w2.mit_loadouts)
pruef("Und der Gast erfaehrt es", g2.mit_loadouts)
pruef("Der Gastgeber traegt sein eigenes",
      w2.kaempfer[0].waffen == ["schrot", "scharf", "rauch"],
      str(w2.kaempfer[0].waffen))
gast_k2 = w2.kaempfer.get(g2.meine_nummer)
pruef("Und der Gast das, das er angemeldet hat",
      gast_k2 is not None
      and gast_k2.waffen == ["repetierer", "sturm", "granate"],
      str(gast_k2.waffen if gast_k2 else None))
pruef("Munition und Magazin gelten fuer genau diese Waffen",
      gast_k2 is not None
      and set(gast_k2.magazin) == set(gast_k2.waffen)
      and set(gast_k2.vorrat) == set(gast_k2.waffen))
pruef("Das Brecheisen bleibt ausserhalb und damit immer da",
      K.NAHKAMPF["waffe"] not in w2.kaempfer[0].waffen
      and bool(w2.kaempfer[0].nahkampf()))
w2.verlassen(); g2.verlassen()

wirt3 = netz.Gastgeber(53903)
w3 = Gefecht(app_w, "WIRT", gastgeber=wirt3, modus="pvp", seed=7)
pruef("Ohne Loadout-Regel hat jeder alles",
      w3.kaempfer[0].waffen == list(K.HOTBAR), str(w3.kaempfer[0].waffen))
w3.verlassen()

# Und nochmal: eine zweite Endmeldung darf nichts verdoppeln.
w._runde_buchen()
g._runde_buchen()
pruef("Eine zweite Endmeldung traegt nichts nach",
      len(app_w.konto.journal.eintraege) == 1
      and len(app_g.konto.journal.eintraege) == 1)
app_w.konto.abgleichen()
app_g.konto.abgleichen()
pruef("Beide Journale sind abgeglichen",
      not app_w.konto.journal.offen() and not app_g.konto.journal.offen())
w.verlassen(); g.verlassen()
app_w.konto.schliessen(); app_g.konto.schliessen()
pygame.quit()

shutil.rmtree(arbeitsordner, ignore_errors=True)
print()
print("FEHLER:", fails or "keine")
