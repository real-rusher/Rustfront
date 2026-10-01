# DUSTFRONT - Konto, Statistik und Loadouts

Dieses Dokument beantwortet drei Fragen: **wo die Zahlen liegen**, **warum
dort** und **wie man es in zehn Minuten aufsetzt**. Wer nur spielen will,
muss nichts davon lesen - ohne eingerichteten Server laeuft alles lokal
weiter, und kein einziger Aufruf im Spiel merkt den Unterschied.

---

## 1. Die Anforderung

Woertlich gestellt waren drei Dinge:

1. **Alle harmlosen Spielwerte** sollen in einer eigenen, kostenlosen
   Datenbank mitlaufen.
2. Auf einem **neuen Geraet** soll eine **einfache Anmeldung** reichen -
   direkt nachdem man die Dateien heruntergeladen hat.
3. Es soll **nie** Abweichungen oder Fehler in den Zahlen geben, und
   spaeter genauso wenig bei der Anpassung (Skins, Loadouts).

Punkt 2 und Punkt 3 sind die schwierigen. Punkt 2 schliesst alles aus,
was einen Schluessel braucht, den der Spieler irgendwo abschreiben muss.
Punkt 3 schliesst aus, dass man einfach "die Zahlen hochschickt" - ein
Netz ist nicht zuverlaessig, und eine Antwort, die ausbleibt, sagt einem
nicht, ob geschrieben wurde.

---

## 2. Warum Supabase

Verglichen wurden vier Wege:

| Weg | Warum nicht / warum doch |
|---|---|
| **Google Drive** | Ausdruecklich ausgeschlossen. Waere auch kein guter Weg: eine Tabelle ist keine Datenbank, und die Anmeldung braucht ein Google-Konto. |
| **Firebase** | Kann es, braucht aber ein SDK und ein Google-Konto. Dasselbe Problem wie oben, nur eleganter verpackt. |
| **Eigener Server** (PocketBase, Flask) | Technisch am schoensten, scheitert an Punkt 2: irgendwo muss dann dauernd ein Rechner laufen, und der kostet Geld oder steht im Kinderzimmer. |
| **Supabase** | **Gewaehlt.** |

Vier Gruende, in der Reihenfolge ihres Gewichts:

1. **Es spricht nur HTTPS und JSON.** Kein SDK, kein `pip install`,
   keine Abhaengigkeit. `urllib.request` aus der Standardbibliothek
   reicht, genau wie schon bei der Portfreigabe in `upnp.py`. Wer das
   Spiel herunterlaedt, hat alles, was er braucht - das ist Punkt 2,
   direkt erfuellt.
2. **Der oeffentliche Schluessel darf oeffentlich sein.** Der
    *publishable key*
   ist dafuer gemacht, im Klienten zu stehen; er liegt deshalb mit im
   Quelltext. Niemand muss irgendwo etwas eintragen, damit die Anmeldung
   auf einem neuen Rechner geht.
3. **Kennwoerter fasst das Spiel nie an.** Sie gehen einmal ueber TLS an
   den Anmeldedienst und werden dort mit bcrypt gehasht. Es liegt kein
   Klartextkennwort im Spiel, und es koennte auch keines dort liegen.
4. **Zeilenschutz (Row Level Security).** Der mitgelieferte Schluessel
   kommt an fremde Zeilen nicht heran, und zwar weil der *Server* das
   entscheidet. Ein veraenderter Klient nuetzt nichts.

Dazu: der kostenlose Tarif gibt 500 MB Datenbank und 50 000 Anmeldungen
im Monat. Eine Runde belegt etwa 300 Byte. Das reicht fuer rund anderthalb
Millionen Runden - bei fuenf Runden am Tag waere die Grenze in etwa
achthundert Jahren erreicht.

**Und wenn Supabase eines Tages zumacht?** Dann wird `NetzAblage` in
`ablage.py` gegen eine andere getauscht. Das Spiel kennt nur die
Schnittstelle (`anmelden`, `profil_lesen`, `gefechte_senden`, ...); es
gibt keine Stelle ausserhalb von `ablage.py`, die weiss, wer da antwortet.

---

## 3. Warum nichts durcheinandergeraet

Das ist der wichtigere Teil. Drei Regeln, alle drei in der Ablage und
keine davon im Spielcode.

### 3.1 Der Gastgeber vergibt die Partiekennung

Am Rundenende wuerfelt **nur der Gastgeber** eine Kennung fuer die Partie
und schickt sie mit dem Endstand an alle. Jeder Rechner traegt dieselbe
Runde unter derselben Kennung ein.

Genauso kommen auch die Zahlen vom Gastgeber: er ist der einzige, der die
Welt rechnet, also der einzige, der sie kennen kann. Ein Gast bekommt
seine eigenen zugeschickt. Damit kann niemand seine Statistik erfinden,
und zwei Rechner koennen fuer dieselbe Runde keine zwei verschiedenen
Zahlen ablegen.

### 3.2 Zweimal schicken heisst einmal speichern

Die Tabelle hat einen **eindeutigen Index auf (Partie, Konto)**, und
geschrieben wird mit `Prefer: resolution=ignore-duplicates`. Dieselbe
Runde ein zweites Mal zu schicken aendert nichts.

Das ist die Antwort auf den einen Fall, an dem alle naiven Loesungen
scheitern: der Server schreibt, und **dann** faellt die Leitung aus. Der
Klient weiss jetzt nicht, ob es angekommen ist. Schickt er nicht nochmal,
fehlt die Runde. Schickt er nochmal, zaehlt sie doppelt - ausser der
Server laesst sie nicht doppelt zu. Genau dieser Fall wird in
`tests/test_konto.py` nachgestellt (`FalscherServer.aussetzen`).

### 3.3 Erst ins Journal, dann ins Netz

Am Rundenende landet das Ergebnis sofort in `journal.json` im
Benutzerordner. Ab da kann es nicht mehr verloren gehen. Der Abgleich ist
ein eigener, spaeterer Schritt:

```
Runde endet ──▶ Journal (offen) ──▶ Abgleich ──▶ Server
                     ▲                   │
                     └─ Bestaetigung ────┘  erst dann abgehakt
```

Bleibt die Bestaetigung aus, bleibt der Eintrag offen und geht beim
naechsten Mal wieder mit. Das darf beliebig oft passieren, siehe 3.2.

**Die Anzeige rechnet immer aus dem Journal**, nie aus einer Antwort des
Servers. Man schiesst jemanden ab und sieht es sofort, auch im Zug ohne
Netz.

### 3.4 Das Profil zaehlt seine Fassungen

Loadouts und Einstellungen liegen in einer Zeile mit einem Zaehler. Wer
speichert, schickt die Fassung mit, die er gelesen hat; der Server
schreibt nur, wenn sie noch stimmt (`?fassung=eq.<gelesen>`). Passt sie
nicht mehr, kommt nichts zurueck, der Klient liest neu und fuehrt
zusammen.

Damit kann ein zweiter Rechner die Loadouts nicht still ueberschreiben -
das ist der Fehler, den man sonst erst merkt, wenn ein Satz weg ist.
Dieselbe Mechanik traegt spaeter die Skins.

---

## 4. Was gespeichert wird

Die Liste steht an genau einer Stelle: `WERTE` in `config.py`. Was dort
nicht steht, wird nicht gespeichert.

**Nur harmlose Zahlen.** Alles darin entsteht im Spiel und sagt nichts
ueber den Menschen davor: keine Adressen, keine Geraete, keine Zeiten, an
denen jemand am Rechner sass. Ein selbstgewaehlter Name und das, was die
Figur getan hat. `tests/test_konto.py` prueft das nach.

