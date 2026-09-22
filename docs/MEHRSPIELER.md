# DUSTFRONT - Der Mehrspieler, vollstaendig

**Was das hier ist.** Die komplette Beschreibung des LAN-Mehrspielers, wie
er auf dem Zweig `multiplayer-test` in Version 0.18.0 steht: Aufbau,
Protokoll, alle sechs Spielarten, jede Zahl mit Begruendung, jeder Fehler,
der beim Bauen aufgetreten ist, und die Reihenfolge, in der man das Ganze
wieder aufbaut.

**Warum es das gibt.** Der Mehrspieler war ein Test und ist fertig. Der
Hauptzweig geht **ohne** ihn weiter (dort ist er aus der Historie
herausgenommen, siehe Abschnitt 14). Dieses Dokument ist die Bauanleitung
fuer den Tag, an dem er zurueckkommen soll.

**Fuer wen.** Fuer Der Meister, und fuer jede Claude-Instanz, die den Satz
hoert: *"bau mal wieder Mehrspieler ein wie in Version 0.18.0"*. Wer das
liest, braucht ausser dem Spielkern nichts weiter zu wissen.

**Stand beim Schreiben:** Version 0.18.0, PRE-ALPHA, Zweig
`multiplayer-test`. Zwei Testlaeufe gruen: `tests/test_spiel.py` und
`tests/test_menues.py`.

---

## 0. Wie dieses Dokument zu benutzen ist

| Ich will ... | Lies |
| --- | --- |
| verstehen, was es ueberhaupt gibt | 1, 2 |
| es wieder einbauen | 15, dann 3 bis 9 |
| eine Zahl aendern | 11 |
| einen Fehler suchen | 12 |
| wissen, was schon schiefging | 12 |
| wissen, was noch fehlt | 13 |

Drei Arten von Aussagen, immer unterscheidbar:

| Zeichen | Bedeutung |
| --- | --- |
| **FEST** | Steht so im Code. Wer es aendert, aendert Verhalten. |
| **GRUND** | Warum es so ist. Meist ein Fehler, der genau daher kam. |
| **OFFEN** | Bekannte Luecke. Nicht gebaut, bewusst oder aus Zeitmangel. |

---

## 1. Kurzfassung

Vier Dateien, rund 1500 Zeilen. Der Spielkern wurde dafuer fast
vollstaendig in Ruhe gelassen - das war die Bedingung, unter der sich der
ganze Zweig spaeter in einem Stueck wieder entfernen liess. Die beiden
Ausnahmen stehen in 2.4.

| Datei | Zeilen | Was drin steht |
| --- | ---: | --- |
| `dustfront/netz.py` | ~250 | Steckdosen, Verbindungen, JSON-Zeilen. Weiss nichts vom Spiel. |
| `dustfront/mehrspieler.py` | ~1400 | Die Spielszene `Gefecht` und drei Wesen. Weiss alles vom Spiel. |
| `dustfront/bestenliste.py` | ~110 | Bestenliste im Benutzerordner. |
| `dustfront/config.py` | +150 | `NETZ`, `MODI`, `TEAMS`, `ZONE`, `VERSUS`, `GEFECHT`, `REVIVE`, `WELLEN_MP`, `GEGNER_MP`, `MUNITION`. |

Dazu: vier Startdateien (`LAN-GASTGEBER.bat/.command`,
`LAN-GAST.bat/.command`), Schalter in `main.py` und die Pruefungen im
Abschnitt "LAN-Gefecht" von `tests/test_spiel.py`.

**Sechs Spielarten:**

| Schluessel | Name | Gegner | Spieler treffen sich | Aufhelfen | Mannschaften | Endet durch |
| --- | --- | --- | --- | --- | --- | --- |
| `pvp` | PVP | nein | ja | nein | nein | Zeit oder Abschuesse |
| `pve` | PVE | ja | nein | ja | nein | alle liegen am Boden |
| `pvpve` | PVPVE | ja | ja | nein | nein | Zeit oder Abschuesse |
| `team` | TEAM | nein | ja | nein | ja | Zeit oder Teamabschuesse |
| `versus` | VERSUS | nein | ja | ja | ja | Rundensiege (Zeit als Notbremse) |
| `huegel` | HUEGEL | nein | ja | nein | ja | voller Kreis (Zeit als Notbremse) |

---

## 2. Grundentscheidungen

Vier Entscheidungen tragen alles Weitere. Wer eine davon umwirft, baut
etwas anderes.

### 2.1 Der Gastgeber rechnet alles

**FEST.** Ein Rechner hat die einzige echte Welt. Gaeste schicken nur, was
sie druecken, und bekommen zurueck, wo alles steht. Ein Gast simuliert
**nichts** - seine Figuren sind Attrappen, die an gemeldete Stellen gesetzt
werden.

**GRUND.** Kein Streit darueber, wer getroffen hat. Niemand kann durch eine
geaenderte Datei schummeln. Der Preis ist eine Verzoegerung von einem Hin-
und Rueckweg; im LAN sind das unter zwei Millisekunden.

**Die Folge, die man spuert:** Der Gast sieht seine eigene Figur mit
Verzoegerung. Es gibt **keine** Vorhersage (client-side prediction) und
**keine** Korrektur. Im LAN faellt das nicht auf, ueber das Internet waere
es unspielbar. Siehe 13.

### 2.2 Keine Threads

**FEST.** Die Steckdosen stehen auf nicht-blockierend, `select` mit
Zeitlimit 0, einmal je Bild wird nachgesehen, was angekommen ist.

**GRUND.** Ein Spiel hat ohnehin eine Schleife. Die zweite Schleife eines
Threads waere nur eine Quelle fuer Fehler, die man nicht nachstellen kann -
und nicht nachstellbare Fehler sind in einem Spiel mit festen Zeitschritten
das Letzte, was man will.

### 2.3 Eine JSON-Zeile je Nachricht

**FEST.** `json.dumps(...) + "\n"`, UTF-8, ueber TCP.

**GRUND.** Lesbar, mit blossem Auge zu pruefen, und der Zeilenumbruch loest
gleich das Problem, wo eine Nachricht aufhoert. Nicht das sparsamste
Format; bei acht Spielern im LAN ist Bandbreite kein Engpass.

**Wichtig:** TCP kennt keine Nachrichtengrenzen. Was als eine Zeile
losgeschickt wurde, kann in drei Stuecken ankommen, und drei Zeilen koennen
in einem Stueck ankommen. Beides passiert im LAN wirklich. Deshalb haelt
`Leitung` einen Puffer und schneidet an `\n`. Wer das vergisst, bekommt
`json.JSONDecodeError` unter Last - und nur unter Last.

### 2.4 Der Spielkern bleibt unangetastet

**FEST.** `entities.py`, `world.py` und `play.py` wurden fuer den
Mehrspieler so gut wie nicht geaendert (die zwei Ausnahmen stehen unten).
Wo etwas fehlte, wurde es umgangen:

* `Gegner.schritt()` liest `welt.held`. Statt das umzubauen, setzt
  `KampfGegner.schritt()` `welt.held` fuer die Dauer des Schritts auf sein
  eigenes Ziel und gibt es danach zurueck (`try/finally`).
* `Aufsammler` schaut nur auf `welt.held`. `KampfBeute` bringt seine eigene
  Abfrage ueber alle Kaempfer mit.
* Nachladen fuellt im Kern das Magazin randvoll. `Kaempfer.schritt()`
  verrechnet das **nachtraeglich** gegen den Vorrat, statt in den Kern
  einzugreifen.

**GRUND.** Genau dadurch liess sich der ganze Mehrspieler spaeter mit zwei
Reverts aus dem Hauptzweig nehmen, ohne dass am Spiel etwas fehlte.

**Zwei Ausnahmen, ab 0.17.0.** Die Rauchgranate und der Granatensturz
gehoeren zum Spiel, nicht zum Mehrspieler, und stehen darum im Kern:
`Rauchwolke` in `entities.py`, die Liste `welt.rauch` in `world.py`, das
Zeichnen in `render.py`. Der Mehrspieler schickt sie nur ueber die
Leitung. Wer ihn wieder herausnimmt, laesst beides stehen - es funktioniert
im Einzelspieler genauso.

---

## 3. Der Ablauf eines Bildes

Beide Seiten laufen in derselben Szene (`Gefecht`), unterschieden nur durch
`ist_gastgeber`.

**Gastgeber**, in dieser Reihenfolge (`_schritt_gastgeber`):

