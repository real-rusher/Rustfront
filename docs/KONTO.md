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
2. **Der oeffentliche Schluessel darf oeffentlich sein.** Der *anon key*
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

**Keine Adresse.** Supabase will fuer ein Konto eine E-Mail-Adresse.
Angemeldet wird deshalb mit `<name>@spieler.dustfront`, einer Domaene,
die es nicht gibt und nie geben wird. Eine echte Adresse wird nicht
abgefragt: sie waere fuer ein Schulprojekt eine Menge personenbezogener
Daten, die niemand braucht.

---

## 5. Aufsetzen

Zehn Minuten, einmalig.

### 5.1 Projekt anlegen

1. Auf <https://supabase.com> mit GitHub anmelden, **New project**.
2. Name egal, Region moeglichst nah, Datenbankkennwort notieren (wird
   hier nie gebraucht, aber Supabase fragt danach).
3. Warten, bis es steht.

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
create or replace function neues_profil() returns trigger
language plpgsql security definer as $$
begin
  insert into profil (konto, name)
  values (new.id, coalesce(new.raw_user_meta_data->>'name', 'SPIELER'))
  on conflict (konto) do nothing;
  return new;
end $$;

drop trigger if exists profil_anlegen on auth.users;
create trigger profil_anlegen after insert on auth.users
  for each row execute function neues_profil();
```

### 5.3 Bestaetigung per Post ausschalten

**Authentication → Providers → Email**: *Confirm email* **aus**. Sonst
wartet jedes neue Konto auf eine Bestaetigung an eine Adresse, die es
nicht gibt.

### 5.4 Zugang eintragen

**Project Settings → API**: dort stehen *Project URL* und der *anon
public* Schluessel. Beides in `dustfront/ablage.py` oben in `SERVER`
eintragen:

```python
SERVER = {
    "url": "https://abcdefghijkl.supabase.co",
    "schluessel": "eyJhbGciOi...",
}
```

Beides darf im Quelltext stehen und ins Repository - genau darum geht die
Anmeldung auf einem frisch heruntergeladenen Spiel sofort.

Wer ein eigenes Projekt benutzen will, ohne den Quelltext zu aendern,
legt stattdessen `server.json` in den Benutzerordner (siehe `pfade.py`):

```json
{"url": "https://...", "schluessel": "eyJ..."}
```

Diese Datei gilt vor `SERVER`.

### 5.5 Nachsehen, ob es geht

```
python -m dustfront --konto liste
```

zeigt, ob ein Server eingetragen ist. Danach im Spiel anmelden.

---

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
| `<Benutzerordner>/konten.json` | Lokale Konten (nur ohne Server) |
| `<Benutzerordner>/sitzung.json` | Die laufende Anmeldung und das Profil |
| `<Benutzerordner>/journal.json` | Die gespielten Runden, mit Haken |
| `<Benutzerordner>/server.json` | Eigener Zugang, falls gewuenscht |

Wo der Benutzerordner liegt, sagt `python -m dustfront --konto liste`.