Abschuesse, Tode, Aufgeholfen, Schaden, Eingesteckt, Schuesse, Treffer,
Nahkampftreffer, Granaten, Rauchwolken, Medkits, Aufgesammelt, Gelaufen,
Stuerze, Zeit im Kreis, Runden, Siege, Spielzeit, beste Abschussfolge,
beste Runde - und dasselbe getrennt je Waffe (Schuesse, Treffer,
Abschuesse), damit sich sagen laesst, womit jemand wirklich spielt.

Seit 0.31 dazu: Zombie- und Bossabschuesse, Treffer auf Spieler und auf
Zombies, Schuesse und Treffer getrennt nach PVP und PVE, die Zahl der
abgebrochenen Runden - und je Runde die Version, ob sie regulaer endete,
und wen man darin wie oft erledigt hat (Name und Kontokennung des
Gegners, die einzige Zeile, in der ein anderes Konto vorkommt; siehe 5.7).

**Keine Adresse.** Supabase will fuer ein Konto eine E-Mail-Adresse.
Angemeldet wird deshalb mit `<name>@spieler.dustfront`, einer Domaene,
die es nicht gibt und nie geben wird. Eine echte Adresse wird nicht
abgefragt: sie waere fuer ein Schulprojekt eine Menge personenbezogener
Daten, die niemand braucht.

---

## 5. Aufsetzen

Zehn Minuten, einmalig.

### 5.1 Projekt anlegen

1. Auf <https://supabase.com> anmelden. In der Organisation **New
   project**.
2. Name egal, Region moeglichst nah (Frankfurt), Datenbankkennwort
   notieren. Es wird hier nie gebraucht, aber Supabase fragt danach und
   zeigt es spaeter nicht wieder.
3. Warten, bis es steht - das dauert ein paar Minuten.

### 5.2 Tabellen anlegen

Im **SQL Editor** einfuegen und ausfuehren:

```sql
-- ── Profil: eine Zeile je Konto ────────────────────────────────────
create table if not exists profil (
  konto      uuid primary key references auth.users(id) on delete cascade,
  name       text not null,
  fassung    bigint not null default 0,
  werte      jsonb  not null default '{}'::jsonb,
  loadouts   jsonb  not null default '[]'::jsonb,
  geaendert  timestamptz not null default now()
);

-- ── Gefecht: eine Zeile je Runde und Spieler ───────────────────────
create table if not exists gefecht (
  partie     text not null,
  konto      uuid not null references auth.users(id) on delete cascade,
  gespielt   bigint not null,
  modus      text  not null,
  team       int,
  gewonnen   boolean,
  gastgeber  boolean,
  werte      jsonb not null default '{}'::jsonb,
  waffen     jsonb not null default '{}'::jsonb,
  -- DAS hier ist die Absicherung gegen doppeltes Zaehlen. Ohne sie
  -- zaehlt jeder Wiederholungsversuch nach einem Netzaussetzer noch
  -- einmal, und die Zahlen laufen auseinander.
  primary key (partie, konto)
);

-- ── Zeilenschutz: jeder sieht und schreibt nur das Eigene ──────────
alter table profil  enable row level security;
alter table gefecht enable row level security;

create policy "eigenes profil lesen"     on profil  for select using (auth.uid() = konto);
create policy "eigenes profil anlegen"   on profil  for insert with check (auth.uid() = konto);
create policy "eigenes profil aendern"   on profil  for update using (auth.uid() = konto)
                                                    with check (auth.uid() = konto);
create policy "eigene gefechte lesen"    on gefecht for select using (auth.uid() = konto);
create policy "eigene gefechte anlegen"  on gefecht for insert with check (auth.uid() = konto);
-- Absichtlich kein update und kein delete auf gefecht: eine gespielte
-- Runde wird nicht mehr veraendert. Damit kann auch ein veraenderter
-- Klient seine Zahlen nicht nachbessern.

-- Beim Anlegen eines Kontos gleich ein Profil dazu.
--
-- Die beiden Kleinigkeiten in der ersten Zeile sind keine: ohne
-- `set search_path` laeuft die Funktion mit dem Suchpfad des
-- Anmeldedienstes, und der kennt `public` nicht - dann findet sie
-- `profil` nicht, das Anlegen bricht ab, und der Dienst meldet nur
-- "Database error saving new user". Darum der leere Suchpfad und
-- ueberall der volle Name `public.profil`.
create or replace function public.neues_profil() returns trigger
language plpgsql security definer set search_path = '' as $$
begin
  insert into public.profil (konto, name)
  values (new.id, coalesce(new.raw_user_meta_data->>'name', 'SPIELER'))
  on conflict (konto) do nothing;
  return new;
end $$;

drop trigger if exists profil_anlegen on auth.users;
create trigger profil_anlegen after insert on auth.users
  for each row execute function public.neues_profil();
```

### 5.3 Bestaetigung per Post ausschalten

Der direkte Weg, an der Oberflaeche vorbei:

    https://supabase.com/dashboard/project/_/auth/providers

Das `_` ersetzt Supabase selbst durch das Projekt. Ueber das Menue:
**Authentication**, dort die Seite mit den Anmeldearten - je nach Stand
der Oberflaeche heisst sie *Providers* oder *Sign In / Providers*, die
Adresse ist dieselbe. Dort **Email** aufklappen und den Schalter fuer
das Bestaetigen der Adresse ausschalten (*Confirm email*; in der
Konfiguration heisst er `enable_confirmations`). Speichern nicht
vergessen.

**Warum das sein muss:** bei einem gehosteten Projekt steht die
Bestaetigung von Haus aus an. Das Spiel meldet sich aber mit einer
Adresse an, die es nicht gibt (`<name>@spieler.dustfront`, siehe 5.4) -
die Bestaetigung kaeme also nie an, und niemand kaeme je hinein.

**Woran man merkt, dass es noch ansteht:** der Anmeldedienst legt das
Konto an, gibt aber keine Sitzung zurueck. Das Spiel sagt dann

    KONTO ANGELEGT, ABER NOCH NICHT BESTAETIGT

und `--konto server` (5.5) faellt beim ersten Schritt durch und nennt
genau diese Stelle. Das ist der Punkt, an dem es am haeufigsten haengt.

### 5.4 Zugang eintragen

**Settings → API Keys**. Dort stehen zwei Sorten Schluessel, und es ist
wichtig, die richtige zu nehmen:

| Schluessel | Nehmen? |
|---|---|
| *publishable key*, faengt mit `sb_publishable_` an | **Ja.** Er ist dafuer gemacht, im Klienten zu stehen. |
| *secret key*, faengt mit `sb_secret_` an | **Nein, niemals.** Er haengt den Zeilenschutz aus. Wer ihn ins Repository legt, hat die Datenbank verschenkt. |
| *anon* / *service_role* (alte Namen, fangen mit `eyJ` an) | Gehen noch, laufen aber Ende 2026 aus. Fuer ein neues Projekt der falsche Weg. |

Die *Project URL* steht unter **Settings → API** (oder im **Connect**-
Dialog oben). Beides in `dustfront/ablage.py` oben in `SERVER` eintragen:

```python
SERVER = {
    "url": "https://abcdefghijkl.supabase.co",
    "schluessel": "sb_publishable_...",
    "postfach": "spieler.dustfront",
}
```

URL und publishable key duerfen im Quelltext stehen und ins Repository -
genau darum geht die Anmeldung auf einem frisch heruntergeladenen Spiel
sofort. Das ist keine Nachlaessigkeit, sondern die Bedingung, unter der
das Ganze ueberhaupt gebaut wurde.

`postfach` ist die Domaene, hinter der die Spielernamen als Adresse
laufen (`MEISTER` wird zu `meister@spieler.dustfront`). Sie existiert
nicht und soll nicht existieren. Falls der Anmeldedienst die erfundene
Endung ablehnt, wird hier eine andere eingetragen - das ist dann eine
Zeile. **Vorher entscheiden:** wer die Domaene aendert, nachdem sich
Leute angemeldet haben, hat danach andere Konten.