1. `annehmen()` - neue Gaeste hereinlassen.
2. Nachrichten holen: `hallo` -> `_dazu()` + `willkommen` zurueck;
   `ein` -> `_anwenden()`.
3. `gegangen()` - tote Leitungen wegraeumen, deren Kaempfer auf
   `lebt = False`.
4. Die eigene Eingabe auf die eigene Figur legen.
5. Wenn nicht vorbei: `_beute_nachlegen`, `_wellen`, `_zone`, `_runden`.
6. `_gegnerlast_zaehlen()`.
7. `welt.schritt(dt)` - der gewoehnliche Spielkern.
8. `_revive`, `_tote_abrechnen`, `_ende_pruefen`.
9. Alle `NETZ["takt"]` Sekunden: `_weltmeldung()` an alle.

**Gast** (`_schritt_gast`):

1. Nachrichten holen: `willkommen` -> Spielart uebernehmen;
   `welt` -> alles setzen; `ende` -> Endtafel.
2. Eingabe senden - entweder wenn `eingabe_takt` um ist **oder sofort**,
   wenn ein einmaliger Tastendruck wartet (siehe 12.1).

Ein Gast ruft `welt.schritt()` **nie** auf. Seine `welt.wesen` wird in
`_welt_uebernehmen` gesetzt:

```python
self.welt.wesen = [k for k in self.kaempfer.values() if k.lebt]
self.welt.neue = []
```

Alles andere (Gegner, Beute, Geschosse, Granaten) zeichnet er aus den
gemeldeten Punktlisten, ohne Wesen dafuer anzulegen (`_fremdes_zeichnen`).

---

## 4. Das Protokoll, vollstaendig

### 4.1 Gast -> Gastgeber

**`hallo`** - einmal beim Verbinden.

```json
{"t": "hallo", "name": "MEISTER"}
```

**`ein`** - der Eingabezustand, rund 60 Mal je Sekunde.

| Feld | Typ | Bedeutung |
| --- | --- | --- |
| `will` | `[x, y]` | Laufrichtung, laenger als 1 wird beim Gastgeber gekuerzt |
| `ziel` | `[x, y]` | Mauszeiger in Weltkoordinaten |
| `feuert` | bool | Feuertaste gehalten |
| `zielt` | bool | zweite Maustaste gehalten |
| `sprint` | bool | Sprinttaste gehalten |
| `nutzen` | bool | Nutzentaste **gehalten** (Treppe und Aufhelfen haengen daran) |
| `waffe` | int | gewuenschte Waffe, `-1` = keine Aenderung |
| `knoepfe` | Liste | einmalige Druecke seit dem letzten Paket: `nachladen`, `heilen`, `tracer`, `tracer_weit` |

`nutzen` ist bewusst **gehalten** und nicht **gedrueckt**: Aufhelfen
braucht Zeit. `knoepfe` ist bewusst eine Liste von Ereignissen - siehe
12.1, das ist der wichtigste Fehler des ganzen Zweigs.

### 4.2 Gastgeber -> Gast

**`willkommen`** - einmal je Gast. Die Spielart bestimmt **allein** der
Gastgeber; sonst spielen zwei Leute mit verschiedenen Regeln auf derselben
Karte.

```json
{"t": "willkommen", "id": 2, "name": "GAST",
 "modus": "huegel", "ende_art": "zeit", "ende_wert": 600.0, "knapp": false,
 "schutz": true, "medkits": 1, "medkit_spawn": true}
```

Die letzten drei sind die Schalter aus Abschnitt 7.7. Ein Gast stellt
nichts davon selbst - er uebernimmt, was hier steht.

**`welt`** - der ganze Zustand, `NETZ["takt"]` Mal je Sekunde. Kurze
Schluessel, weil das Paket oft geht.

Je Spieler in `spieler`:

| Kurz | Bedeutung | Kurz | Bedeutung |
| --- | --- | --- | --- |
| `i` | Nummer | `nl` | Nachladerest |
| `n` | Name | `fo` | Fokus (Scharfschuetze) |
| `p` | Position `[x, y]` | `zi` | zielt |
| `w` | Winkel | `tr` | Ziellinie an |
| `e` | Ebene | `tw` | Ziellinie verlaengert |
| `f` | Flughoehe im Sturz | `mk` | Medkits |
| `l` | Leben | `hr` | Heilrest |
| `b` | Waffenname | `sz` | Nahkampfschlag zeigen |
| `a` | Abschuesse | `wi` | wieder in x Sekunden |
| `d` | Tode | `ab` | am Boden |
| `v` | lebt | `br` | Bodenrest |
| `m` | Magazin | `rs` | Aufhelfstand 0..1 |
| `vo` | Vorrat | `tm` | **Mannschaft** (-1 = keine) |
| | | `ra` | **raus** (versus, diese Runde erledigt) |

Dazu global:

| Feld | Bedeutung |
| --- | --- |
| `rest` | Restzeit |
| `schuesse` | `[[x, y, winkel, ebene, name, flug], ...]` - Geschosse und Granaten. `flug` ist die Hoehe ueber der Zielebene: alles ueber 0 faellt gerade und wird beim Gast mit dem Massstab seiner eigenen Hoehe gezeichnet |
| `rauch` | `[[x, y, ebene, radius, alter], ...]` - Rauchwolken. Das Alter genuegt, die Dichte rechnet jede Seite daraus selbst |
| `beute` | `[[x, y, ebene, bild], ...]` |
| `gegner` | `[[x, y, winkel, ebene, art, lebensanteil], ...]` |
| `welle`, `pause`, `offen` | Wellenstand |
| `aus` | Runde vorbei |
| `tp` | **Teampunkte**, Liste |
| `zs` | **Ladestand des Kreises** je Mannschaft |
| `zh` | **wer den Kreis haelt**, -1 = niemand |
| `rn`, `rp` | **Runde**, **Rundenpause** |
| `st` | **Siegermannschaft**, -1 = keine |

**`ende`**

```json
{"t": "ende", "liste": [...], "gewonnen": true, "welle": 4,
 "sieger": 0, "teampunkte": [3, 1]}
```

### 4.3 Was **nicht** uebertragen wird

**FEST.** Partikel, Huelsen, Blutflecken, Staubwolken, Muendungsfeuer.

**GRUND.** Reine Kosmetik, entsteht bei jedem selbst. Wer sie mitschickte,
haette den zehnfachen Verkehr fuer nichts. Die Folge: Blutflecken liegen
bei jedem an anderen Stellen. Das faellt niemandem auf.

---

## 5. Fraktionen - wer wen treffen kann

Die Trefferabfrage in `world.py` ueberspringt alles, was zur selben
Fraktion gehoert. Alle Spieler tragen von Haus aus `"mensch"`, koennten
sich also nie treffen. `_fraktion_fuer()` regelt das:

| Lage | Fraktion | Wirkung |
| --- | --- | --- |
| mit Mannschaften | `"team0"` / `"team1"` | Nebenmann sicher, Gegner nicht |
| `beute=True`, ohne Mannschaften | `"kaempfer<nr>"` | jeder gegen jeden |
| sonst (pve) | `"mannschaft"` | niemand trifft den anderen |

**Das ist die gesamte Freundfeuer-Logik.** Keine zusaetzliche Abfrage, kein
Schalter. Wer eine dritte Mannschaft will, aendert eine Zeile in
`TEAMS["namen"]` - Zuteilung, Faerbung und Punktetafel rechnen alle ueber
die **Laenge** dieser Listen.

---

## 6. Mannschaften

### 6.1 Zuteilung

**FEST.** `_team_fuer()` gibt den Neuen in die **kleinere** Mannschaft.

**GRUND.** Nicht abwechselnd: wer geht, hinterlaesst sonst eine Luecke, die
nie wieder gefuellt wird. Nach drei Verbindungsabbruechen steht es sonst
3 gegen 1, obwohl vier Leute da sind.

### 6.2 Einstiegsort

**FEST.** `_einstiegsort(team)` wuerfelt `NETZ["hoechstens"] * 6` freie
Punkte und bewertet sie:

```
wert = Abstand zum naechsten Gegner - 0.5 * Abstand zum naechsten eigenen Mann
```

Der beste gewinnt. Ohne Mannschaften genuegt der einfache Fall: der erste
Punkt, der weiter als `GEFECHT["abstand"]` (160 px) von allen weg ist.

**GRUND.** Weit weg von den Gegnern zaehlt, nahe bei den eigenen hilft.
Ohne den zweiten Teil faengt jede Versus-Runde damit an, dass beide
Mannschaften quer ueber die Karte zueinander laufen.

