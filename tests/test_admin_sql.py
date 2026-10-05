"""
Das SQL aus docs/KONTO.md gegen ein nachgebautes Supabase.

Gefragt war ein ADMIN-Konto, das alles sieht und alles darf, mit einer
Sperre nach Fehlversuchen. Das sitzt fast ganz im Server, in Funktionen
aus KONTO.md 5.8 - und SQL, das nur in einer Anleitung steht, prueft
sonst niemand, bis jemand es in Supabase einfuegt und es scheitert.

Darum: ein frisches PostgreSQL in einem Wegwerfordner, darin so viel
Supabase, wie das SQL braucht (die Rollen anon und authenticated, das
Schema auth mit users, identities und sessions, auth.uid()), und dann
genau die Bloecke aus KONTO.md 5.2, 5.6, 5.7 und 5.8, wie sie dort stehen.

Ohne PostgreSQL auf dem Rechner wird der Test uebersprungen, nicht
bestanden - er sagt es.

    python tests/test_admin_sql.py
"""

import glob
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

WURZEL = Path(__file__).resolve().parent.parent
fails = []


def pruef(text, bedingung, zusatz=""):
    if bedingung:
        print("  ok  " + text + (("   " + str(zusatz)) if zusatz else ""))
    else:
        print("FAIL  " + text + (("   " + str(zusatz)) if zusatz else ""))
        fails.append(text)


# ── Ein PostgreSQL zum Wegwerfen ───────────────────────────────────────
def postgres_finden():
    for ordner in sorted(glob.glob("/usr/lib/postgresql/*/bin"), reverse=True):
        if os.path.exists(os.path.join(ordner, "initdb")):
            return ordner
    pfad = shutil.which("initdb")
    return os.path.dirname(pfad) if pfad else ""


BIN = postgres_finden()
if not BIN or not shutil.which("psql"):
    print("UEBERSPRUNGEN: kein PostgreSQL auf diesem Rechner (initdb und psql).")
    print("FEHLER: keine")
    sys.exit(0)

# PostgreSQL laeuft nicht als root. Ist man root, laeuft es als postgres.
ALS = []
if os.geteuid() == 0:
    import pwd
    try:
        pwd.getpwnam("postgres")
        ALS = ["runuser", "-u", "postgres", "--"]
    except KeyError:
        print("UEBERSPRUNGEN: als root, aber ohne Benutzer postgres.")
        print("FEHLER: keine")
        sys.exit(0)

ORDNER = tempfile.mkdtemp(prefix="dustfront_pg_")
os.chmod(ORDNER, 0o777)
DATEN = os.path.join(ORDNER, "daten")
PORT = 55000 + os.getpid() % 900


def lauf(befehl, **kw):
    return subprocess.run(ALS + befehl, capture_output=True, text=True, **kw)


r = lauf([BIN + "/initdb", "-D", DATEN, "-A", "trust", "-U", "postgres"])
if r.returncode:
    print("UEBERSPRUNGEN: initdb ging nicht:", r.stderr[-300:])
    print("FEHLER: keine")
    sys.exit(0)
r = lauf([BIN + "/pg_ctl", "-D", DATEN, "-w", "-l", os.path.join(ORDNER, "log"),
          "-o", "-p %d -k %s -c listen_addresses=" % (PORT, ORDNER), "start"])
if r.returncode:
    print("UEBERSPRUNGEN: PostgreSQL startet nicht:", r.stderr[-300:])
    print("FEHLER: keine")
    sys.exit(0)


def sql(text, rolle="", wer="", fehler_ok=False):
    """Fuehrt SQL aus. rolle: 'anon' oder 'authenticated', wer: auth.uid()."""
    vorne = ""
    if wer:
        vorne += "set request.jwt.claim.sub = '%s';\n" % wer
    if rolle:
        vorne += "set role %s;\n" % rolle
    r = subprocess.run(["psql", "-h", ORDNER, "-p", str(PORT), "-U", "postgres",
                        "-d", "postgres", "-At", "-q", "-v", "ON_ERROR_STOP=1"],
                       input=vorne + text, capture_output=True, text=True)
    if r.returncode and not fehler_ok:
        raise RuntimeError(r.stderr.strip()[-500:])
    return (r.stdout.strip(), r.stderr.strip()) if fehler_ok else r.stdout.strip()