Wer ein eigenes Projekt benutzen will, ohne den Quelltext zu aendern,
legt stattdessen `server.json` in den Benutzerordner (siehe `pfade.py`):

```json
{"url": "https://...", "schluessel": "sb_publishable_..."}
```

Diese Datei gilt vor `SERVER`.

### 5.5 Nachsehen, ob es geht

```
python -m dustfront --konto server
```

Das ist die Abnahme. Es wird nicht angepingt, sondern der ganze Weg
gegangen, den ein Spieler auch geht:

```
  ok    Konto anlegen   PRUEF3f2a91c
  ok    Anmelden
  ok    Profil lesen   Fassung 0
  ok    Profil schreiben   Fassung 1
  ok    Runde buchen   selbsttest-1a0f1fbd4
  ok    Dieselbe Runde noch einmal buchen
  ok    Eine Runde auf fremden Namen wird abgelehnt
  ok    Runden zurueklesen
  ok    Sie steht genau einmal da   1x
  ok    Ohne Anmeldung ist nichts zu sehen   nichts

Alle 10 Schritte in Ordnung. Der Server traegt.
```

Die letzten vier Schritte sind die, um die es eigentlich geht:

* **Genau einmal.** Steht dort `2x`, fehlt der eindeutige Index aus 5.2 -
  und dann zaehlt spaeter jeder Netzaussetzer eine Runde doppelt, ohne
  dass es jemandem auffaellt.
* **Fremder Name.** Geschrieben wird eine Runde auf ein anderes Konto,
  also das, was ein veraenderter Klient versuchen wuerde. Der Server
  muss sie ablehnen, nicht das Spiel.
* **Ohne Anmeldung.** Gelesen wird mit dem oeffentlichen Schluessel
  allein. So weit kommt jeder, der das Spiel herunterlaedt - kommt dabei
  auch nur eine Zeile zurueck, kann jeder alle Zahlen aller Spieler
  lesen.

Schlaegt ein Schritt fehl, nennt der Selbsttest den wahrscheinlichen
Grund und die Stelle in der Oberflaeche. Er legt dabei ein Wegwerfkonto
mit gewuerfeltem Namen an, das stehenbleibt.

`python -m dustfront --konto liste` zeigt nur, **ob** ein Server
eingetragen ist, nicht ob er geht.

---

## 5a. Die Kontoseite

`KONTO.html` im Wurzelverzeichnis. Doppelklicken, anmelden, fertig - kein
Server, keine Installation, kein Internet ausser dem zu Supabase.

### Was sie kann

| Reiter | Inhalt |
|---|---|
| **UEBERSICHT** | Die Zahlen, die man wirklich anschaut, dazu Verhaeltnis, Abschuesse je Runde und Trefferquoten gesamt, PVP und PVE (gerechnet, nicht gespeichert). Seit 0.31 aus den Runden - bis 0.30 aus dem Profil, wo die Einstellungen stehen, und darum Nullen |
| **WERTE** | **Jeder** Zaehler, mit seinem Namen in der Datenbank daneben - und darunter alles, was sonst noch gespeichert ist, auch die Einstellungen im Profil |
| **WAFFEN** | Schuesse, Treffer, Abschuesse je Waffe, addiert aus allen Runden, mit dem Symbol aus dem Spiel |
| **ERLEDIGT** | Wen du wie oft erledigt hast, nach Konto (seit 0.31) |
| **RUNDEN** | Jede gespielte Runde einzeln, so wie sie in der Tabelle steht, mit Version und Ende |
| **AUSRUESTUNG** | Die drei Loadouts aendern und eines zum Tragen waehlen. Geaendert wird ein Entwurf, bis SPEICHERN - bis 0.29 sprang eine gewaehlte Waffe sofort zurueck, weil jede Auswahl die Seite aus dem Gespeicherten neu baute |
| **AUSSEHEN** | Grau. Vorbereitet, noch ohne Inhalt - siehe `docs/KOSMETIK.md` |
| **KOSMETIK** | Eigener Ton und eigenes Bild fuer die Blendgranate: MP3 laden und zuschneiden, Bass, lauter, mit Knall und Pfeifen aus dem Spiel mischen; Bild laden und filtern, auf dem Weiss verschieben und in der Groesse einstellen (sonst fuellt es den Schirm); Vorschau in Spielgroesse. Braucht die Tabelle aus 5.6 |
| **KONTO** | Anzeigename, Kennwort aendern, Kennung, Fassung, abmelden |

Ueber UEBERSICHT, WERTE, WAFFEN, ERLEDIGT und RUNDEN steht ein Filter:
**Version** (oder "vor 0.31"), **Art** (PVP, PVE, PVPVE) und ob
**abgebrochene Runden** mitzaehlen (5.7). Er gilt auf allen fuenf.

Mit dem Namen **admin** meldet sich der ADMIN an (5.8): eine Liste aller
Konten, dieselben Zahlenreiter ueber alle zusammen, und jedes Konto zum
Oeffnen - mit genau den Reitern, die sein Spieler sieht, und KONTO zum
Umbenennen, Kennwort setzen und Loeschen.

Dazu **ALLES HERUNTERLADEN**: Profil, alle Runden und die Kosmetik als JSON-Datei. Das
ist der Punkt an der Sache. Wer wissen will, was ueber ihn gespeichert
ist, soll es nicht erfragen muessen, sondern anklicken koennen.

### Was sie nicht kann, mit Absicht

* **Zahlen aendern.** Geschrieben werden genau drei Sachen: der
  Anzeigename, die Loadouts und die eigene Spielerkosmetik (5.6). Werte,
  die man selbst setzen kann, waeren keine Statistik mehr.
* **Das eigene Konto loeschen.** Das kann nur der ADMIN (5.8) - ohne
  *secret key*, der in keiner Datei stehen darf, die jemand herunterladen
  kann.
* **Fremde Konten sehen.** Der Zeilenschutz laesst nur die eigenen Zeilen
  durch, und das entscheidet der Server, nicht die Seite. Die einzige
  Ausnahme ist der ADMIN (5.8), und der geht nicht am Zeilenschutz
  vorbei, sondern durch Funktionen, die sein Kennwort pruefen.

### Wie sie gebaut ist

**Sie wird erzeugt, nicht getippt:**

```
python -m dustfront --kontoseite      (oder: python werkzeug_kontoseite.py)
```

`werkzeug_kontoseite.py` nimmt `kontoseite_vorlage.html` und schiebt an
einer einzigen Stelle (`/*DATEN*/`) alles hinein, was die Seite ueber
DUSTFRONT wissen muss: Zugang, Waffen mit Namen und Bild, die Namen
aller Werte, die Loadout-Regeln, Spielarten, Mannschaftsfarben,
Seltenheitsstufen - und die Pixelschrift des Spiels als Punktmuster,
mit der die Ueberschriften auf eine Leinwand gemalt werden.

**Warum erzeugt:** weil sonst dieselben Sachen zweimal gepflegt werden
muessten, und zweimal gepflegt heisst einmal gepflegt. Wer eine Waffe
hinzufuegt, soll sie auf der Seite sehen, ohne daran zu denken.
`tests/test_konto.py` prueft darum auch, ob die **eingecheckte**
`KONTO.html` noch zu `config.py` passt - wenn nicht, sagt der Test,
womit sie neu zu erzeugen ist.

**Warum eine einzige Datei:** eine Seite unter `file://` darf keine
Nachbardateien laden. Kein `fetch` auf eine JSON daneben, kein
`<script src=...>`. Bilder gehen als `data:`-URI mit, alles andere steht
im Quelltext. Das ist auch der Grund, warum sie ueberhaupt so
funktionieren kann: Supabase antwortet mit
`access-control-allow-origin: *`, also nimmt es auch eine Anfrage von
einer Datei ohne Herkunft an.