### 6.3 Farben

`TEAMS["farben"]` ist die **helle** Fassung, `TEAMS["dunkel"]` die dunkle.
`_farbe_fuer()` gibt der eigenen Mannschaft hell, der fremden dunkel. Am
Boden liegende sind immer rot.

Die eigene Figur traegt **auch** die Mannschaftsfarbe (sonst weiss man
nicht, wer zu wem gehoert) und bekommt zusaetzlich einen kurzen weissen
Strich ueber dem Namen: *das bist du*. In der Punktetafel steht vor dem
eigenen Namen ein `>`.

---

## 7. Die Spielarten im Einzelnen

### 7.1 pvp

Jeder gegen jeden, jede Figur eine eigene Fraktion. Der Gastgeber waehlt:
Ende nach **Zeit** (`GEFECHT["rundenzeit"]`, 300 s) oder nach
**Abschuessen** (`GEFECHT["abschuesse_ziel"]`, 20). Wer sich selbst
erledigt, zahlt einen Punkt drauf (`punkt_selbst = -1`).

Nach dem Tod steigt man nach `GEFECHT["wieder_nach"]` (3 s) wieder ein, mit
`GEFECHT["schutz"]` (2 s) Unverwundbarkeit.

### 7.2 pve

Alle eine Fraktion, Wellen von Gegnern. Kein Ende nach Zeit - die Runde
endet, wenn **niemand mehr steht**.

Wer faellt, **stirbt nicht**, sondern liegt am Boden: `lebt` bleibt `True`,
damit die Figur weiter gezeichnet wird und ansprechbar bleibt. Am Boden
kriecht man mit `REVIVE["kriechen"]` (35 %) Tempo und kann nichts nutzen.

**Nach jeder Welle steht wieder jeder auf.** Das ist der Ausgleich dafuer,
dass eine Runde sonst mit dem ersten Fehler kippt.

### 7.3 pvpve

Wellen **und** jeder gegen jeden. Endet wie pvp. Kein Aufhelfen - wer
faellt, steigt wieder ein.

### 7.4 team - Deathmatch mit zwei Mannschaften

**FEST.** Abschuesse zaehlen doppelt: einmal fuer den Schuetzen
(Punktetafel) und einmal fuer die Mannschaft (Kopfzeile). Ende nach Zeit
oder nach `GEFECHT["team_abschuesse"]` (30).

Kein Aufhelfen, Wiedereinstieg wie in pvp. Das ist die **schnellste** der
drei Mannschaftsarten und die, in der man am wenigsten falsch machen kann.

### 7.5 versus - ein Leben je Runde

**FEST.**

* Ein Leben je Runde. Wer faellt, liegt am Boden.
* Aufhelfen **nur durch die eigene Mannschaft** (`_darf_helfen`).
* Wer am Boden die Zeit ausreizt, ist fuer die Runde **raus** (`raus`).
* Eine Runde ist zu Ende, wenn eine Mannschaft **niemanden mehr auf den
  Beinen hat**. Am Boden zaehlt noch als stehend - solange jemand
  aufhelfen kann, ist die Runde nicht entschieden.
* Fallen alle gleichzeitig, bekommt niemand den Punkt.
* `VERSUS["runden_bis"]` (3) Rundensiege entscheiden das Gefecht.
* Zwischen zwei Runden `VERSUS["pause"]` (5 s), danach stehen alle wieder
  auf neuen Plaetzen mit vollem Magazin.

**Eigene Zeiten:** am Boden `VERSUS["boden_zeit"]` (20 s statt 45),
Aufhelfen `VERSUS["revive_dauer"]` (4 s statt 3). Die Zeiten stehen am
`Kaempfer`, nicht fest im Code - deshalb kann versus andere haben als pve.

**GRUND fuer kuerzer am Boden:** In pve soll eine Welle zu schaffen sein,
da sind 45 s richtig. In versus wuerde eine Runde damit stehen bleiben:
zwei Leute liegen, niemand kann hin, alle warten. **GRUND fuer laengeres
Aufhelfen:** Aufhelfen ist in versus die staerkste Handlung im Spiel - sie
nimmt der anderen Mannschaft einen sicheren Rundensieg wieder weg. Sie
muss teuer sein.

**Solange eine Mannschaft leer ist, faengt keine Runde an.** Ohne das waere
jede Runde in dem Augenblick entschieden, in dem sie beginnt - der
Gastgeber allein haette in drei Sekunden gewonnen.

### 7.6 huegel - der Kreis in der Mitte

Nach dem Vorbild der Hot Zone aus Brawl Stars.

**FEST.**

* Der Kreis liegt in der **Mitte der Karte**, auf Ebene `ZONE["ebene"]`
  (0), mit Radius `ZONE["radius"]` (96 px = sechs Kacheln).
* Die Mitte wird beim Start aus den Kartenmassen gerechnet, auf **beiden**
  Seiten gleich - der Gast bekommt sie nicht geschickt, er rechnet dieselbe
  Zahl aus.
* Wer drin steht, muss **leben, stehen** (nicht am Boden) und auf der
  **richtigen Ebene** sein.
* Wer die **Mehrheit** hat, laedt fuer seine Mannschaft.
* Bei **Gleichstand laedt niemand** - auch nicht, wenn beide viele Leute
  drin haben. Der Stand verfaellt dann mit `ZONE["verfall"]`.
* Tempo: `je_sekunde + je_kopf * (Vorsprung - 1)`, gedeckelt auf
  `hoechstens`.
* Wer `ZONE["bis"]` (100) erreicht, gewinnt.

| Lage | Vorsprung | laedt je Sekunde |
| --- | ---: | ---: |
| 1 gegen 0 | 1 | 7.0 |
| 2 gegen 1 | 1 | 7.0 |
| 2 gegen 0 | 2 | 9.5 |
| 3 gegen 1 | 2 | 9.5 |
| 3 gegen 0 | 3 | 12.0 |

**GRUND.** Es zaehlt der **Vorsprung**, nicht die Kopfzahl: wer den Kreis
gegen Widerstand haelt, soll nicht schneller sein als der, der ihn leer
vorfindet. Und der Gleichstand macht den Kreis zu dem Ort, an dem man sich
trifft, statt ihn abwechselnd leerzuraeumen: wer allein hineinlaeuft laedt
schnell, wer auf Widerstand trifft muss ihn erst wegraeumen. Bei voller
Ladung dauert eine Runde allein rund 14 Sekunden - deshalb ist die
Anzeige zweifarbig und der Verfall langsam (1.2/s): ein Vorsprung ist
etwas wert, aber nie endgueltig.

---

### 7.7 Was der Gastgeber sonst noch stellt

Vier Schalter, die zu jeder Spielart gehoeren. Alle stehen im
`willkommen`, keiner ist beim Gast einstellbar.

| Schalter | Kommandozeile | Wirkung |
| --- | --- | --- |
| Knappe Munition | `--knapp` | Vorrat ausserhalb des Magazins, Nachschubkisten alle 18 s |
| Einstiegsschutz | `--kein-schutz` schaltet ihn ab | `GEFECHT["schutz"]` Sekunden unverwundbar nach jedem Einstieg |
| Medkits beim Einstieg | `--medkits N` | 0 bis 9, Vorgabe 1 |
| Medkits auf der Karte | `--keine-medkits` schaltet sie ab | sonst alle 12 s eines, hoechstens 4 gleichzeitig |

**Einstiegsschutz.** Gegen Spawnkilling: wer gerade erst eingestiegen ist,
soll nicht von jemandem erledigt werden, der schon zielt. Er ist sichtbar -
ein Ring um die Figur, der mit der Restzeit kleiner wird. **GRUND fuer den
Ring:** ohne ihn sieht man nur, dass Treffer nichts tun, und haelt es fuer
einen Fehler.

Abschaltbar, weil man ihn auf einer kleinen Karte auch ausnutzen kann: man
laeuft geschuetzt ins Gefecht. Bei zweien lohnt sich das Abschalten, bei
sechsen nicht.

**Medkits.** Dieselbe Idee wie die knappe Munition: ohne Nachschub zaehlt,
was man beim Einstieg dabei hat, und ein Treffer wiegt schwerer. Wer
`--medkits 0 --keine-medkits` setzt, spielt eine Runde ohne jede Heilung -
das ist die haerteste Einstellung und fuer `versus` die interessanteste.

Aufheben bleibt bei `MEDKIT["hoechstens"]` (3) gedeckelt, auch wenn man mit
mehr einsteigt.