def rpc(name, *argumente, rolle="anon"):
    """Eine Funktion so, wie die Kontoseite sie ruft: als anon, Antwort JSON."""
    teile = []
    for a in argumente:
        if a is None:
            teile.append("null")
        elif isinstance(a, (dict, list)):
            teile.append("'%s'::jsonb" % json.dumps(a).replace("'", "''"))
        elif isinstance(a, int):
            teile.append(str(a))
        else:
            teile.append("'%s'" % str(a).replace("'", "''"))
    return json.loads(sql("select public.%s(%s);" % (name, ", ".join(teile)), rolle=rolle))


def bloecke(abschnitt):
    """Alle ```sql-Bloecke eines Abschnitts von KONTO.md, wie sie dort stehen."""
    text = (WURZEL / "docs" / "KONTO.md").read_text(encoding="utf-8")
    start = text.index("### %s " % abschnitt)
    ende = text.find("\n### ", start + 5)
    ende2 = text.find("\n## ", start + 5)
    ende = min(e for e in (ende, ende2, len(text)) if e > 0)
    return re.findall(r"```sql\n(.*?)```", text[start:ende], re.S)


try:
    # ── So viel Supabase, wie das SQL braucht ─────────────────────────
    sql("""
    create role anon nologin;
    create role authenticated nologin;
    create schema auth;
    create schema extensions;
    grant usage on schema public, extensions to anon, authenticated;
    create table auth.users (
      id uuid primary key default gen_random_uuid(),
      email text unique, encrypted_password text,
      raw_user_meta_data jsonb default '{}'::jsonb,
      created_at timestamptz default now(), updated_at timestamptz default now());
    create table auth.identities (
      id uuid primary key default gen_random_uuid(),
      user_id uuid references auth.users(id) on delete cascade,
      provider text, provider_id text, identity_data jsonb);
    create table auth.sessions (
      id uuid primary key default gen_random_uuid(),
      user_id uuid references auth.users(id) on delete cascade);
    create function auth.uid() returns uuid language sql stable as $$
      select nullif(current_setting('request.jwt.claim.sub', true), '')::uuid $$;
    -- Wie in Supabase: was in public angelegt wird, duerfen anon und
    -- authenticated erst einmal benutzen. Der Zeilenschutz regelt den Rest.
    alter default privileges in schema public grant all on tables to anon, authenticated;
    alter default privileges in schema public grant execute on functions to anon, authenticated;
    """)
    print("-- Das SQL aus KONTO.md --")
    for abschnitt in ("5.2", "5.6", "5.7", "5.8"):
        b = bloecke(abschnitt)
        pruef("KONTO.md %s hat einen SQL-Block" % abschnitt, len(b) >= 1, len(b))
        for block in b:
            try:
                sql(block)
                pruef("KONTO.md %s laeuft durch" % abschnitt, True)
            except RuntimeError as fehler:
                pruef("KONTO.md %s laeuft durch" % abschnitt, False, fehler)
    for abschnitt in ("5.7", "5.8"):
        try:
            for block in bloecke(abschnitt):
                sql(block)
            pruef("KONTO.md %s ein zweites Mal: kein Fehler" % abschnitt, True)
        except RuntimeError as fehler:
            pruef("KONTO.md %s ein zweites Mal: kein Fehler" % abschnitt, False, fehler)

    def konto_anlegen(name, wort="geheim12345"):
        kennung = sql("""
          insert into auth.users (email, encrypted_password, raw_user_meta_data)
          values ('%s@spieler.dustfront', extensions.crypt('%s', extensions.gen_salt('bf')),
                  '{"name": "%s"}') returning id;""" % (name.lower(), wort, name))
        sql("""insert into auth.identities (user_id, provider, provider_id, identity_data)
               values ('%s', 'email', '%s', '{"email": "%s@spieler.dustfront"}');
               insert into auth.sessions (user_id) values ('%s');"""
            % (kennung, kennung, name.lower(), kennung))
        return kennung

    a = konto_anlegen("Erster")
    b = konto_anlegen("Zweiter")
    for nr, (wer, modus, ende) in enumerate([(a, "pvp", "regulaer"), (a, "pve", "abgebrochen"),
                                             (b, "pvp", "regulaer")]):
        sql("""insert into gefecht (partie, konto, gespielt, modus, werte, version, ende)
               values ('p%d', '%s', %d, '%s', '{"abschuesse": %d}', '0.31.0', '%s');"""
            % (nr, wer, 1000 + nr, modus, nr + 1, ende))

    print("\n-- 5.7: Version, Ende, Opfer --")
    pruef("Die neuen Spalten haben ihre Vorgaben",
          sql("select version || '|' || ende || '|' || opfer::text from gefecht "
              "where partie = 'p0' and konto = '%s'" % a) == "0.31.0|regulaer|[]")
    _, f = sql("insert into gefecht (partie, konto, gespielt, modus, ende) "
               "values ('x', '%s', 1, 'pvp', 'quatsch');" % a, fehler_ok=True)
    pruef("Ein drittes Ende gibt es nicht", "gefecht_ende" in f, f[-80:])
    alt = sql("insert into gefecht (partie, konto, gespielt, modus) "
              "values ('alt', '%s', 1, 'pvp') returning version || '|' || ende;" % a)
    pruef("Eine Zeile ohne die neuen Felder (altes Spiel) geht weiter", alt == "|regulaer", alt)
    sql("delete from gefecht where partie = 'alt';")

    print("\n-- 5.8: Anmelden und das erste Kennwort --")
    p = rpc("admin_anmelden", "123")
    pruef("Mit 123 geht es beim ersten Mal", p.get("ok") is True, p)
    pruef("... und es muss sofort geaendert werden", p.get("muss_aendern") is True, p)
    p = rpc("admin_konten", "123")
    pruef("Vorher geht nichts anderes", not p["ok"] and "KENNWORT AENDERN" in p["fehler"], p)
    p = rpc("admin_wort_aendern", "123", "kurz")
    pruef("Zu kurz geht nicht", not p["ok"] and "ZU KURZ" in p["fehler"], p)
    p = rpc("admin_wort_aendern", "123", "123")
    pruef("Das alte auch nicht", not p["ok"], p)
    p = rpc("admin_wort_aendern", "123", "Meisterwort1")
    pruef("Ein richtiges neues schon", p.get("ok") is True, p)
    pruef("Danach gilt 123 nicht mehr", rpc("admin_anmelden", "123")["fehler"] == "FALSCH")
    p = rpc("admin_anmelden", "Meisterwort1")
    pruef("Das neue gilt, ohne Zwang zum Aendern",
          p.get("ok") is True and p.get("muss_aendern") is False, p)
    for block in bloecke("5.8"):
        sql(block)
    pruef("Das SQL noch einmal ausgefuehrt setzt das Kennwort NICHT zurueck",
          rpc("admin_anmelden", "Meisterwort1").get("ok") is True)
    W = "Meisterwort1"

    print("\n-- Niemand sonst kommt heran --")
    _, f = sql("select * from admin_zugang;", rolle="anon", fehler_ok=True)
    pruef("anon liest die Tabelle nicht", "permission denied" in f, f[-60:])
    _, f = sql("select * from admin_zugang;", rolle="authenticated", wer=a, fehler_ok=True)
    pruef("Ein angemeldeter Spieler auch nicht", "permission denied" in f, f[-60:])
    _, f = sql("update admin_zugang set fehlversuche = 0;", rolle="authenticated", wer=a,
               fehler_ok=True)
    pruef("... und setzt die Sperre nicht zurueck", "permission denied" in f, f[-60:])
    for innen in ("admin_pruefen('x')", "admin_darf('x')", "admin_sperre_minuten(3)"):
        _, f = sql("select public.%s;" % innen, rolle="anon", fehler_ok=True)
        pruef("Die innere Funktion %s ist von aussen nicht zu rufen" % innen.split("(")[0],
              "permission denied" in f, f[-60:])
    sichtbar = sql("select count(*) from gefecht;", rolle="authenticated", wer=b)
    pruef("Der Zeilenschutz der Spieler gilt weiter", sichtbar == "1", sichtbar)

    print("\n-- Die Sperre: 1, 5, 15, 30 Minuten, dann doppelt --")

    def sperre_aus():
        sql("update admin_zugang set gesperrt_bis = now() - interval '1 second';")

    erwartet = [0, 0, 1, 5, 15, 30, 60, 120, 240]
    gesehen = []
    for i, minuten in enumerate(erwartet):
        p = rpc("admin_anmelden", "falsch")
        gesehen.append(int(float(p.get("sekunden", -60))) // 60)
        if i == 1:
            pruef("Nach zwei Fehlversuchen: noch frei, keine Versuche mehr ohne Sperre",
                  p.get("frei") == 0 and float(p.get("sekunden")) == 0, p)
        if i == 2:
            g = rpc("admin_anmelden", W)
            pruef("Gesperrt hilft auch das richtige Kennwort nicht",
                  g.get("fehler") == "GESPERRT" and 0 < g.get("sekunden") <= 60, g)
            vorher = sql("select fehlversuche from admin_zugang;")
            rpc("admin_anmelden", "falsch")
            pruef("... und ein Versuch in der Sperre zaehlt nicht",
                  sql("select fehlversuche from admin_zugang;") == vorher)
            rpc("admin_loeschen", W, a)
            pruef("Auch keine andere Funktion geht in der Sperre",
                  sql("select count(*) from auth.users where id = '%s';" % a) == "1")
        sperre_aus()
    pruef("Die Sperren in Minuten", gesehen == erwartet, gesehen)
    pruef("Und die Verdopplung laeuft nicht ueber den Kalender hinaus",
          float(sql("select public.admin_sperre_minuten(10000);")) == 30 * 2 ** 20)
    p = rpc("admin_anmelden", W)
    pruef("Nach der Sperre geht das richtige Kennwort", p.get("ok") is True, p)
    pruef("... und setzt alles zurueck",
          sql("select fehlversuche || '|' || coalesce(gesperrt_bis::text, '-') "
              "from admin_zugang;") == "0|-")
    rpc("admin_anmelden", "falsch")
    rpc("admin_anmelden", W)
    rpc("admin_anmelden", "falsch")
    rpc("admin_anmelden", "falsch")
    pruef("Gezaehlt wird nach dem letzten richtigen neu: zwei frei",
          sql("select gesperrt_bis is null from admin_zugang;") == "t")
    rpc("admin_anmelden", W)

    print("\n-- Lesen --")
    p = rpc("admin_konten", W)
    namen = {k["anmeldename"]: k for k in p.get("konten", [])}
    pruef("Alle Konten, mit Name und Rundenzahl",
          set(namen) == {"erster", "zweiter"} and namen["erster"]["runden"] == 2
          and namen["zweiter"]["runden"] == 1, p)
    p = rpc("admin_gefechte", W, None, 0, 1000)
    pruef("Die Runden aller, neueste zuerst",
          [g["partie"] for g in p["gefechte"]] == ["p2", "p1", "p0"], p)
    pruef("Mit Version und Ende", p["gefechte"][1]["ende"] == "abgebrochen"
          and p["gefechte"][1]["version"] == "0.31.0")
    p = rpc("admin_gefechte", W, a, 0, 1000)
    pruef("Oder die eines Kontos", [g["partie"] for g in p["gefechte"]] == ["p1", "p0"], p)
    p = rpc("admin_gefechte", W, None, 1, 1)
    pruef("Seitenweise", [g["partie"] for g in p["gefechte"]] == ["p1"], p)
    p = rpc("admin_gefechte", "falsch", None, 0, 1000)
    pruef("Mit falschem Kennwort nichts", not p["ok"] and "gefechte" not in p, p)
    rpc("admin_anmelden", W)

    print("\n-- Profil, Loadouts, Kosmetik eines anderen --")
    p = rpc("admin_profil", W, a)
    pruef("Das Profil eines anderen lesen", p.get("ok") and p["profil"]["name"] == "Erster", p)
    fassung = p["profil"]["fassung"]
    lo = [{"name": "VOM ADMIN", "waffen": ["scharf", "schrot"], "wuerfe": ["granate"]}]
    p = rpc("admin_profil_schreiben", W, a, fassung, "", {"bildschirm_ruckeln": 10}, lo)
    pruef("Und schreiben - die Fassung zaehlt hoch, damit das Spiel es sieht",
          p.get("ok") and p["profil"]["fassung"] == fassung + 1
          and p["profil"]["loadouts"] == lo and p["profil"]["name"] == "Erster", p)
    p = rpc("admin_profil_schreiben", W, a, fassung, "", {}, [])
    pruef("Mit veralteter Fassung nicht",
          not p["ok"] and "ZWISCHENDURCH" in p["fehler"], p)
    pruef("Der Spieler sieht die neuen Loadouts",
          "VOM ADMIN" in sql("select loadouts::text from profil;", rolle="authenticated", wer=a))
    p = rpc("admin_kosmetik_schreiben", W, a, "VE9O", "QklMRA==", "TVVTSUM=")
    pruef("Kosmetik eines anderen setzen", p.get("ok") is True, p)
    p = rpc("admin_kosmetik", W, a)
    pruef("... Ton, Bild und Music Kit lesen", p.get("ton") == "VE9O"
          and p.get("bild") == "QklMRA==" and p.get("music_kit") == "TVVTSUM=", p)
    p = rpc("admin_kosmetik_schreiben", W, a, "x" * 540001, "", "")
    pruef("Zu gross wird abgelehnt, nicht abgeschnitten",
          not p["ok"] and "ZU GROSS" in p["fehler"]
          and rpc("admin_kosmetik", W, a)["ton"] == "VE9O", p.get("fehler"))
    rpc("admin_kosmetik_schreiben", W, a, "", "", "")
    pruef("Beides leer: die Zeile ist weg",
          sql("select count(*) from kosmetik;") == "0")

    print("\n-- Namen und Kennwoerter --")
    for falsch, grund in (("ab", "3 BIS 24"), ("-xy", "3 BIS 24"), ("mit leer", "3 BIS 24"),
                          ("Admin", "VORBEHALTEN"), ("ZWEITER", "VERGEBEN")):
        p = rpc("admin_name_aendern", W, a, falsch)
        pruef("Name '%s' geht nicht" % falsch, not p["ok"] and grund in p["fehler"], p)
    p = rpc("admin_name_aendern", W, a, "Neuname")
    pruef("Umbenennen", p.get("ok") is True and p.get("anmeldename") == "neuname", p)
    zeile = sql("""select u.email || '|' || (u.raw_user_meta_data->>'name') || '|' ||
                   (i.identity_data->>'email') || '|' || p.name
                   from auth.users u join auth.identities i on i.user_id = u.id
                   join profil p on p.konto = u.id where u.id = '%s';""" % a)
    pruef("Adresse, Metadaten, Identitaet und Profil wechseln zusammen",
          zeile == "neuname@spieler.dustfront|Neuname|neuname@spieler.dustfront|Neuname", zeile)
    p = rpc("admin_kennwort_setzen", W, b, "kurz")
    pruef("Ein zu kurzes Kennwort setzt er nicht", not p["ok"], p)
    p = rpc("admin_kennwort_setzen", W, b, "Neueswort99")
    pruef("Ein neues Kennwort setzen", p.get("ok") is True, p)
    pruef("Es passt zum Hash, wie ihn der Anmeldedienst prueft",
          sql("select encrypted_password = extensions.crypt('Neueswort99', encrypted_password) "
              "from auth.users where id = '%s';" % b) == "t")
    pruef("Und alle Anmeldungen des Kontos sind beendet",
          sql("select count(*) from auth.sessions where user_id = '%s';" % b) == "0")

    print("\n-- Den Namen ADMIN bekommt kein Spieler --")
    _, f = sql("insert into auth.users (email) values ('admin@spieler.dustfront');",
               fehler_ok=True)
    pruef("Ein Konto 'admin' laesst der Server nicht anlegen", "VORBEHALTEN" in f, f[-60:])

    print("\n-- Loeschen --")
    rpc("admin_kosmetik_schreiben", W, b, "VE9O", "", "")
    p = rpc("admin_loeschen", "falsch", b)
    pruef("Mit falschem Kennwort wird nichts geloescht",
          not p["ok"] and sql("select count(*) from auth.users where id = '%s';" % b) == "1")
    rpc("admin_anmelden", W)
    p = rpc("admin_loeschen", W, b)
    pruef("Loeschen", p.get("ok") is True, p)
    reste = sql("""select (select count(*) from auth.users where id = '{0}') +
                          (select count(*) from profil where konto = '{0}') +
                          (select count(*) from gefecht where konto = '{0}') +
                          (select count(*) from kosmetik where konto = '{0}');""".format(b))
    pruef("Konto, Profil, Runden und Kosmetik sind weg", reste == "0", reste)
    p = rpc("admin_loeschen", W, b)
    pruef("Ein zweites Mal: nicht gefunden, kein Fehler",
          not p["ok"] and "NICHT GEFUNDEN" in p["fehler"], p)
    pruef("Das andere Konto bleibt",
          sql("select count(*) from gefecht where konto = '%s';" % a) == "2")
finally:
    lauf([BIN + "/pg_ctl", "-D", DATEN, "-m", "immediate", "stop"])
    time.sleep(0.2)
    shutil.rmtree(ORDNER, ignore_errors=True)

print()
print("FEHLER:", fails or "keine")
sys.exit(1 if fails else 0)