### Etwas dazubauen

Ein neuer Reiter ist **ein Eintrag** in `SEITEN` in der Vorlage:

```js
{name:"AUSSEHEN", frei:true, bauen:(ziel) => { ... }},
```

Die Leiste, das Umschalten und das Neuzeichnen ergeben sich daraus.
`frei:false` macht ihn grau und zeigt beim Darueberfahren, was fehlt -
so steht in der Seite selbst, was noch kommt.

Alles, was mit dem Server redet, steht in `Netz`; was gerade bekannt
ist, in `Stand`. Zwei Stellen, nicht zwanzig.

---

### 5.6 Spielerkosmetik (seit 0.28)

Eigener Ton und eigenes Bild fuer die Blendgranate, gemacht in der
Kontoseite (Reiter KOSMETIK). Dafuer braucht es **eine weitere Tabelle**.
Einmal im **SQL Editor** ausfuehren:

```sql
-- ── Kosmetik: eine Zeile je Konto ───────────────────────────────────
-- Eigene Tabelle und nicht das Profil: das Profil geht bei jedem
-- geaenderten Loadout hin und her, und eine Viertelmegabyte Ton jedes
-- Mal mitzuschicken waere Verschwendung.
create table if not exists kosmetik (
  konto      uuid primary key default auth.uid()
             references auth.users(id) on delete cascade,
  blend_ton  text not null default '',   -- WAV, Base64
  blend_bild text not null default '',   -- PNG, Base64
  geaendert  timestamptz not null default now(),
  -- Die Grenzen stehen auch hier, nicht nur im Spiel: ein veraenderter
  -- Klient soll den Server nicht mit Megabytes fuellen koennen.
  constraint kosmetik_ton_groesse  check (octet_length(blend_ton)  <= 540000),
  constraint kosmetik_bild_groesse check (octet_length(blend_bild) <= 210000)
);

alter table kosmetik enable row level security;

-- Die drop-Zeilen machen das Ganze wiederholbar: wer es ein zweites Mal
-- ausfuehrt, bekommt keinen Fehler "policy already exists".
drop policy if exists "eigene kosmetik lesen"    on kosmetik;
drop policy if exists "eigene kosmetik anlegen"  on kosmetik;
drop policy if exists "eigene kosmetik aendern"  on kosmetik;
drop policy if exists "eigene kosmetik loeschen" on kosmetik;
create policy "eigene kosmetik lesen"    on kosmetik for select using (auth.uid() = konto);
create policy "eigene kosmetik anlegen"  on kosmetik for insert with check (auth.uid() = konto);
create policy "eigene kosmetik aendern"  on kosmetik for update using (auth.uid() = konto)
                                                     with check (auth.uid() = konto);
create policy "eigene kosmetik loeschen" on kosmetik for delete using (auth.uid() = konto);
```

**Warum nur die eigene lesbar ist:** an die Kosmetik der anderen kommt man
nicht ueber den Server, sondern in der Lobby - jeder schickt seine selbst
an den Gastgeber, der verteilt sie. Wer nicht mit dir in einer Runde ist,
bekommt sie nie zu sehen.

Fehlt die Tabelle, sagt die Kontoseite es auf dem Reiter KOSMETIK; das
Spiel laeuft dann ohne Kosmetik weiter.

### 5.7 Version, Abbruch und Opfer (seit 0.31)

Seit 0.31 traegt jede Runde drei Spalten mehr: **mit welcher Version**
gespielt wurde, ob sie **regulaer endete oder abgebrochen** wurde, und
**wen man darin wie oft erledigt** hat. Einmal im **SQL Editor**
ausfuehren (wiederholbar):

```sql
-- ── 0.31: Version, Ende und Opfer je Runde ─────────────────────────
-- Mit welcher Fassung des Spiels gespielt wurde ("" = vor 0.31),
-- ob die Runde regulaer endete oder abgebrochen wurde, und wen man
-- darin wie oft erledigt hat ([{"name","konto","anzahl"}]).
alter table gefecht add column if not exists version text  not null default '';
alter table gefecht add column if not exists ende    text  not null default 'regulaer';
alter table gefecht add column if not exists opfer   jsonb not null default '[]'::jsonb;

-- Nur diese zwei. Ein Tippfehler im Spiel soll auffallen und nicht
-- als dritte Art von Ende in der Statistik stehen.
alter table gefecht drop constraint if exists gefecht_ende;
alter table gefecht add  constraint gefecht_ende check (ende in ('regulaer', 'abgebrochen'));

-- Wer nach Version filtert, soll nicht die ganze Tabelle lesen muessen.
create index if not exists gefecht_version on gefecht (version);

-- Supabase merkt sich die Spalten einer Tabelle. Ohne das kennt es die
-- neuen erst nach ein paar Minuten.
notify pgrst, 'reload schema';
```

**Was "abgebrochen" heisst:** die Runde endete vor ihrer Zeit - das Fenster
ging zu, die Verbindung riss, der Gastgeber ging zurueck in die Lobby oder
wechselte die Regeln. Sie wird trotzdem hochgeladen, mit allem, was bis
dahin gezaehlt war, aber mit `ende = 'abgebrochen'`, `runden = 0`,
`siege = 0` und `abgebrochen = 1` in den Werten. Die Uebersicht im Spiel
und auf der Kontoseite laesst sie weg, damit "Abschuesse je Runde" und
"Siege je Runde" stimmen; wer will, nimmt sie mit einem Haken dazu. Wie
viele es waren, steht immer da. Gebucht wird ein Abbruch erst ab
`GEFECHT["abbruch_ab"]` Sekunden (5) - wer eine Runde aufmacht und gleich
wieder zu, hat nicht gespielt.

**Wer bucht, wenn die Verbindung weg ist:** der Gastgeber schickt jedem Gast
alle `GEFECHT["zwischenstand_takt"]` Sekunden (2) seine Zahlen. Reisst die
Leitung, bucht der Gast diesen letzten Stand. Geht der Gastgeber geordnet
(ESC, Fenster zu), schickt er vorher allen dieselbe Partiekennung und ihre
Zahlen - genau wie beim regulaeren Ende. Beim Schliessen des Fensters
laedt das Spiel noch hoch, was offen ist (`Konto.hochladen_vor_ende`);
klappt das nicht, geht es beim naechsten Start hoch wie immer.

**Warum die Version:** wird spaeter etwas ausbalanciert (Zombies mit weniger
Leben, eine schwaechere Waffe), sind die Zahlen davor und danach nicht
dieselben. Die Kontoseite filtert danach; `Journal.summe(version=...)` im
Spiel ebenso. Runden von vor 0.31 haben die Version `''`.

**Ohne diese Spalten** geht jede Runde trotzdem hoch - das Spiel merkt am
Fehler `PGRST204`, dass der Server sie nicht kennt, und schickt sie ohne
(`ablage.py`, `SPALTEN_031`). Ob sie abgebrochen war, steht dann noch in
den Werten; Version und Opfer fehlen. Der Selbsttest (5.5) sagt es.

**Getrennt nach PVP und PVE** sind seit 0.31 auch Schuesse und Treffer
(`schuesse_pvp`, `treffer_pvp`, `schuesse_pve`, `treffer_pve`), dazu
Treffer auf Spieler und auf Zombies, Zombie- und Bossabschuesse, und je
Waffe die Abschuesse. Das sind Werte in der Spalte `werte` und brauchen
keine eigene Spalte.

### 5.8 Das ADMIN-Konto (seit 0.31)