---

### 7.8 Das Pausenmenue

**FEST.** Esc macht einen Deckel **in** der Szene auf, keine eigene Szene
darueber.

**GRUND.** Eine geschobene Szene haelt das Gefecht an. Beim Gastgeber
heisst das: jeder Gast friert ein, solange einer ins Menue schaut. Hier
laeuft die Welt weiter, nur die eigene Eingabe ist stillgelegt - und der
Deckel ist halb durchsichtig, damit man sieht, dass es weitergeht. Das ist
keine Kosmetik, sondern eine Warnung: wer hier steht, steht auch in der
Welt und kann erschossen werden.

Der Gast hat zwei Eintraege (weiter, gehen). Der Gastgeber stellt alles:

| Eintrag | Wirkt |
| --- | --- |
| SPIELART | ab der naechsten Runde |
| RUNDEN BIS SIEG (versus) | ab der naechsten Runde |
| RUNDE ENDET NACH / BEI | ab der naechsten Runde |
| EINSTIEGSSCHUTZ, MEDKITS, MUNITION KNAPP | ab der naechsten Runde |
| MANNSCHAFTEN EINTEILEN | **sofort** |
| NEUE RUNDE MIT DIESEN REGELN | sofort, setzt alles zurueck |

**Warum die Regeln erst zur naechsten Runde gelten:** mitten im Gefecht
die Spielart zu wechseln hiesse, Fraktionen, Punkte und Einstiegsplaetze
unter laufenden Kugeln umzubauen. Die Mannschaftseinteilung ist die eine
Ausnahme, weil ihr Zweck das Gegenteil ist: der Gastgeber greift ein,
*weil* es gerade ungleich steht.

**FEST: Eintraege, die etwas tun, reagieren nur auf Enter.** Ein Pfeil auf
"GEFECHT VERLASSEN" haette sonst die Runde beendet - im Test gefunden,
bevor es jemandem passiert ist.

Der Neustart geht als Nachricht `neustart` an alle Gaeste. Es ist
dieselbe Nachricht wie das `willkommen`, nur mit `id = -1`: die eigene
Nummer bleibt dann, wie sie war.

---

## 8. Aufhelfen

| Schritt | Was passiert |
| --- | --- |
| Fallen | `am_boden = True`, `lebt` bleibt `True`, Leben auf 0, `boden_rest` laeuft |
| Helfen | Helfer haelt die Nutzentaste in `REVIVE["reichweite"]` (28 px), gleiche Ebene, gleiche Mannschaft |
| Fortschritt | `revive_stand += dt * Anzahl Helfer / revive_dauer` |
| Geschafft | `aufhelfen()`: `REVIVE["danach_leben"]` (40) Leben, `schutz` (2 s) |
| Abgebrochen | `revive_stand` sinkt wieder, `boden_rest` laeuft weiter |
| Zeit um | `Spieler.sterben()` - jetzt richtig tot |

**Zwei Helfer sind doppelt so schnell.** Das belohnt, wenn sich die
Mannschaft sammelt.

**Erst sammeln, dann anwenden.** `_revive` baut zuerst ein Woerterbuch
`{wem: wie viele Helfer}` und wertet es danach aus. Wuerde man beides in
einer Schleife machen, haengt das Ergebnis an der Reihenfolge im
Woerterbuch.

---

## 9. Wellen und Gegner-KI (pve, pvpve)

Ein Gegner aus dem Einzelspieler laeuft immer auf `welt.held` zu. Zu viert
waere das ein Rudel, das geschlossen auf denselben Mann zulaeuft, waehrend
die anderen drei in Ruhe zielen. `KampfGegner` waehlt selbst, nach drei
Regeln:

1. **Naehe zaehlt.** Der naechste ist der wahrscheinlichste.
2. **Gedraenge schreckt ab.** Jeder Gegner, der schon an einem Ziel haengt,
   macht es um `GEGNER_MP["gedraenge"]` (55 %) unattraktiver.
3. **Wer entschieden hat, bleibt dabei** - `ziel_haltezeit` (2.5 s). Ohne
   das wechselt ein Gegner bei jedem Schritt und zappelt auf der Stelle,
   sobald zwei Spieler gleich weit weg sind.

Bewertung (kleiner ist besser):

```
wert = Abstand
     + ebenen_strafe (420)  falls andere Ebene
     + boden_strafe  (900)  falls am Boden
wert *= 1 + Last * gedraenge
```

Wellengroesse:

```
anzahl = grund * (1 + je_welle * (Welle - 1)) * (1 + je_spieler * (Spieler - 1))
```

gedeckelt auf `hoechstens` (40). Ab Welle `brecher_ab` (3) sind
`brecher_anteil` (22 %) davon Brecher.

---

## 10. Darstellung

### 10.1 Der Kreis liegt **im** Boden, nicht darueber

**FEST.** `Renderer.welt_zeichnen()` nimmt einen zusaetzlichen Aufruf
entgegen:

```python
def welt_zeichnen(self, ziel, welt, kamera, alpha, blick_hoehe=None, boden=None)
```

`boden(flaeche, ebene, ecke)` laeuft je Ebene **nach** `ebene_zeichnen` und
**vor** `wesen_zeichnen`. `Gefecht._kreis_zeichnen` haengt sich dort ein
und ruft `Renderer.kreis_zone()`.

**GRUND.** Drei Dinge auf einen Schlag:

1. Die Figuren stehen sichtbar **auf** dem Kreis statt unter einem Schleier.
2. Auf den verkleinerten Tiefenflaechen stimmt der Kreis von selbst - dort
   ist die Flaeche groesser und wird hinterher als Ganzes verkleinert. Der
   Mehrspieler muss von Perspektive nichts wissen.
3. Abdunklung und Dunst der Ebene bekommt er geschenkt: von Ebene 2 aus
   sieht man den Kreis unten liegen, klein und im Dunst, genau wie den
   Boden drumherum.

`kreis_zone()` zeichnet: Flaeche mit `ZONE["fuellung"]` (34) Deckkraft,
pulsender Ring (`ZONE["puls"]`, 0.9 s je Schlag), und den Ladestand als
Bogen, **oben beginnend im Uhrzeigersinn**. Farbe ist die der haltenden
Mannschaft, sonst cremefarben.

### 10.2 Kopfzeile

| Zeile | Wann |
| --- | --- |
| Spielart, Rolle, Adresse | immer, links oben |
| `WELLE n` | mit Gegnern |
| Uhr `m:ss` | ueberall ausser pve |
| `BIS n ABSCHUESSE` / `BIS n TEAMABSCHUESSE` | wenn nach Abschuessen gespielt wird |
| `ROT n : m BLAU` | mit Mannschaften |
| zwei Ladebalken + `ROT HAELT DEN KREIS` / `UMKAEMPFT` | huegel |
| `RUNDE n BIS 3 SIEGEN` / `NAECHSTE RUNDE IN n` / `WARTET AUF MITSPIELER` | versus |

In pve laeuft **keine** Uhr - die Runde endet, wenn alle liegen, eine Uhr
waere eine Zahl ohne Bedeutung.

### 10.3 Ueber den Figuren

Name in der Mannschaftsfarbe, darunter ein Lebensbalken. Am Boden zeigt der
Balken stattdessen den **Aufhelfstand** - wichtiger als das Leben, das
ohnehin null ist - und Helfer sehen `[E]`, aber nur, wenn sie ueberhaupt
helfen duerfen.

---

## 11. Alle Zahlen an einer Stelle

Alle stehen in `config.py`. **Keine Zahl im Code.**

### NETZ

| Name | Wert | Wirkung, wenn man dreht |
| --- | ---: | --- |
| `port` | 50505 | Standardport |
| `hoechstens` | 8 | mehr Gaeste = mehr Verkehr, das Paket waechst linear |
| `puffer` | 65536 | je Leseversuch |
| `hoechstzeile` | 262144 | laenger = Leitung gilt als kaputt (Schutz gegen Speicherfluten) |
| `wartezeit` | 5.0 s | Verbindungsversuch |
| `takt` | 1/60 s | Weltmeldung. Niedriger = ruckeliger beim Gast, sparsamer |
| `eingabe_takt` | 1/60 s | Eingabepakete |
| `namenslaenge` | 10 | die 5x7-Schrift kennt nur Grossbuchstaben |

### GEFECHT