Ein Konto, das alle anderen sieht und verwalten kann: alle Profile, die
Statistik aller zusammen, Loadouts und Kosmetik bearbeiten, Namen und
Kennwoerter aendern, Konten loeschen. Angemeldet wird auf der Kontoseite
mit dem Namen **admin**. Das erste Kennwort ist **123**; es muss sofort
geaendert werden, vorher geht nichts anderes.

Einmal im **SQL Editor** ausfuehren, **nach 5.2, 5.6 und 5.7**:

```sql
-- ── 0.31: Das ADMIN-Konto ──────────────────────────────────────────
-- Kein Konto im Anmeldedienst, sondern eine Zeile mit einem Kennwort-
-- Hash und Funktionen, die es bei jedem Aufruf pruefen. So steht nirgends
-- ein geheimer Schluessel, und der Zeilenschutz der Spieler bleibt, wie
-- er ist: ein Spieler sieht weiter nur sich selbst.
create extension if not exists pgcrypto with schema extensions;

create table if not exists public.admin_zugang (
  nr            int primary key default 1 check (nr = 1),    -- genau eine Zeile
  hash          text not null,                              -- bcrypt
  muss_aendern  boolean not null default true,              -- "123" gilt nur einmal
  fehlversuche  int not null default 0,
  gesperrt_bis  timestamptz,
  geaendert     timestamptz not null default now()
);
-- Zeilenschutz an und KEINE Regel: von aussen liest und schreibt niemand
-- diese Tabelle, auch kein angemeldeter Spieler. Nur die Funktionen unten.
alter table public.admin_zugang enable row level security;
revoke all on public.admin_zugang from public, anon, authenticated;

-- Das Anfangskennwort. Beim ersten Anmelden muss es geaendert werden;
-- vorher geht keine andere Funktion. "on conflict do nothing": ein
-- zweites Ausfuehren setzt ein geaendertes Kennwort NICHT zurueck.
insert into public.admin_zugang (nr, hash)
values (1, extensions.crypt('123', extensions.gen_salt('bf')))
on conflict (nr) do nothing;

-- Den Namen ADMIN bekommt kein Spieler. Sonst gaebe es zwei "admin",
-- und die Kontoseite wuesste nicht, welcher gemeint ist.
create or replace function public.name_vorbehalten() returns trigger
language plpgsql security definer set search_path = '' as $$
begin
  if lower(split_part(new.email, '@', 1)) = 'admin' then
    raise exception 'NAME VORBEHALTEN';
  end if;
  return new;
end $$;
drop trigger if exists name_vorbehalten on auth.users;
create trigger name_vorbehalten before insert on auth.users
  for each row execute function public.name_vorbehalten();

-- ── Pruefen und Sperren ───────────────────────────────────────────
-- Die ersten zwei Fehlversuche kosten nichts. Der dritte sperrt eine
-- Minute, der vierte 5, der fuenfte 15, der sechste 30, und danach
-- verdoppelt sich die Sperre mit jedem weiteren (60, 120, 240, ...).
-- Ein richtiges Kennwort setzt alles zurueck. Waehrend einer Sperre
-- wird gar nicht erst geprueft - auch das richtige Kennwort nicht,
-- sonst waere die Sperre keine - und es zaehlt auch nichts hoch.
--
-- Die Funktion wirft nie. Ein Fehler wuerde die Transaktion
-- zuruecknehmen und mit ihr den hochgezaehlten Fehlversuch: man koennte
-- dann beliebig oft raten. Darum kommt jede Antwort als JSON zurueck.
create or replace function public.admin_sperre_minuten(versuche int) returns numeric
language sql immutable set search_path = '' as $$
  select case
    when versuche < 3 then 0
    when versuche = 3 then 1
    when versuche = 4 then 5
    when versuche = 5 then 15
    -- Die Hochzahl ist gedeckelt (2^20 * 30 Minuten sind 60 Jahre),
    -- damit die Rechnung nie ueber das Ende des Kalenders hinauslaeuft.
    else 30 * power(2, least(versuche - 6, 20))
  end
$$;

create or replace function public.admin_pruefen(wort text) returns jsonb
language plpgsql security definer set search_path = '' as $$
declare
  z public.admin_zugang;
  minuten numeric;
begin
  select * into z from public.admin_zugang where nr = 1 for update;
  if not found then
    return jsonb_build_object('ok', false, 'fehler', 'KEIN ADMIN EINGERICHTET');
  end if;
  if z.gesperrt_bis is not null and z.gesperrt_bis > now() then
    return jsonb_build_object('ok', false, 'fehler', 'GESPERRT',
      'sekunden', ceil(extract(epoch from z.gesperrt_bis - now())));
  end if;
  if wort is not null and z.hash = extensions.crypt(wort, z.hash) then
    update public.admin_zugang set fehlversuche = 0, gesperrt_bis = null where nr = 1;
    return jsonb_build_object('ok', true, 'muss_aendern', z.muss_aendern);
  end if;
  minuten := public.admin_sperre_minuten(z.fehlversuche + 1);
  update public.admin_zugang
     set fehlversuche = z.fehlversuche + 1,
         gesperrt_bis = case when minuten > 0
                             then now() + minuten * interval '1 minute' end
   where nr = 1;
  return jsonb_build_object('ok', false, 'fehler', 'FALSCH',
    'fehlversuche', z.fehlversuche + 1,
    'sekunden', minuten * 60,
    -- Wie viele Fehlversuche noch nichts kosten. Nach dem zweiten: keiner.
    'frei', greatest(0, 1 - z.fehlversuche));
end $$;

-- Fuer alles ausser dem Anmelden und dem Kennwortwechsel: richtig, und
-- das Anfangskennwort schon ersetzt. Gibt null zurueck, wenn es geht.
create or replace function public.admin_darf(wort text) returns jsonb
language plpgsql security definer set search_path = '' as $$
declare p jsonb;
begin
  p := public.admin_pruefen(wort);
  if not (p->>'ok')::boolean then return p; end if;
  if (p->>'muss_aendern')::boolean then
    return jsonb_build_object('ok', false, 'fehler', 'ERST DAS KENNWORT AENDERN');
  end if;
  return null;
end $$;

-- Diese drei sind nur fuer die Funktionen hier, nicht fuer die Kontoseite.
revoke execute on function public.admin_pruefen(text)        from public, anon, authenticated;
revoke execute on function public.admin_darf(text)           from public, anon, authenticated;
revoke execute on function public.admin_sperre_minuten(int)  from public, anon, authenticated;

-- ── Anmelden, eigenes Kennwort ────────────────────────────────────
create or replace function public.admin_anmelden(wort text) returns jsonb
language plpgsql security definer set search_path = '' as $$
begin
  return public.admin_pruefen(wort);
end $$;

create or replace function public.admin_wort_aendern(wort text, neu text) returns jsonb
language plpgsql security definer set search_path = '' as $$
declare p jsonb;
begin
  p := public.admin_pruefen(wort);
  if not (p->>'ok')::boolean then return p; end if;
  if neu is null or length(neu) < 8 then
    return jsonb_build_object('ok', false, 'fehler', 'KENNWORT ZU KURZ (MINDESTENS 8)');
  end if;
  if length(neu) > 72 then
    return jsonb_build_object('ok', false, 'fehler', 'KENNWORT ZU LANG (HOECHSTENS 72)');
  end if;
  if neu = wort then
    return jsonb_build_object('ok', false, 'fehler', 'DAS IST DAS ALTE KENNWORT');
  end if;
  update public.admin_zugang
     set hash = extensions.crypt(neu, extensions.gen_salt('bf')),
         muss_aendern = false, geaendert = now()
   where nr = 1;
  return jsonb_build_object('ok', true);
end $$;

-- ── Lesen ─────────────────────────────────────────────────────────
create or replace function public.admin_konten(wort text) returns jsonb
language plpgsql security definer set search_path = '' as $$
declare f jsonb;
begin
  f := public.admin_darf(wort);
  if f is not null then return f; end if;
  return jsonb_build_object('ok', true, 'konten', coalesce((
    select jsonb_agg(jsonb_build_object(
             'konto',      u.id,
             'anmeldename', split_part(u.email, '@', 1),
             'name',       coalesce(p.name, ''),
             'fassung',    coalesce(p.fassung, 0),
             'runden',     (select count(*) from public.gefecht g where g.konto = u.id),
             'angelegt',   extract(epoch from u.created_at)::bigint)
           order by lower(u.email))
      from auth.users u left join public.profil p on p.konto = u.id), '[]'::jsonb));
end $$;

create or replace function public.admin_profil(wort text, konto uuid) returns jsonb
language plpgsql security definer set search_path = '' as $$
declare f jsonb; p public.profil;
begin
  f := public.admin_darf(wort);
  if f is not null then return f; end if;
  select * into p from public.profil where profil.konto = admin_profil.konto;
  if not found then
    return jsonb_build_object('ok', false, 'fehler', 'KEIN PROFIL ZU DIESEM KONTO');
  end if;
  return jsonb_build_object('ok', true, 'profil', jsonb_build_object(
    'name', p.name, 'fassung', p.fassung, 'werte', p.werte, 'loadouts', p.loadouts));
end $$;

-- Die Runden, seitenweise: ohne Konto die aller Spieler zusammen.
create or replace function public.admin_gefechte(wort text, konto uuid default null,
                                                 ab int default 0, anzahl int default 1000)
returns jsonb
language plpgsql security definer set search_path = '' as $$
declare f jsonb;
begin
  f := public.admin_darf(wort);
  if f is not null then return f; end if;
  return jsonb_build_object('ok', true, 'gefechte', coalesce((
    select jsonb_agg(to_jsonb(g) order by g.gespielt desc, g.partie, g.konto)
      from (select * from public.gefecht x
             where admin_gefechte.konto is null or x.konto = admin_gefechte.konto
             order by x.gespielt desc, x.partie, x.konto
             offset greatest(0, ab) limit least(greatest(1, anzahl), 1000)) g), '[]'::jsonb));
end $$;

create or replace function public.admin_kosmetik(wort text, konto uuid) returns jsonb
language plpgsql security definer set search_path = '' as $$
declare f jsonb; k public.kosmetik;
begin
  f := public.admin_darf(wort);
  if f is not null then return f; end if;
  select * into k from public.kosmetik where kosmetik.konto = admin_kosmetik.konto;
  return jsonb_build_object('ok', true, 'ton', coalesce(k.blend_ton, ''),
                            'bild', coalesce(k.blend_bild, ''));
end $$;

-- ── Aendern ───────────────────────────────────────────────────────
-- Dieselbe Regel wie fuer den Spieler: nur, wenn die Fassung noch
-- stimmt. Sonst ueberschriebe der ADMIN, was das Spiel gerade gespeichert
-- hat, oder umgekehrt - und ein Loadout waere still verschwunden.
create or replace function public.admin_profil_schreiben(wort text, konto uuid, fassung bigint,
                                                         name text, werte jsonb, loadouts jsonb)
returns jsonb
language plpgsql security definer set search_path = '' as $$
declare f jsonb; p public.profil;
begin
  f := public.admin_darf(wort);
  if f is not null then return f; end if;
  update public.profil
     set fassung  = profil.fassung + 1,
         name     = coalesce(nullif(admin_profil_schreiben.name, ''), profil.name),
         werte    = coalesce(admin_profil_schreiben.werte, '{}'::jsonb),
         loadouts = coalesce(admin_profil_schreiben.loadouts, '[]'::jsonb),
         geaendert = now()
   where profil.konto = admin_profil_schreiben.konto
     and profil.fassung = admin_profil_schreiben.fassung
  returning * into p;
  if not found then
    return jsonb_build_object('ok', false, 'fehler', 'PROFIL WURDE ZWISCHENDURCH GEAENDERT');
  end if;
  return jsonb_build_object('ok', true, 'profil', jsonb_build_object(
    'name', p.name, 'fassung', p.fassung, 'werte', p.werte, 'loadouts', p.loadouts));
end $$;

-- Beides leer heisst: weg damit. Die Groessengrenzen der Tabelle gelten
-- auch hier - eine zu grosse Datei wird abgelehnt, nicht abgeschnitten.
create or replace function public.admin_kosmetik_schreiben(wort text, konto uuid,
                                                           ton text, bild text)
returns jsonb
language plpgsql security definer set search_path = '' as $$
declare f jsonb;
begin
  f := public.admin_darf(wort);
  if f is not null then return f; end if;
  if coalesce(ton, '') = '' and coalesce(bild, '') = '' then
    delete from public.kosmetik where kosmetik.konto = admin_kosmetik_schreiben.konto;
    return jsonb_build_object('ok', true);
  end if;
  begin
    insert into public.kosmetik (konto, blend_ton, blend_bild, geaendert)
    values (admin_kosmetik_schreiben.konto, coalesce(ton, ''), coalesce(bild, ''), now())
    on conflict on constraint kosmetik_pkey do update
      set blend_ton = excluded.blend_ton, blend_bild = excluded.blend_bild,
          geaendert = now();
  exception when check_violation then
    return jsonb_build_object('ok', false, 'fehler', 'ZU GROSS FUER DEN SERVER');
  end;
  return jsonb_build_object('ok', true);
end $$;

-- Der Name, mit dem man sich anmeldet. Er steckt an drei Stellen im
-- Anmeldedienst (Adresse, Metadaten, Identitaet) und im Profil, und
-- alle vier muessen zusammen wechseln - sonst meldet man sich mit dem
-- neuen Namen an und heisst im Spiel noch wie vorher.
create or replace function public.admin_name_aendern(wort text, konto uuid, neu text)
returns jsonb
language plpgsql security definer set search_path = '' as $$
declare f jsonb; alt text; adresse text;
begin
  f := public.admin_darf(wort);
  if f is not null then return f; end if;
  neu := trim(coalesce(neu, ''));
  -- Dieselben Regeln wie im Spiel (ablage.name_pruefen).
  if neu !~ '^[[:alnum:]][[:alnum:]_-]{2,23}$' then
    return jsonb_build_object('ok', false, 'fehler',
      'NAME: 3 BIS 24 ZEICHEN, BUCHSTABEN, ZIFFERN, - UND _');
  end if;
  if lower(neu) = 'admin' then
    return jsonb_build_object('ok', false, 'fehler', 'NAME VORBEHALTEN');
  end if;
  select email into alt from auth.users where id = admin_name_aendern.konto;
  if not found then
    return jsonb_build_object('ok', false, 'fehler', 'KONTO NICHT GEFUNDEN');
  end if;
  adresse := lower(neu) || '@' || split_part(alt, '@', 2);
  if exists (select 1 from auth.users
              where lower(email) = adresse and id <> admin_name_aendern.konto) then
    return jsonb_build_object('ok', false, 'fehler', 'NAME SCHON VERGEBEN');
  end if;
  update auth.users
     set email = adresse,
         raw_user_meta_data = coalesce(raw_user_meta_data, '{}'::jsonb)
                              || jsonb_build_object('name', neu),
         updated_at = now()
   where id = admin_name_aendern.konto;
  update auth.identities
     set identity_data = coalesce(identity_data, '{}'::jsonb)
                         || jsonb_build_object('email', adresse)
   where user_id = admin_name_aendern.konto and provider = 'email';
  update public.profil set name = neu, fassung = profil.fassung + 1, geaendert = now()
   where profil.konto = admin_name_aendern.konto;
  return jsonb_build_object('ok', true, 'anmeldename', lower(neu));
end $$;

-- Ein neues Kennwort fuer ein Konto. Alle Anmeldungen dieses Kontos
-- enden damit - wer das alte kannte, soll nicht angemeldet bleiben.
create or replace function public.admin_kennwort_setzen(wort text, konto uuid, neu text)
returns jsonb
language plpgsql security definer set search_path = '' as $$
declare f jsonb;
begin
  f := public.admin_darf(wort);
  if f is not null then return f; end if;
  if neu is null or length(neu) < 8 then
    return jsonb_build_object('ok', false, 'fehler', 'KENNWORT ZU KURZ (MINDESTENS 8)');
  end if;
  if length(neu) > 72 then
    return jsonb_build_object('ok', false, 'fehler', 'KENNWORT ZU LANG (HOECHSTENS 72)');
  end if;
  update auth.users
     set encrypted_password = extensions.crypt(neu, extensions.gen_salt('bf')),
         updated_at = now()
   where id = admin_kennwort_setzen.konto;
  if not found then
    return jsonb_build_object('ok', false, 'fehler', 'KONTO NICHT GEFUNDEN');
  end if;
  delete from auth.sessions where user_id = admin_kennwort_setzen.konto;
  return jsonb_build_object('ok', true);
end $$;

-- Weg damit: das Konto, sein Profil, seine Runden, seine Kosmetik. Die
-- drei Tabellen haengen mit "on delete cascade" am Konto (5.2, 5.6).
create or replace function public.admin_loeschen(wort text, konto uuid) returns jsonb
language plpgsql security definer set search_path = '' as $$
declare f jsonb;
begin
  f := public.admin_darf(wort);
  if f is not null then return f; end if;
  delete from auth.users where id = admin_loeschen.konto;
  if not found then
    return jsonb_build_object('ok', false, 'fehler', 'KONTO NICHT GEFUNDEN');
  end if;
  return jsonb_build_object('ok', true);
end $$;

notify pgrst, 'reload schema';
```

**Wie es gebaut ist - und warum so.** Der ADMIN ist kein Konto im
Anmeldedienst, sondern eine Zeile in `admin_zugang` mit einem bcrypt-Hash.
Jede Funktion bekommt das Kennwort mit und prueft es selbst
(`security definer`: sie laeuft mit den Rechten dessen, der sie angelegt
hat, und kommt darum an alle Zeilen). Das hat drei Gruende:

* **Kein geheimer Schluessel in einer Datei.** Fremde Kennwoerter setzen und
  Konten loeschen geht sonst nur mit dem *secret key*, und der darf nie in
  `KONTO.html` stehen. So bleibt der oeffentliche Schluessel der einzige.
* **Der Zeilenschutz der Spieler bleibt unangetastet.** Kein Spieler
  bekommt mehr Rechte; die Regeln aus 5.2 gelten weiter genau so.
* **Die Sperre sitzt im Server.** Eine Sperre in der Seite umgeht jeder,
  der die Seite neu laedt.

Das Kennwort des ADMIN steht nur im Speicher der offenen Seite, nie im
Browser gespeichert: wer die Seite neu laedt, meldet sich neu an.

**Die Sperre.** Zwei Fehlversuche kosten nichts. Der dritte sperrt
**1 Minute**, der vierte **5**, der fuenfte **15**, der sechste **30**,
danach verdoppelt sich die Sperre mit jedem weiteren Fehlversuch (60, 120,
240 Minuten, ...). Ein richtiges Kennwort setzt alles zurueck. Waehrend
einer Sperre wird gar nicht erst geprueft, auch nicht das richtige
Kennwort. Die Funktionen werfen nie, sondern antworten mit JSON: ein
Fehler naehme die Transaktion zurueck und mit ihr den gezaehlten
Fehlversuch.