| Name | Wert | Begruendung |
| --- | ---: | --- |
| `team_abschuesse` | 30 | zwei gegen zwei rund sechs Minuten |
| `rundenzeit` | 300 s | fuenf Minuten, eine Runde in einer Pause |
| `abschuesse_ziel` | 20 | pvp ohne Mannschaften |
| `wieder_nach` | 3.0 s | lang genug, dass der Tod weh tut, kurz genug, dass man nicht zusieht |
| `punkt_abschuss` | 1 | |
| `punkt_selbst` | -1 | wer sich selbst erledigt, zahlt drauf |
| `schutz` | 2.0 s | unverwundbar nach dem Einstieg, gegen Spawnkilling |
| `abstand` | 160 px | so weit weg wird eingestiegen |
| `medkit_takt` | 12 s | |
| `medkit_hoechstens` | 4 | |

### TEAMS / ZONE / VERSUS

| Name | Wert | Begruendung |
| --- | ---: | --- |
| `TEAMS["namen"]` | ROT, BLAU | Laenge bestimmt die Anzahl der Mannschaften |
| `ZONE["ebene"]` | 0 | unten, wo alle hinkommen |
| `ZONE["radius"]` | 96 px | sechs Kacheln - gross genug fuer ein Gefecht, klein genug zum Halten |
| `ZONE["bis"]` | 100 | allein rund 14 s |
| `ZONE["je_sekunde"]` | 7.0 | Grundtempo bei Vorsprung 1 |
| `ZONE["je_kopf"]` | 2.5 | Aufschlag je weiterem Kopf Vorsprung |
| `ZONE["hoechstens"]` | 18.0 | auch acht gegen null brauchen noch ueber 5 s |
| `ZONE["verfall"]` | 1.2 | langsam: ein Vorsprung soll etwas wert sein |
| `ZONE["fuellung"]` | 34 | Deckkraft. Hoeher = der Boden verschwindet |
| `ZONE["puls"]` | 0.9 s | ein ruhiger Kreis verschwindet im Boden |
| `VERSUS["runden_bis"]` | 3 | |
| `VERSUS["pause"]` | 5.0 s | |
| `VERSUS["boden_zeit"]` | 20 s | siehe 7.5 |
| `VERSUS["revive_dauer"]` | 4.0 s | siehe 7.5 |

### Einstieg und Heilung (0.17.0)

| Name | Wert | Begruendung |
| --- | ---: | --- |
| `GEFECHT["schutz_an"]` | True | Vorgabe, vom Gastgeber abschaltbar |
| `GEFECHT["start_medkits"]` | 1 | wie im Einzelspieler |
| `GEFECHT["start_medkits_hoechstens"]` | 9 | mehr laesst der Gastgeber nicht zu |
| `GEFECHT["medkits_spawnen"]` | True | abschaltbar, siehe 7.7 |

### RAUCH (0.17.0)

| Name | Wert | Begruendung |
| --- | ---: | --- |
| `radius` | 78 px | eine Tuer und ihr Umfeld, kein halber Raum |
| `dauer` | 14 s | lang genug, um einen Weg zu queren, zu kurz, um eine Stelle dauerhaft zuzustellen |
| `aufbau` | 0.9 s | sie zieht auf, statt dazustehen - wer sie wirft, kommt nicht sofort in Deckung |
| `abbau` | 2.4 s | sie verweht sichtbar, niemand wird ueberrascht |
| `block` | 8 px | Kantenlaenge eines Blocks, ein Viertel einer Kachel |
| `kern` | 0.72 | bis hierhin gilt eine Stelle als verborgen (`welt.verdeckt`) |
| `zackung` | 0.30 | so stark franst der Rand aus. 0 waere ein Kreis |
| `fremde_ebene` | 0.55 | so viel Deckkraft behaelt Rauch einer anderen Etage |

**Blockig, nicht rund.** Die Wand besteht aus Bloecken im Weltraster, alle
voll deckend, in vier Grautoenen. Auf- und Abbau zeigt sich daran, *welche*
Bloecke stehen, nicht daran, wie durchsichtig sie sind. **GRUND:** alles in
diesem Spiel sitzt auf einem Raster; eine weich verlaufende Scheibe faellt
sofort als Fremdkoerper auf - und ein Verlauf machte aus der Sichtwand
einen Schleier, durch den man noch alles sah.

Welche Bloecke stehen, entscheidet eine feste Rechnung aus ihrer Lage.
Dadurch sieht dieselbe Wolke bei Gastgeber und Gast gleich aus, **ohne
dass ein einziger Block uebertragen wird** - im Netz stehen nur Mitte,
Ebene, Radius und Alter.

**Verborgen heisst wirklich verborgen.** Im Kern ist die Figur nicht zu
sehen **und ihr Name auch nicht** (`welt.verdeckt`, gefragt nach der
Ebene des Verborgenen, nicht des Zuschauers). Ohne die Namensregel waere
die Wand wertlos: man saehe die Gestalt nicht mehr, aber ihr Name
schwebte weiter darueber und zeigte genau, wo sie steht.

Die Rauchgranate macht **keinen** Schaden und haelt **keine** Kugel auf.
Wer hindurchschiesst, trifft - er sieht es nur nicht. **GRUND:** Sicht ist
die Waehrung in diesem Spiel; Rauch, der auch noch schuetzt, waere zwei
Sachen auf einmal. Sie fliegt kuerzer als die Sprenggranate (165 statt
260 px): eine Sichtwand, die man quer ueber die Karte setzen kann, nimmt
dem Gegner die Karte statt einer Stelle.

### Waffenzahlen, die sich in 0.17.0 geaendert haben

| Waffe | Was | Vorher | Jetzt | Warum |
| --- | --- | ---: | ---: | --- |
| Brecheisen | Schaden | 46 | 60 | zwei Treffer toeten (2 x 60 > 100) |
| Brecheisen | Takt | 0.40 s | 0.62 s | gab dem Schlag Gewicht; seit 0.18.0 gibt es ohnehin keine Unverwundbarkeit mehr, die Schlaege schlucken koennte |
| Schrot | Streuung | 7.5 Grad | 5.5 Grad | trifft auf halber Zimmerbreite mit mehr als zwei Kuegelchen |
| Schrot | Reichweite | 210 px | 300 px | bleibt die Waffe fuer kurze Wege, ist aber nicht mehr auf Armlaenge beschraenkt |
| Scharfschuetze | Reichweite | 900 px | 2200 px | weiter, als man sehen kann: das Bild ist 640 px breit, die Karte diagonal rund 1600 |
| Ziellinie | Weite | 900 px | 2200 px | sie soll zeigen, wo der Schuss hingeht, und nicht vorher aufhoeren |

**Das Brecheisen ist der Fall, an dem man sieht, wie zwei Zahlen
aneinanderhaengen.** Mehr Schaden allein haette wenig gebracht: bei 0.40 s
Takt lief jeder zweite Schlag in die Unverwundbarkeit des Getroffenen, man
brauchte drei Schlaege fuer zwei Treffer. Erst der langsamere Takt macht
aus "zwei Treffer toeten" auch "zwei Schlaege toeten".

### REVIVE (pve)

`boden_zeit` 45 s, `dauer` 3 s, `reichweite` 28 px, `danach_leben` 40,
`schutz` 2 s, `kriechen` 0.35.

### MUNITION (Schalter `--knapp`)

Vorrat: Repetierer 70, Sturm 150, Schrot 32, Scharf 20, Granate 4,
Brecheisen 0. Kiste alle 18 s, hoechstens 3 gleichzeitig, eine Kiste gibt
45 % des vollen Vorrats.

### Was ich beim naechsten Mal zuerst drehen wuerde

1. `ZONE["radius"]` - 96 px ist auf der Testkarte richtig. Auf einer
   groesseren Karte muss er mitwachsen, sonst findet ihn niemand.
2. `VERSUS["boden_zeit"]` - 20 s fuehlt sich bei zwei gegen zwei richtig
   an, bei vier gegen vier wahrscheinlich zu lang.
3. `GEFECHT["team_abschuesse"]` - haengt stark an der Spielerzahl. Besser
   waere `10 * Spieler`.

---

## 12. Fehlerquellen - was wirklich passiert ist

Dieser Abschnitt ist der wichtigste. Jeder Punkt ist ein Fehler, der
aufgetreten und behoben wurde. Wer den Mehrspieler neu baut, baut sie sonst
alle nochmal.

### 12.1 Einzelne Tastendruecke gehen verloren (schwer)

**Symptom.** Nachladen, Heilen, Ziellinie und Waffenwechsel funktionieren
beim Gast "manchmal". Die Hoehenebenen lassen sich nicht scrollen.