**Ausgesperrt?** Im SQL Editor (dort ist man ohnehin Besitzer der Datenbank):

```
update admin_zugang set fehlversuche = 0, gesperrt_bis = null;
```

**Kennwort vergessen?** Ebenda zurueck auf `123` - beim naechsten Anmelden
muss es wieder geaendert werden:

```
update admin_zugang set hash = extensions.crypt('123', extensions.gen_salt('bf')),
                        muss_aendern = true, fehlversuche = 0, gesperrt_bis = null;
```

**Der Name ADMIN ist vorbehalten.** Kein Spieler kann ihn anlegen (der
Ausloeser `name_vorbehalten`, und Spiel und Kontoseite pruefen es schon
vorher), und der ADMIN kann niemanden so umbenennen.

**Was der ADMIN tut, tut er wirklich.** Ein neues Kennwort beendet alle
Anmeldungen des Kontos. Ein geloeschtes Konto ist mit allen Runden, dem
Profil und der Kosmetik weg - es gibt kein Zurueck. Die Kontoseite fragt
darum vorher nach dem Namen des Kontos.

**Statistik aller.** Die Kontoseite liest dafuer alle Runden aller Konten
(`admin_gefechte` ohne Konto, je 1000) und rechnet sie mit denselben
Filtern zusammen wie die eigenen: Version, Art, Abbrueche.

`tests/test_admin_sql.py` fuehrt diesen Abschnitt (und 5.2, 5.6, 5.7) gegen
ein nachgebautes Supabase in einem lokalen PostgreSQL aus und prueft jede
Funktion, die Sperre und den Zeilenschutz.

## 6. Ohne Server

Alles laeuft weiter, nur eben auf diesem Rechner:

```
python -m dustfront --konto liste                       Konten anzeigen
python -m dustfront --konto neu   --name MEISTER        Konto anlegen
python -m dustfront --konto pruef --name MEISTER        Kennwort pruefen
```

Das ist nicht als Notloesung gedacht. Der Gastgeber einer LAN-Runde kann
damit seinen Gaesten Konten anlegen, ohne dass irgendwo ein Server
laufen muss - im Keller mit vier Leuten und ohne Internet hat trotzdem
jeder seine Zahlen und seine Loadouts.

Kennwoerter liegen dabei als **scrypt**-Hash mit eigenem Salz je Konto
(aus `hashlib`, also wieder ohne Fremdpaket). Wer die Datei findet, hat
damit noch keine Kennwoerter.

---

## 7. Loadouts

Ein Loadout ist **zwei Waffen und eine Wurfwaffe**. Das Brecheisen steht
nicht drin: es liegt auf `F` und ist immer da. Drei Loadouts lassen sich
anlegen; sie liegen im Profil und wandern damit mit dem Konto mit.

Der Gastgeber entscheidet, ob sie gelten:

* **eigenes** - jeder traegt sein gewaehltes Loadout,
* **alles** - jeder hat alles, wie bisher.

Beides muss es geben. "Alles" ist die Runde, in der man einfach spielt;
"eigenes" ist die, in der die Wahl der Waffe eine Wahl ist.

Gefragt wird nur beim ersten Mal. Wer schon einen Satz gespeichert hat,
soll nicht jedes Mal eine Maske wegklicken - das merkt sich das Profil in
`werte["loadout_gewaehlt"]`.

Alles davon steht in `LOADOUT` in `config.py`: wie viele Plaetze, wie
viele Waffen, woraus gewaehlt werden darf und womit ein neues Loadout
vorbelegt wird.

---

## 8. Dateien