**Ursache.** `gedrueckt()` ist genau **ein Bild** lang wahr. Das Spiel
rechnet 120 Mal je Sekunde, gesendet wird 60 Mal. Wer direkt beim Senden
abfragt, erwischt den Druck nur, wenn er zufaellig im richtigen Bild lag -
statistisch die Haelfte, gefuehlt seltener.

**Behebung.** `knoepfe_sammeln()` laeuft in **jedem** Bild und legt
einmalige Druecke in `self._knoepfe` ab. Das Paket raeumt die Menge leer.
Zusaetzlich wird **sofort** gesendet, wenn etwas wartet:

```python
eilig = bool(self._knoepfe) or self._waffe_wunsch >= 0
if eilig or self._seit_senden >= K.NETZ["eingabe_takt"]:
```

**Merke.** Alles, was einmalig ist, muss zwischen zwei Paketen gesammelt
werden. Alles, was gehalten wird (`feuert`, `nutzen`), darf direkt
abgefragt werden.

### 12.2 `if k.hilft:` - die Null ist falsch (schwer)

**Symptom.** Dem Gastgeber kann niemand aufhelfen. Allen anderen schon.

**Ursache.** Der Gastgeber ist **immer** Spieler 0, und `0` ist in Python
falsch. `if k.hilft:` war fuer ihn nie wahr.

**Behebung.** `hilft = None` statt `hilft = 0`, Abfrage
`if k.hilft is not None:`.

**Merke.** Spielernummern, Ebenen, Indizes: nie auf Wahrheit pruefen,
immer auf `is not None`. Dieser Fehler ist im Test nur aufgefallen, weil
ausdruecklich **dem Gastgeber** aufgeholfen wurde.

### 12.3 Alle Gegner laufen auf denselben Mann

**Symptom.** Eine frische Welle laeuft geschlossen auf einen Spieler zu.

**Ursache.** Die Last wird einmal je Schritt gezaehlt. Beim ersten Waehlen
ist sie ueberall null, also waehlen alle im selben Schritt dasselbe Ziel.

**Behebung.** Die eigene Wahl sofort in `gegnerlast` mitzaehlen, damit der
naechste Gegner sie schon sieht. Messbar: `{1: 6}` wurde zu `{0: 3, 1: 3}`.

### 12.4 Der Gast sah die halbe Runde nicht

Beim ersten Bauen fehlten dem Gast: Granaten, Munitionsanzeige, Treppen
nach oben, sichtbares Nachladen. Ursache war jedes Mal dieselbe: **das Feld
war nicht in der Weltmeldung.** Ein Gast rechnet nichts - was nicht
geschickt wird, gibt es fuer ihn nicht.

**Merke.** Neues Spielerfeld = neue Zeile in `_weltmeldung` **und** in
`_welt_uebernehmen`. Beide, sonst ist es still kaputt. Dieselbe Falle gilt
fuer die neuen Felder `tm`, `ra`, `tp`, `zs`, `zh`, `rn`, `rp`, `st`.

### 12.5 Der Kreis war unsichtbar, obwohl er gezeichnet wurde

**Symptom im Test.** "Kreis in der Mitte" schlug fehl, obwohl 7500
Bildpunkte anders waren.

**Ursache.** Die Figur stand genau auf der Mitte und verdeckte den Kreis
dort - weil der Kreis **unter** den Figuren liegt. Der Test war falsch,
nicht der Code.

**Merke.** Einen Kreis nie in seinem Mittelpunkt pruefen. Der Test misst
jetzt bei halbem Radius (anders) und ausserhalb (gleich), und prueft die
Mitte ausdruecklich auf **gleich** - das belegt, dass die Figur darauf
steht.

### 12.6 Aufhelfen ueber die Mannschaftsgrenze

**Symptom (gefunden, bevor er auftrat).** In versus koennte man den Gegner
aufheben, den man gerade umgelegt hat - und die Runde nie beenden.

**Behebung.** `_darf_helfen()` sitzt an **drei** Stellen: bei der Suche
(`_wem_helfen`), bei der Anzeige (`[E]`) und implizit in der Abrechnung.

### 12.7 Versus allein: Runde nach Runde in Sekunden

**Symptom.** Der Gastgeber allein gewinnt das Gefecht, bevor der erste Gast
verbunden ist.

**Ursache.** "Eine Mannschaft hat niemanden mehr auf den Beinen" ist wahr,
solange die Mannschaft leer ist.

**Behebung.** `_beide_besetzt()`. Keine Runde faengt an, solange eine
Mannschaft leer ist.

### 12.8 Zahlen aus dem Netz

Alles, was von aussen kommt, ist ein **Vorschlag**. `_anwenden()` kuerzt
den Richtungsvektor auf Laenge 1, prueft den Waffenindex gegen die Liste
und faengt jede Umwandlung ab. `_liste_uebernehmen()` laesst die Laenge der
eigenen Listen unveraendert - eine zu kurze oder falsch gefuellte Liste aus
dem Netz darf den Punktestand nicht kippen. Eine kaputte JSON-Zeile wirft
niemanden raus, sie wird uebersprungen.

### 12.9 Kein Ton, kein Ruckeln, kein Blut (schwer, 0.17.0)

**Symptom.** Im ganzen Mehrspieler war nichts zu hoeren, bei Gastgeber wie
Gast. Kein Schuss, keine Explosion, kein Medkit.

**Ursache.** `Welt.klang` ist in `world.py` eine **leere Methode**, genau
wie `ruckeln`, `blutfleck`, `brandfleck` und `kurz_langsam`. Der
Einzelspieler haengt in `play.neu_aufbauen()` die echten Empfaenger daran.
Das Gefecht tat es nie - also lief alles ins Leere, ohne eine einzige
Fehlermeldung.

**Behebung.** `Gefecht._welt_verdrahten()`, aufgerufen im Baukasten.
**Ausser `kurz_langsam`:** die Zeitlupe beim Toeten wuerde beim Gastgeber
die ganze Welt verlangsamen, also auch die Runde aller Gaeste. Ein
Abschuss darf nicht die Runde der anderen bremsen.

**Merke.** Ein leerer Haken meldet sich nie. Wer eine zweite Spielszene
neben `play.py` baut, geht dessen Aufbau Zeile fuer Zeile durch und fragt
bei jeder: braucht meine Szene das auch?

### 12.10 Der Sturztod als Teleport (schwer, 0.17.0)

**Symptom.** Wer eine Ebene hinuntersprang, stand ploetzlich irgendwo
anders auf der Karte. Ohne Todesbild, ohne Wartezeit. Bei Gastgeber und
Gast gleichermassen.

**Ursache.** In `_tote_abrechnen` hing alles an `if k.toeter is not None`:
Todeszaehler, Punkte **und** `wieder_in`. Ein Sturz toetet ohne Toeter
(`aufschlag()` ruft `schaden(..., von=None)`). Also blieb `wieder_in` auf
0.0 stehen, war im selben Bild schon abgelaufen, und der Wiedereinstieg
setzte die Figur sofort auf einen frischen Einstiegsplatz - im Test
gemessen 244 Pixel weit.

**Behebung.** Ein eigenes Merkmal `abgerechnet` am Kaempfer. Jeder Tod
wird genau einmal verbucht, mit oder ohne Toeter; ein Sturztod kostet
ausserdem einen Punkt, wie das Selbsterledigen.

**Merke.** Sobald es einen Tod ohne Verursacher gibt, darf kein Zaehler
mehr am Verursacher haengen. Das Gleiche gilt fuer Ertrinken, Feuer, Sturz
aus der Karte - alles, was spaeter dazukommt.

### 12.11 Die Ziellinie des Gastes zeigte auf seinen Einstieg (0.17.0)

**Symptom.** Beim Gast zeigte die Ziellinie immer auf die Stelle, an der er
eingestiegen war, egal wohin er die Maus hielt. Beim Gastgeber stimmte sie.

**Ursache.** `ziel` steht in **keiner** Weltmeldung - es ist eine Eingabe,
keine Weltlage. Der Gast simuliert nichts, also blieb `ziel` auf dem Wert
aus dem Baukasten: `pos + (1, 0)`, dem Einstiegspunkt.

**Behebung.** `_eigenes_zielen()`, einmal je Bild, aus der eigenen Maus -
nicht aus dem Netz. Das ist zugleich das Richtigere: Zielen soll ohne
Verzoegerung folgen. Geschossen wird weiterhin nur dort, wo der Gastgeber
rechnet; die Linie ist Anzeige, keine Entscheidung.