| Datei | Was drin ist |
|---|---|
| `dustfront/ablage.py` | Die zwei Ablagen und die Schnittstelle dazwischen |
| `dustfront/konto.py` | Anmeldung, Profil, Loadouts, Journal, der Faden fuers Netz |
| `dustfront/config.py` | `WERTE`, `WAFFEN_WERTE`, `LOADOUT`, `KONTO` |
| `tests/test_konto.py` | Alles davon, ohne Netz - mit nachgebautem Server |
| `tests/test_admin_sql.py` | Das SQL aus 5.2 bis 5.8 gegen ein lokales PostgreSQL |
| `tests/kontoseite_browser.py` | Die Kontoseite in Chromium, mit vorgetaeuschtem Server |
| `<Benutzerordner>/konten.json` | Lokale Konten (nur ohne Server) |
| `<Benutzerordner>/sitzung.json` | Die laufende Anmeldung und das Profil |
| `<Benutzerordner>/journal.json` | Die gespielten Runden, mit Haken |
| `<Benutzerordner>/server.json` | Eigener Zugang, falls gewuenscht |
| `KONTO.html` | Die Kontoseite zum Doppelklicken (5a). Erzeugt |
| `kontoseite_vorlage.html` | Ihre Vorlage. **Hier wird geaendert**, nicht in KONTO.html |
| `werkzeug_kontoseite.py` | Erzeugt die eine aus der anderen |
| `--konto server` | Die Abnahme eines frisch aufgesetzten Projekts (5.5) |
| `dustfront/zertifikate.pem` | Mitgelieferte Wurzelzertifikate (9) |
| `dustfront/windows_tls.py` | Unter Windows: Windows das Zertifikat pruefen lassen (9) |
| `<Benutzerordner>/zertifikate.pem` | Die Wurzel des eigenen Netzes, falls es HTTPS mitliest (9) |

Wo der Benutzerordner liegt, sagt `python -m dustfront --konto liste`.

---

## 9. Wenn die Anmeldung ZERTIFIKAT sagt

Gemeldet aus dem Netz einer Klinik: das Spiel meldete beim Anmelden
`SERVER NICHT ERREICHBAR [SSL: CERTIFICATE_VERIFY_FAILED ...]`, Firefox
oeffnete dieselbe Adresse ohne Murren. Seit 0.28 heisst die Meldung
`ZERTIFIKAT UNBEKANNT [KONTO.MD 9]` - und hier steht, was dahinter steckt.

**Die Pruefung wird nie abgeschaltet.** Ohne sie koennte sich jeder im
selben Netz als Server ausgeben und Kennwoerter mitlesen. Stattdessen
bekommt das Spiel die Wurzel, die ihm fehlt. Drei Ursachen gibt es:

| Ursache | Was das Spiel dagegen tut |
|---|---|
| **Windows hat die Wurzel noch nicht.** Windows laedt Wurzelzertifikate erst nach, wenn ein Programm sie ueber Windows anfragt. Python sieht nur, was schon da ist. | Die Wurzeln der ueblichen Stellen (Google Trust Services, Let's Encrypt, GlobalSign, DigiCert, Amazon, Sectigo) liegen bei: `dustfront/zertifikate.pem`. Seit 0.28, nichts zu tun. |
| **Python und Windows urteilen verschieden.** Die Firewall eines Hauses bringt Zwischenzertifikate mit, die nur Windows kennt, oder ein Zertifikat, das OpenSSL anders liest. | Unter Windows fragt das Spiel dann Windows (seit 0.29, siehe unten). Nichts zu tun. |
| **Python ab 3.13 prueft streng** (RFC 5280) und lehnt viele Zertifikate ab, die Firmen- und Kliniknetze selbst ausstellen - auch wenn Windows ihnen vertraut. | Die Strenge ist zurueckgenommen. Die Kette wird weiter ganz geprueft, nur Formfehler in den Erweiterungen fuehren nicht mehr zur Ablehnung - wie im Browser. Seit 0.28, nichts zu tun. |
| **Das Netz liest HTTPS mit.** Eine Firewall unterschreibt jede Verbindung mit einem eigenen Zertifikat neu. Ihre Wurzel kennt der Browser (die Verwaltung hat sie dort eingetragen), Python nicht. | Liegt `zertifikate.pem` im Benutzerordner, wird sie zusaetzlich geladen. Die Datei muss man selbst holen, siehe unten. |

**Seit 0.29 fragt das Spiel unter Windows Windows selbst** (`windows_tls.py`),
wenn Python ablehnt - so wie Edge und Chrome es tun. Damit gilt, was auf
dem Rechner gilt: die Wurzeln, die die Verwaltung eingetragen hat, die
Zwischenzertifikate der Firewall, die Wurzeln, die Windows bei Bedarf
nachlaedt. Gemeldet war nach 0.28.1 noch `ZERTIFIKAT UNGUELTIG` - genau
der Fall, in dem Python und Windows verschieden urteilen. Wie das geht:

1. Verbindung aufbauen, Handschlag, die Kette des Servers lesen. Noch ist
   nichts gesendet.
2. Windows pruefen lassen: `CertGetCertificateChain`, dann
   `CertVerifyCertificateChainPolicy` mit der SSL-Regel und dem Namen
   des Servers.
3. Nur bei einem Ja geht die Anfrage hinaus. **Jeder Fehler heisst nein** -
   auch einer im Code, der Windows fragt.

Hat Windows einmal ja gesagt, wird ab da gleich Windows gefragt.

**Ohne Eingabeaufforderung:** die Anmeldetafel zeigt unter der Meldung
zwei Zeilen - `GRUND:` (was OpenSSL oder Windows gesagt hat) und `VON:`
(wer das Zertifikat ausgestellt hat, das ankommt). Das ist dasselbe, was
der Selbsttest sagt.

**Welche es ist, sagt auch der Selbsttest:**

```
python -m dustfront --konto server
```

Scheitert er am Zertifikat, schreibt er dazu, **wer** das Zertifikat
ausgestellt hat, das ankommt. Steht da Google Trust Services oder Let's
Encrypt, ist es eine der ersten beiden Ursachen. Steht da der Name einer
Firewall (Fortinet, Sophos, Palo Alto, Zscaler, Cisco ...) oder des
Hauses, liest das Netz mit.

### Die Wurzel des Netzes aus Firefox holen

1. In Firefox die Adresse des Servers oeffnen (die `url` aus `SERVER` in
   `ablage.py` oder aus `server.json`, also `https://<projekt>.supabase.co`).
   Was die Seite anzeigt, ist egal - es geht nur um die Verbindung.
2. Links in der Adressleiste auf das **Schloss** klicken, dann
   **Verbindung sicher**, dann **Weitere Informationen**, dann
   **Zertifikat anzeigen**.
3. Oben stehen Reiter, einer je Zertifikat der Kette. Der **rechte** ist
   die Wurzel. Ihn waehlen, nach unten zu **Verschiedenes** und bei
   **Herunterladen** auf **PEM (Zertifikat)** klicken.
4. Die Datei in **`zertifikate.pem`** umbenennen und in den Benutzerordner
   legen - unter Windows `%APPDATA%\Dustfront` (so in die Adresszeile des
   Explorers tippen). Wo er genau liegt, sagt
   `python -m dustfront --konto liste`.
5. Das Spiel neu starten.

Mehrere Wurzeln duerfen in derselben Datei stehen, einfach hintereinander.
Eine kaputte Datei haelt das Spiel nicht auf; sie wird uebergangen.

**Nur die Wurzel des eigenen Netzes nehmen**, und nie eine Datei, die
einem jemand schickt. Wer eine Wurzel in diese Datei bekommt, kann alles
mitlesen, was das Spiel mit dem Server redet.

Geht es gar nicht, bleibt **OHNE KONTO SPIELEN**: alles laeuft, gezaehlt
wird auf diesem Rechner (6). Oder ein anderes Netz, etwa der Hotspot
eines Telefons.

### Die mitgelieferten Wurzeln erneuern

`dustfront/zertifikate.pem` ist ein Auszug aus der Liste von Mozilla,
ueber das Python-Paket `certifi`. Wurzeln laufen nach zehn bis
fuenfundzwanzig Jahren ab; wer sie erneuern will, nimmt aus
`certifi.where()` dieselben Eintraege (die Namen stehen in der Datei als
`# Label:`) und ersetzt die Datei. Die eigenen des Systems und die im
Benutzerordner gelten weiter daneben.