**Merke.** Die Trennung heisst nicht "der Gast zeigt nur an", sondern:
**Weltlage kommt vom Gastgeber, eigene Eingabe gehoert dem Gast.** Was nur
anzeigt und nichts entscheidet, darf und soll lokal sein.

### 12.12 Granaten prallten an Loechern ab (0.17.0)

**Symptom.** Eine Granate, die ueber eine Kante geworfen wurde, blieb oben
liegen und zuendete eine Etage ueber dem, den sie treffen sollte.

**Ursache.** `welt.bewegen` behandelt Loecher als Wand fuer alles, was das
Klassenmerkmal `faellt` nicht gesetzt hat - und das hatte nur `Spieler`.

**Behebung.** `Granate.faellt = True`, dazu ein `loch_unter`-Test im
Schritt und ein eigenes `aufschlag()` **ohne** Sturzschaden: das geerbte
haette der Granate Fallschaden gegeben, sie waere tot gewesen und haette
nie gezuendet. Der Zuender wartet ausserdem, bis sie liegt, sonst kaeme
der Knall auf der Zielebene an, waehrend sie im Bild noch faellt.

**Merke.** `faellt` ist das Merkmal, das ueber Loecher entscheidet. Alles
Neue, das hinunterfallen koennen soll, braucht es - und dann auch ein
`aufschlag()`, das zu ihm passt.

### 12.14 Unverwundbarkeit nach jedem Treffer (schwer, 0.18.0)

**Symptom.** Wer beschossen wurde, blinkte nach jedem Schuss kurz wie
frisch eingestiegen. Und eine Schrotladung tat kaum etwas.

**Ursache.** `Spieler.schaden` setzte bei **jedem** Treffer
`unverwundbar = 0.6`. Von sieben Schrotkugeln zaehlte damit genau eine -
die erste. Dasselbe traf den Sturz: der Fallschaden machte fuer eine halbe
Sekunde unverwundbar.

**Behebung.** Ersatzlos gestrichen. Unverwundbarkeit gibt es nur noch nach
dem Einstieg, und nur wenn der Gastgeber sie eingeschaltet hat.

**Was das an der Balance aendert:** die Schrotflinte macht auf kurze
Entfernung jetzt wirklich ihre 91 Schaden statt 13. Sie toetet nah in
einem Schuss. Das ist gewollt - eine Schrotflinte, von der sechs von
sieben Kugeln folgenlos bleiben, ist keine.

### 12.15 Der Laserpointer, der nicht wiederkam (0.18.0)

**Symptom.** "Mein Laserpointer ist auf einmal verschwunden und nicht
mehr wiedergekommen."

**Ursache.** Zielhilfen gehoeren zu der Ebene, auf der die Figur steht,
und werden nur gezeichnet, solange man diese auch anschaut. Wer einmal am
Mausrad gedreht hatte - oft versehentlich - schaute fuer den Rest der
Runde eine Etage daneben. Nichts holte ihn zurueck, und der Hinweis dazu
konnte von einem anderen Hinweis verdraengt werden.

**Behebung.** Die verschobene Ansicht kommt nach `GEFECHT["blick_zurueck"]`
Sekunden von selbst zurueck, und ihr Hinweis hat Vorrang vor allen
anderen.

**Merke.** Ein Zustand, in den man mit einer Taste kommt und aus dem nur
dieselbe Taste wieder herausfuehrt, ist eine Falle - besonders, wenn er
etwas ausblendet, das man dauernd braucht.

### 12.16 Kleinere Fallen

| Falle | Was passiert |
| --- | --- |
| `welt.wesen` beim Gast vergessen zu setzen | Der Renderer zeichnet nichts; der Gast sieht eine leere Karte. |
| `welt.neue` nicht leeren | Wesen sammeln sich beim Gast an und werden nie weggeraeumt. |
| `_beute_legen` ohne Obergrenze | Nach zehn Minuten liegt die Karte voller Medkits. |
| Ein Test, der `_gedrueckt` gesetzt laesst | Ein Schalter kippt mehrfach - Testfehler, nicht Codefehler. |
| `unverwundbar` nach `aufhelfen()` | Schaden im Test kommt nicht an. Erst `unverwundbar = 0.0` setzen. |
| Ein einzelner `FIXED_DT`-Schritt fuer `rest = 0.01` | Zu kurz. Restzeit knapp unter **einen** Schritt setzen. |
| `Spiel()` ohne Seed im Test | Sporadische Fehlschlaege. Tests geben einen festen Seed. |

### 12.17 Was **nicht** kaputt war

Zwei Dinge sahen nach Fehlern aus und waren keine: die unterschiedlichen
Blutflecken auf beiden Rechnern (Kosmetik wird nicht uebertragen, siehe
4.3) und dass 2 gegen 1 im Kreis nicht schneller laedt als 1 gegen 0 (der
Vorsprung zaehlt, nicht die Kopfzahl, siehe 7.6).

Das gemeldete "etwas laggy" war dagegen **echt**: `NETZ["takt"]` stand auf
1/30, der Gast bekam also 30 Stellungen je Sekunde und zeichnete 120 Bilder
dazwischen. Auf 1/60 erhoeht, dazu `eingabe_takt` eingefuehrt - seitdem
weg. Wer die Zahl senkt, holt sich das Ruckeln zurueck.

---

## 13. Was fehlt

**OFFEN**, bewusst, weil es ein Test war:

* **Keine Vorhersage beim Gast.** Ueber das Internet unspielbar. Wer das
  will, braucht Eingabepuffer, Rueckrechnung und Korrektur - das ist mehr
  Arbeit als der ganze jetzige Mehrspieler.
* **`NETZ["stumm_nach"]` wird nicht benutzt.** Ein Gast, dessen Rechner
  einfach stehen bleibt, faellt erst auf, wenn TCP die Leitung abbricht.
  Die Zahl steht bereit, die Pruefung fehlt.
* **Keine Lobby.** Die Spielart wird beim Start gewaehlt und laeuft bis zum
  Ende. Kein Mannschaftswechsel von Hand, kein Ausbalancieren im Spiel.
* **Kein Wiedereinstieg nach Verbindungsabbruch.** Wer rausfliegt, ist weg;
  beim Wiederverbinden bekommt er eine neue Nummer und faengt bei null an.
* **Keine Karte fuer Mannschaften.** `testkarte()` hat keine getrennten
  Einstiegsseiten. `_einstiegsort` gleicht das aus, ersetzt aber keine
  Karte mit zwei Basen.
* **Der Kreis liegt immer in der geometrischen Mitte.** Keine Pruefung, ob
  dort Boden ist. Bei 96 px Radius ist immer genug frei - auf einer
  anderen Karte muss man das pruefen.
* **Kein Ton fuer Mannschaftsereignisse.** Kein Klang beim Erobern, kein
  Rundenende-Signal.

---

## 14. Wo das alles liegt

| Zweig | Version | Inhalt |
| --- | --- | --- |
| `main` | 0.15.0 | **ohne** Mehrspieler. Die zwei Mehrspieler-Commits wurden zurueckgenommen. |
| `multiplayer-test` | 0.16.0 | **mit** Mehrspieler, vollstaendig, dieser Stand. |

**Versionsnummern.** 0.15.0 gehoert dem Hauptzweig, 0.16.0 diesem. Keine
Nummer wird zweimal vergeben, auch nicht ueber Zweige hinweg - siehe
README, Abschnitt "Versionsnummern".

**Starten:**

```
python -m dustfront --host --name MEISTER --modus huegel --ende zeit --wert 600
python -m dustfront --join 192.168.1.7:50505 --name GAST
python -m dustfront --bestenliste
```

`--modus` ist einer von `pvp pve pvpve team versus huegel`, `--ende` ist
`zeit` oder `abschuesse`, `--knapp` begrenzt die Munition. Ohne
Kommandozeile: `LAN-GASTGEBER.bat` bzw. `.command` fragt alles ab.

---

## 15. Wiederaufbau, Schritt fuer Schritt

Die Reihenfolge ist wichtig: jeder Schritt ist fuer sich lauffaehig und
pruefbar. Wer sie umstellt, sitzt vor einem Stapel, der nicht laeuft und
nicht sagt, woran es liegt.

**Schritt 1 - `netz.py`.** `Leitung` mit Puffer und Zeilenschnitt,
`Gastgeber` (annehmen, holen, gegangen, an_alle, an_einen), `Gast`, dazu
`adresse_lesen`, `eigene_adresse`, `name_saeubern`. Weiss nichts vom Spiel.
*Pruefbar:* zwei Steckdosen auf `127.0.0.1`, eine Nachricht hin und
zurueck.

**Schritt 2 - `config.py`.** `NETZ`, `MODI` mit den fuenf Schaltern
(`gegner`, `beute`, `revive`, `teams`, `runden`, `zone`), `GEFECHT`.
*Pruefbar:* alle Spielarten haben alle Schluessel.

**Schritt 3 - `Kaempfer` und `Gefecht`, nur pvp.** Fraktion je Spieler,
`_dazu`, `_einstiegsort`, `_meine_eingabe`, `_anwenden`, `_weltmeldung`,
`_welt_uebernehmen`, `knoepfe_sammeln` (siehe 12.1!). **Und
`_welt_verdrahten()`** - Ton, Ruckeln, Blut- und Brandflecken, siehe 12.9;
ohne das laeuft alles davon still ins Leere. *Pruefbar:* zwei Szenen ueber
echte Steckdosen, beide sehen einander, einer trifft den anderen, und man
hoert es.

**Schritt 4 - Namen, Punkte, Bestenliste, Endtafel.** *Pruefbar:* Runde
endet nach Zeit und nach Abschuessen.

**Schritt 5 - Zeichnen beim Gast.** `_fremdes_zeichnen` fuer Beute,
Gegner, Geschosse, Granaten. Zielhilfen und Ziellinie nicht vergessen -
`zeichnen()` muss **beide** rufen, und `_eigenes_zielen()` gehoert dazu
(12.11). *Pruefbar:* der Gast sieht eine fliegende Granate, und seine
Ziellinie folgt seiner Maus.

**Schritt 6 - pve.** `REVIVE`, `Kaempfer.sterben` ohne Tod, `_revive`
(erst sammeln, dann anwenden), `KampfBeute`, `KampfGegner` mit eigener
Zielwahl (12.3), `_wellen`. *Pruefbar:* dem **Gastgeber** aufhelfen (12.2),
Gegner verteilen sich.

**Schritt 7 - pvpve und knappe Munition.** `MUNITION`, Vorrat,
Munitionskisten, Nachladen gegen den Vorrat verrechnen.

**Schritt 8 - Mannschaften.** `TEAMS`, `team` in `MODI`, `_team_fuer`,
`_fraktion_fuer` mit Team, `_einstiegsort` mit Team, Teamkonto in
`_tote_abrechnen`, `tm` in der Weltmeldung, Farben in `_farbe_fuer`,
Teamkopf in der Anzeige. *Pruefbar:* zwei Mannschaften, zwei Fraktionen,
ein Abschuss zaehlt fuer die Mannschaft.

**Schritt 9 - versus.** `VERSUS`, `runden`-Schalter, `raus`, `_runden`,
`_runde_aufbauen`, `_beide_besetzt` (12.7), `_darf_helfen` (12.6), eigene
Boden- und Aufhelfzeiten am `Kaempfer`. *Pruefbar:* Runde geht an die
Mannschaft, die noch steht; nach der Pause stehen alle wieder mit vollem
Magazin.

**Schritt 10 - huegel.** `ZONE`, `zone_mitte` aus den Kartenmassen,
`in_der_zone`, `_zone`, `boden=`-Aufruf in `welt_zeichnen`,
`Renderer.kreis_zone`, Balken in der Kopfzeile. *Pruefbar:* der Kreis ist
im Bild nachweisbar (12.5), Gleichstand laedt nicht, der volle Kreis
beendet das Gefecht.

**Schritt 11 - Startdateien und Schalter.** `--host`, `--join`, `--modus`,
`--ende`, `--wert`, `--knapp`, `--kein-schutz`, `--medkits`,
`--keine-medkits`, `--bestenliste`; die vier Startdateien. Alle Schalter
gehoeren ins `willkommen`, sonst spielt der Gast nach anderen Regeln.

**Schritt 12 - Tests.** Alles oben Genannte gehoert in
`tests/test_spiel.py`, mit **echten** Steckdosen auf `127.0.0.1`. Was dort
nicht durchgeht, geht auch im LAN nicht durch.

---

## 16. Was die Tests pruefen

Im Abschnitt "LAN-Gefecht" von `tests/test_spiel.py`, rund 60 Pruefungen.
Jede Zeile hier ist eine Zeile dort.

**Verbinden:** Gastgeber macht auf, Gast verbindet sich, beide kennen
beide, Namen kommen unveraendert an, Positionen stimmen ueberein, jeder hat
eine eigene Fraktion, zwei Spieler treffen sich wirklich, ein Gast, der
abbricht, reisst den Gastgeber nicht mit.

**Gast sieht alles:** Medkits erscheinen und sind nutzbar, Ziellinie und
Zielhilfen, Mausrad scrollt die Ebenen, Granaten sind sichtbar, Munition
wird angezeigt, Treppen funktionieren, Nachladen ist zu sehen.

**Spielarten:** Spielart und Endbedingung kommen beim Gast an; pvp endet
bei der gewaehlten Abschusszahl; pve hat eine Fraktion, Wellen starten und
wachsen mit der Spielerzahl, Gegner verteilen sich, Aufhelfen funktioniert
**auch beim Gastgeber**, pve endet wenn alle liegen, jede Welle hilft
allen auf; knappe Munition nimmt nur, was der Vorrat hergibt.

**Mannschaften:** Gastgeber in Mannschaft 0, der Neue in die kleinere,
zwei Mannschaften sind zwei Fraktionen, gleiche Mannschaft gleiche
Fraktion, Mannschaft kommt beim Gast an, ein Abschuss zaehlt fuer die
Mannschaft und den Schuetzen, team endet bei der Teamabschusszahl, der
Gast erfaehrt den Sieger.

**versus:** kuerzere Bodenzeit und laengeres Aufhelfen, dem Gegner hilft
niemand, dem eigenen Mann schon, am Boden ist die Runde nicht entschieden,
abgelaufene Bodenzeit heisst raus, die Runde geht an die Mannschaft die
noch steht, Pause laeuft, nach der Pause neue Runde mit vollem Magazin und
Abstand, genug Rundensiege beenden das Gefecht, allein faengt keine Runde
an.

**huegel:** Kreis liegt in der Kartenmitte, der Gast rechnet dieselbe
Mitte, drinnen/draussen/falsche Ebene, allein laedt es, Gleichstand laedt
nicht, Vorsprung 2 laedt schneller, Obergrenze haelt, Ladestand kommt beim
Gast an, voller Kreis beendet das Gefecht, **der Kreis ist im Bild
nachweisbar** und die Figur steht darauf.

**Die gemeldeten Fehler aus 0.17.0:** beide Seiten haben einen echten
Tonausgang, spueren Treffer in der Kamera und hinterlassen Flecken, aber
keine Zeitlupe; ein Sturztod versetzt niemanden, zaehlt trotzdem als Tod
und wartet die uebliche Zeit ab; die Ziellinie des Gastes trifft genau den
Mauszeiger und dreht die Figur sofort mit; Rauch und fallende Granaten
kommen beim Gast an und verschwinden dort auch wieder.

**Die neuen Schalter:** Einstiegsschutz an und aus, Zahl der Medkits beim
Einstieg, Medkit-Nachschub an und aus - jeder davon beim Gastgeber gesetzt
und beim Gast nachgeprueft.

**Granate und Rauch (im Spielkern, ohne Netz):** eine Granate rollt ueber
die Kante, faellt weich (unter 8 px je Bild) und zuendet erst unten; eine
Rauchgranate macht genau eine Wolke, die aufzieht, im Bild wirklich
verdeckt - auf ihrer Ebene und von der Ebene darueber - und nach ihrer
Zeit verschwindet.

**Balance, gemessen statt geglaubt:** zwei Brecheisenschlaege toeten, einer
nicht, und der Takt liegt ueber der Unverwundbarkeit; Schrot trifft auf 260
px und nah trotzdem haerter; der Scharfschuetze trifft auf 900 px, weiter
als das Bild breit ist.

**In `tests/test_menues.py`:** Bestenliste anlegen, eintragen, sortieren,
Neustart ueberleben, kaputte Datei abfangen, Namen saeubern, Adressen
zerlegen.

---

## 17. Der eine Satz zum Merken

Der Gastgeber rechnet, der Gast zeigt an. Alles, was der Gast sehen soll,
muss in der Weltmeldung stehen - und alles, was nur einen Augenblick lang
wahr ist, muss gesammelt werden, bevor es ins Paket geht.
