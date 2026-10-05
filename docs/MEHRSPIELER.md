# DUSTFRONT - Der Mehrspieler, vollstaendig

**Was das hier ist.** Die komplette Beschreibung des LAN-Mehrspielers, wie
er auf dem Zweig `multiplayer-test` in Version 0.19.1 steht: Aufbau,
Protokoll, alle sechs Spielarten, jede Zahl mit Begruendung, jeder Fehler,
der beim Bauen aufgetreten ist, und die Reihenfolge, in der man das Ganze
wieder aufbaut.

**Warum es das gibt.** Der Mehrspieler war ein Test und ist fertig. Der
Hauptzweig geht **ohne** ihn weiter (dort ist er aus der Historie
herausgenommen, siehe Abschnitt 14). Dieses Dokument ist die Bauanleitung
fuer den Tag, an dem er zurueckkommen soll.

**Fuer wen.** Fuer Der Meister, und fuer jede Claude-Instanz, die den Satz
hoert: *"bau mal wieder Mehrspieler ein wie in Version 0.19.1"*. Wer das
liest, braucht ausser dem Spielkern nichts weiter zu wissen.

**Stand beim Schreiben:** Version 0.19.1, PRE-ALPHA, Zweig
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
| `dustfront/upnp.py` | ~250 | Der Weg durch den Router, fuer Runden ueber das Internet. Weiss nichts vom Spiel. |
| `dustfront/bestenliste.py` | ~150 | MVP-Punkte und Auszeichnungen ueber alle Runden im Benutzerordner. |
| `dustfront/regeln.py` | ~380 | Seit 0.27: jede Regel einer Runde einmal - Name, Werte, wann sie gilt (12b). |
| `dustfront/lobby.py` | ~690 | Seit 0.27: Lobby, Rundenplan und die Tafel dazu (12b). |
| `dustfront/anzeige.py` | ~530 | Seit 0.27: die Anzeige im Gefecht (12b). |
| `dustfront/wege.py` | ~350 | Seit 0.27: Wegenetz ueber Treppen und Rampen fuer die Gegner (12b). |
| `dustfront/config.py` | +150 | `NETZ`, `MODI`, `TEAMS`, `ZONE`, `VERSUS`, `GEFECHT`, `REVIVE`, `WELLEN_MP`, `GEGNER_MP`, `MUNITION`. |

Dazu: der Einstieg ueber das Hauptmenue (`DUSTFRONT.bat/.command`),
Schalter in `main.py`, die
Lobbysuche (`lan.py`), das Umsteigen zwischen Lobbys (`sitzung.py`, beide
12g) und die Pruefungen im Abschnitt "LAN-Gefecht" von
`tests/test_spiel.py`.

**Sechs Spielarten:**

| Schluessel | Name | Gegner | Spieler treffen sich | Aufhelfen | Mannschaften | Endet durch |
| --- | --- | --- | --- | --- | --- | --- |
| `pvp` | PVP | nein | ja | nein | nein | Zeit oder Abschuesse |
| `pve` | PVE | ja | nein | ja | nein | alle liegen am Boden |
| `pvpve` | PVPVE | ja | ja | nein | nein | Zeit oder Abschuesse |
| `team` | TEAM | nein | ja | nein | ja | Zeit oder Teamabschuesse |
| `versus` | VERSUS | nein | ja | ja | ja | Rundensiege (Zeit als Notbremse) |
| `huegel` | HUEGEL | nein | ja | nein | ja | voller Kreis (Zeit als Notbremse) |

Dazu seit 0.27 die **Lobby** (`lobby`): keine waehlbare Spielart, sondern
der Ort vor und zwischen den Runden (12b).

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

**Seit 0.27** stellt der Gastgeber die **Haltezeit** ein (10 bis 180 s,
Vorgabe 15; allein und ohne Gegenwehr gerechnet) und ob der Fortschritt
**verfaellt**. Rate und Verfall werden aus der Haltezeit hochgerechnet
(`zone_faktor`), im selben Verhaeltnis - sonst waere bei drei Minuten ein
kurzer Ausfall mehr wert als eine Minute im Kreis. Gemessen: 15,1 s bei
15, 60,0 s bei 60.

---

### 7.7 Was der Gastgeber sonst noch stellt

**Seit 0.27 steht jede Regel in `regeln.py`** und wird in der Lobby auf
einer Tafel eingestellt, nicht mehr im Terminal (12b). Die Kommandozeile
geht weiter und belegt die erste geplante Runde vor. Neu dazu:
SCHWIERIGKEIT und BOSSE (alles mit Wellen), EINES FUER ALLE (ein Loadout
des Gastgebers fuer jeden), HALTEZEIT und VERFALL (huegel), HOECHSTDAUER
(versus, huegel).

Die Schalter von 0.19, die zu jeder Spielart gehoeren. Alle stehen im
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
laeuft die Welt weiter, nur die eigene Eingabe ist stillgelegt - und das
Gefecht bleibt rechts neben der Spalte sichtbar. Das ist keine Kosmetik,
sondern eine Warnung: wer hier steht, steht auch in der Welt und kann
erschossen werden.

**Aussehen (seit 0.32, nach Helldivers 2).** Eine dunkle Spalte am
linken Rand, die Eintraege klappen nacheinander von links auf (je 30 ms
versetzt, `ui.aufklappen`), rechts eine Tafel: Spielart, Karte, Spieler,
Zeit oder Punkte, **die naechste Runde**, beim Gastgeber die Adresse, und
darunter in einem Satz, was der gewaehlte Eintrag tut. Das Pausenmenue im
Einzelspieler (`menues.Pause`) sieht genauso aus (`ui.spalteneintrag`).

**Maus.** Zeigen waehlt, Linksklick loest aus, Rechtsklick geht zurueck
wie Esc, das Rad blaettert. Im Menue gehoert die Maus allein dem Menue:

* kein Zoom am Rad,
* **kein Zielen** - das Ziel bleibt, wo es beim Aufmachen war
  (`_ziel_zuletzt`). Vorher drehte sich die Figur fuer alle sichtbar mit,
  waehrend man ueber die Eintraege fuhr;
* **kein Schuss nach WEITER**: der Klick auf WEITER haelt die linke
  Taste noch, wenn das Menue zugeht. `_feuer_sperre` haelt das Feuer
  zurueck, bis beide Maustasten einmal oben waren.

**Eintraege.** Seit 0.32 nur noch Taten, keine Regelzeilen mehr. Bis dahin
stand beim Gastgeber jede Regel der Runde hier, beim Huegel neunzehn
Zeilen - dieselben, die auch die Rundentafel stellt. Jetzt stellt man die
naechste Runde an einer Stelle ein:

| Eintrag | Wer | Wirkt |
| --- | --- | --- |
| WEITER | alle | |
| RUNDE STARTEN (MIT / OHNE KOSMETIK) | Gastgeber, Lobby | sofort |
| NAECHSTE RUNDE EINSTELLEN / ANSEHEN | alle | oeffnet die Tafel (12b) |
| RUNDE NEU STARTEN | Gastgeber, Runde | sofort, setzt alles zurueck |
| MANNSCHAFTEN | Gastgeber, Teams | **sofort** |
| AUSRUESTUNG, KONTO, EINSTELLUNGEN | alle | Szene darueber |
| ANDERER LOBBY BEITRETEN | Lobby | Lobbysuche (12g) |
| LOBBY / GEFECHT VERLASSEN | Gast | in die eigene Lobby (12g) |
| GEFECHT VERLASSEN | Gastgeber, Runde | alle zurueck in die Lobby |
| SPIEL BEENDEN | alle | zu, bzw. zurueck ins Hauptmenue |

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

### 7.9 Ueber das Internet

**FEST.** `--online` aendert am Spiel **nichts**. Es ist dieselbe Leitung,
dasselbe Protokoll, derselbe autoritative Gastgeber - nur von weiter her.
Der einzige Unterschied liegt davor: der Port muss durch den Router.

Dafuer gibt es genau drei Wege, und nur zwei davon sind ohne eigenen
Server zu haben:

| Weg | Geht das? |
| --- | --- |
| Von Hand im Router freigeben | Immer - aber jeder muss es selbst tun |
| **UPnP**: der Router macht es auf Bitte selbst | Oft. `dustfront/upnp.py` |
| Server in der Mitte, der beide verbindet | Ueberall - braucht einen Rechner, der laeuft. **Gibt es hier nicht.** |

Also UPnP mit Handarbeit als Rueckfall. Drei Schritte, alle mit
Bordmitteln: M-SEARCH per UDP an 239.255.255.250:1900, die genannte
Beschreibung als XML holen, dann `AddPortMapping` per SOAP. Dazu
`GetExternalIPAddress` - die oeffentliche Adresse kommt damit **vom
Router**, nicht von einer fremden Seite im Netz.

**Jeder Fehler endet in upnp.py**, nicht im Gefecht: kein Router,
abgelehnte Freigabe, Zeitueberschreitung - die Runde laeuft trotzdem, nur
eben im eigenen Netz. Und die Freigabe wird beim Beenden wieder
zurueckgenommen; wer das vergisst, hinterlaesst eine offene Stelle bis zum
naechsten Neustart des Routers.

**Kennwort.** Ein Port im Internet steht jedem offen, der die Adresse
kennt. `--passwort` prueft im `hallo`; wer nicht passt, bekommt
`abgelehnt` und die Leitung wird geschlossen, ohne dass ein Platz belegt
oder ein Name uebernommen wird. Das Kennwort wird wie ein Name gesaeubert
(Grossbuchstaben, Ziffern, `-` und `_`), damit man es am Telefon vorlesen
kann.

**OFFEN, und das ist der Punkt, an dem man ehrlich sein muss:** ueber das
Internet ist die Verzoegerung so gross wie die Leitung. Der Gastgeber
rechnet alles, es gibt keine Vorhersage beim Gast (siehe 2.1) - ein Gast
sieht seine eigene Figur erst nach einem Hin- und Rueckweg. Im LAN sind
das zwei Millisekunden, ueber das Internet dreissig bis hundert. Zielen
folgt trotzdem sofort, das rechnet jeder bei sich (12.11). Wer das
Gefecht wirklich ueber das Internet spielen will, braucht als naechstes
eine Vorhersage fuer die eigene Bewegung - und das ist mehr Arbeit als
alles, was hier bisher steht.

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

**Seit 0.27 ersetzt durch `anzeige.py`** (12b). Die Tabelle bleibt als
Beschreibung dessen, was oben in der Mitte steht; die Adresse steht nur
noch in der Lobby und im Pausenmenue.

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
| `korn` | 3 px | Aufloesung der Wolke, im Massstab der Kacheln daneben |
| `gitter` | 17 px | Maschenweite der groben Lage; die feine ist halb so gross |
| `kern` | 0.70 | bis hierhin deckt sie voll - und verbirgt auch Namen |
| `schwelle` | 0.30 | ab dieser Dichte steht ueberhaupt Rauch. Sie steigt beim Verwehen |
| `grund` / `dicke_hell` | 0.20 / 0.70 | Helligkeit am duennen Rand und Zuwachs durch Dicke |
| `licht_staerke` | 1.1 | wie stark das Gefaelle zum Licht die Tonstufe verschiebt |
| `fremde_ebene` | 0.55 | so viel Deckkraft behaelt Rauch einer anderen Etage |
| `puffer` | 24 | so viele fertige Wolkenbilder werden gehalten |

**Ein Dichtefeld, keine gewuerfelten Kloetze.** Der erste Anlauf wuerfelte
jeden Block einzeln - das ergab Rauschen, kein Rauch: "sieht aus wie
Konfetti" war das Urteil, und es stimmte. Jetzt liegt darunter ein
glattes Feld aus zwei Zufallsgittern (17 px und 8.5 px Maschenweite), die
dazwischen mit einer S-Kurve ueberblendet werden. Benachbarte Stellen
bekommen dadurch aehnliche Werte, und daraus werden zusammenhaengende
Ballen.

**Volumen aus zwei Anteilen.** Wo die Wolke dick ist, streut sie mehr
Licht und ist heller - das gibt ihr den Koerper. Dazu das Gefaelle zum
Licht hin (von oben links, wie im ganzen Spiel) als leichte Kante.
Umgekehrt gewichtet sah es aus wie Gestein: harte Adern mit viel
Kontrast.

**Pixel-Art bleibt es trotzdem**, weil das Feld in Koerner von
`RAUCH["korn"]` (3 px) zerlegt und in sieben Tonstufen quantisiert wird.
Gebaut wird in einem kleinen Puffer, in dem ein Bildpunkt einem Korn
entspricht, und erst am Schluss hart hochskaliert - das ist um
Groessenordnungen schneller, als ein paar tausend Rechtecke einzeln zu
zeichnen.

**Kosten:** rund 4 ms, einmal je Wolke. Das Feld haengt nur an der Lage,
nicht an der Dichte; die verschiebt bloss die Schwelle. Alle
Zeichenstufen bedienen sich also aus demselben Feld. Der erste Anlauf
rechnete es fuenf Mal und brauchte 58 ms - ein sichtbarer Ruckler.

**Deckkraft aus dem Abstand, nicht aus dem Rauschen.** Innerhalb von
`kern` (70 % des Radius) deckt sie voll, darueber in zwei Stufen weniger.
Haengt die Deckkraft am Feld, reisst jede Delle ein durchsichtiges Loch
mitten in die Wand - und zwar genau dort, wo `welt.verdeckt` sagt, hier
sei niemand zu sehen. Beide benutzen jetzt dieselbe Grenze.

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

Vorrat: Repetierer 42, Sturm 90, Schrot 18, Scharf 10, Granate 3, Rauch 2,
Brecheisen 0. Kiste alle 14 s, hoechstens 4 gleichzeitig, eine Kiste gibt
50 % des vollen Vorrats.

**Das sind rund drei Nachladungen je Waffe, und das ist die ganze Idee.**
Vorher war es das Doppelte - 279 Schuss im Vorrat merkt in einer
Testrunde niemand. Und ein Vorrat, der nie sinkt, macht jede
Munitionskiste nutzlos: man kann nichts auffuellen, was voll ist.

**Der Wiedereinstieg zahlt aus dem Vorrat.** Siehe 12.19 - das war der
eigentliche Fehler.

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

### 12.16 Die Treppe, die zweimal ausloest (0.19.0)

**Symptom.** Ein Druck auf E an der Treppe, und man steht blinkend
zwischen zwei Etagen - hoch und sofort wieder hinunter.

**Ursache.** `nutzen` wird **gehalten**, nicht gedrueckt; das braucht das
Aufhelfen. Also versuchte jedes Bild einen Ebenenwechsel. Nach dem ersten
steht die Figur auf der Zielkachel - und dort liegt die Treppe zurueck
nach unten.

**Behebung.** `GEFECHT["treppe_takt"]` (1.5 s) Sperre **am Kaempfer**,
nicht an der Kachel. So haelt sie auch, wenn er nach dem Wechsel gleich
auf der naechsten Treppe steht.

**Merke.** Sobald eine Taste gehalten statt gedrueckt ausgewertet wird,
braucht jede Handlung daran eine eigene Sperre. Der Einzelspieler hat das
Problem nicht - er fragt `gedrueckt()` ab.

**Nachtrag 0.27.** Beim Gast kam es wieder: hoch, runter, hoch, alle
anderthalb Sekunden. Die Sperre hielt nur, solange E wirklich losgelassen
wurde - blieb es beim Gast als gehalten stehen (das Loslassen ging an ein
anderes Fenster, weil der Fokus wechselte), nahm er nach jeder Sperre die
Treppe erneut. Jetzt haengt die Treppe am **Druck**: das Ereignis
`nutzen` in `knoepfe`, das je Druck genau einmal kommt und beim Stau nie
verworfen wird. Halten zaehlt nur noch fuers Aufhelfen. Die Sperre ist auf
0,5 s geschrumpft und faengt nur noch einen Doppeldruck ab. Dazu laesst
das Spiel beim Fokusverlust alle Tasten los, und die Tastenwiederholung
ist im Spiel aus - sonst waere ein gehaltenes E wieder eine Folge von
Druecken.

### 12.19 Knappe Munition, die keine war (schwer, 0.19.1)

**Symptom.** Zwei Meldungen, die nach zwei Fehlern klangen: "man kann
trotzdem unendlich oft nachladen" und "die Munitionskisten einzusammeln
funktioniert auch nicht".

**Ursache, eine fuer beide.** `_wieder_einsteigen` setzte
`k.magazin = {alles voll}` - **am Vorrat vorbei**. In einem Deathmatch
stirbt man alle paar Sekunden, bekommt also alle sieben Magazine
geschenkt (60 Schuss) und kommt nie in die Lage, aus dem Vorrat
nachladen zu muessen. Der Vorrat blieb voll. Und was voll ist, kann man
nicht auffuellen: `auffuellen()` gibt False zurueck, die Kiste bleibt
liegen, und es sieht aus, als ginge das Aufheben nicht.

Dazu kam die zweite Haelfte: 279 Schuss Vorrat sind rund zwanzig
Nachladungen. Selbst wer nie starb, merkte in einer Testrunde keine
Grenze.

**Behebung.** `_magazine_fuellen()`: ohne Begrenzung wie immer umsonst,
mit Begrenzung als Nachladen aller Waffen, bezahlt aus dem Vorrat. Dazu
die Vorraete halbiert und der Vorrat je Waffe in der Hotbar sichtbar,
plus die Meldung "KEIN VORRAT", wenn beides leer ist.

**Merke.** Wer eine Ressource begrenzt, muss **jede** Stelle finden, die
sie vergibt - nicht nur die offensichtliche. Und eine Begrenzung, die man
nirgends sinken sieht, ist von einer kaputten nicht zu unterscheiden.

### 12.20 Kleinere Fallen

| Falle | Was passiert |
| --- | --- |
| `welt.wesen` beim Gast vergessen zu setzen | Der Renderer zeichnet nichts; der Gast sieht eine leere Karte. |
| `welt.neue` nicht leeren | Wesen sammeln sich beim Gast an und werden nie weggeraeumt. |
| `_beute_legen` ohne Obergrenze | Nach zehn Minuten liegt die Karte voller Medkits. |
| Ein Test, der `_gedrueckt` gesetzt laesst | Ein Schalter kippt mehrfach - Testfehler, nicht Codefehler. |
| `unverwundbar` nach `aufhelfen()` | Schaden im Test kommt nicht an. Erst `unverwundbar = 0.0` setzen. |
| Ein einzelner `FIXED_DT`-Schritt fuer `rest = 0.01` | Zu kurz. Restzeit knapp unter **einen** Schritt setzen. |
| `Spiel()` ohne Seed im Test | Sporadische Fehlschlaege. Tests geben einen festen Seed. |

### 12.21 Was **nicht** kaputt war

Zwei Dinge sahen nach Fehlern aus und waren keine: die unterschiedlichen
Blutflecken auf beiden Rechnern (Kosmetik wird nicht uebertragen, siehe
4.3) und dass 2 gegen 1 im Kreis nicht schneller laedt als 1 gegen 0 (der
Vorsprung zaehlt, nicht die Kopfzahl, siehe 7.6).

Das gemeldete "etwas laggy" war dagegen **echt**: `NETZ["takt"]` stand auf
1/30, der Gast bekam also 30 Stellungen je Sekunde und zeichnete 120 Bilder
dazwischen. Auf 1/60 erhoeht, dazu `eingabe_takt` eingefuehrt - seitdem
weg. Wer die Zahl senkt, holt sich das Ruckeln zurueck.

---

## 12a. Wellen, Gegner und Bosse

### Der Fehler, der alles ausloeste

Gemessen auf STAUBTAL (3840 mal 2560 Pixel), Welle 1, zwei Spieler:

| | vorher | jetzt |
|---|---|---|
| Abstand zum naechsten Spieler, Median | **1477 px** | 446 px |
| Laufzeit, bis er ankommt | **20 s** | 6 s |
| Weitester | 1975 px (27 s) | 553 px (7 s) |
| Auf einer Ebene ohne jeden Spieler | **4 von 6** | 1 von 6 |

Der Grund war eine Zeile: `freier_punkt(welt, rnd.randrange(ebenen))`.
Eine gewuerfelte Stelle irgendwo auf der Karte, auf einer gewuerfelten
Ebene. Auf der Testkarte (1408 mal 768) fiel das nie auf, weil dort
jeder zufaellige Punkt zwangslaeufig nah liegt - Median 420 Pixel. Auf
einer grossen Karte war eine Welle damit zwanzig Sekunden nichts und
danach ein Troepfeln, und zwei Drittel standen auf einem Plateau, auf
das nur Rampen fuehren.

### Wo sie jetzt herkommen

`_spawnstelle()` in `mehrspieler.py`, vier Regeln (`K.SPAWN`):

1. **Bei jemandem**, nicht ueber der Karte: gewuerfelt wird im Ring um
   einen lebenden Spieler.
2. **Zwischen `nah` (260) und `weit` (620).** Naeher stuende er im
   Gesicht, weiter waere wieder Fussmarsch. Der Abstand gilt gegen
   **jeden** Spieler, nicht nur gegen den gewuerfelten - stand dort
   einmal nur der eine, und prompt entstand auf der kleinen Karte ein
   Gegner 137 Pixel neben dem zweiten Mann.
3. **Moeglichst ausser Sicht** (`welt.sicht_frei`). Geht das nicht - auf
   offenem Sand oft nicht -, dann eben im Blickfeld.
4. **Auf der Ebene eines Spielers**, in 85 Prozent der Faelle.

Dazu **Marken in der Karte**: der Buchstabe `Z` ist eine Spawnstelle,
genau wie `A`, `B`, `C` Kreise sind. STAUBTAL hat 31 davon - am Fuss der
Plateaus, an den Buden, im Depot, an der Mauer -, die Testkarte 21. Auf
offenem Sand steht keine: mitten im Freien aus dem Nichts zu erscheinen
sieht nach Fehler aus, hinter einer Bude hervorzukommen nicht. Marken
sind eine **Bevorzugung, keine Bedingung** - wer eine Karte ohne Z baut,
bekommt trotzdem Gegner.

### Die Haengerwache

Der zweite Fehler, gefunden beim Nachmessen: ein Laeufer stand nach 120
Sekunden immer noch 323 Pixel entfernt an einer Plateauwand, **auf
derselben Ebene** wie die Spieler. Das Ausweichen ist ein Faecher aus
Proben und kein Wegesucher; an einem Plateau von 32 mal 19 Kacheln
reicht es nicht. Und weil eine Welle erst endet, wenn alle liegen, stand
damit die ganze Runde: in 300 Sekunden wurde Welle 2 nicht fertig.

Ein richtiger Wegesucher waere die saubere Antwort und ein eigenes
Stueck Arbeit. Die ehrliche steht in `_haenger_pruefen`: wer sieben
Sekunden lang nicht naeher kommt, wird an eine frische Stelle gesetzt.
Er ist dabei ausser Sicht, weil die Stelle genau darauf geprueft wird.
Danach: fuenf Wellen in 300 Sekunden statt zwei.

**Ein Boss wird nie umgesetzt.** Ihn zu suchen gehoert zur Aufgabe, und
einer, der hinter dem Ruecken neu auftaucht, ist unfair.

### Woraus eine Welle besteht

`K.MISCHUNG`: je Gegnerart, ab welcher Welle es sie gibt und mit welchem
Gewicht. Die Gewichte verschieben sich mit der Wellennummer; der Laeufer
hat einen fallenden Zuschlag und eine Untergrenze - er verschwindet
nicht, aber er macht Platz.

| Welle | neu dabei | Frage, die er stellt |
|---|---|---|
| 1 | LAEUFER | kannst du treffen, bevor er da ist? |
| 2 | RENNER | kannst du dich noch umdrehen? (138 px/s gegen 132 beim Spieler) |
| 3 | BRECHER | reicht deine Munition? |
| 4 | BLAEHER | wo steht ihr gerade? (platzt beim Sterben) |
| 6 | SPEIER | kommst du an ihn heran? (haelt 150-230 px Abstand und spuckt) |

**Hoechstens eine neue Art je Welle**, und keine faellt mit einer
Bosswelle zusammen - Welle 5 ist schon die neue Sache. Ein Test haelt
beides fest.

### Nachschub statt einer Lieferung

Bisher stand die ganze Welle auf einmal da: der Druck kam einmal und war
vorbei, und bei vierzig Gegnern fiel die Bildrate. Jetzt kommt sie in
Schueben zu sechs, mit 3,2 Sekunden Pause, hoechstens 22 zugleich auf
der Karte. Kleine Wellen kommen weiter auf einmal - bei sechs Gegnern
ist ein Nachschub nur eine Verzoegerung.

### Die Bosse

Jede fuenfte Welle, reihum, immer genau einer. Sein Leben waechst mit
der Zahl der Spieler (plus 55 Prozent je weiterem) und mit der Zahl der
Bosse, die schon lagen (plus 30 Prozent). In einer Bosswelle kommt
weniger Fussvolk - der Boss ist die Aufgabe, ein volles Rudel daneben
macht ihn nicht schwerer, nur unuebersichtlich.

| Boss | Faehigkeit | Wozu er zwingt |
|---|---|---|
| **KOLOSS** | Stampfer: 104 px Umkreis, trifft auch hinter Deckung | **weg von ihm** - Nahkampf wird toedlich, eine Ecke hilft nicht |
| **MUTTER** | Brut: ruft alle 5 s drei Renner, hoechstens 14 | **zu ihr hin** - wer die Brut abarbeitet, dreht den Hahn nicht zu |
| **BRANDSTIFTER** | Brand: wirft Feuer dorthin, wo jemand gleich sein wird | **in Bewegung** - er nimmt Stellungen weg, nicht Leben |

**Jede Faehigkeit hat einen Vorlauf** (0,6 bis 0,9 s) und wird
angekuendigt: ein Ring, der sich zuzieht, in der Groesse der Wirkung,
dazu ein Wort ueber dem Boss und ein Ton. Das ist der Unterschied
zwischen einem Boss und einer Steuer - ohne Vorwarnung kann man nur
Abstand halten, mit Vorwarnung wird es eine Frage: reicht die Zeit noch
fuer einen Schuss?

Der Koloss ist **unverschiebbar**. Ohne das traegt ein Sturmgewehr ihn
rueckwaerts aus der Halle, und seine ganze Bedrohung wird eine Frage des
Nachladens.

### Das Feuer eines Gegners verschont Gegner

Gemessen: ein Blaeher, der in einem Rudel von fuenf Laeufern platzte,
toetete durch sein Feuer **alle fuenf**. Damit waere "Blaeher ins Rudel
locken und erschiessen" ein Trick, der eine halbe Welle loescht - und
wer den Trick hat, spielt ihn und nicht das Spiel.

`Brandflaeche` hat darum ein Feld `verschont`. Leer heisst: es brennt
alles, und so bleibt der **Molotow eines Spielers** - das ist ja seine
Aufgabe. Gesetzt wird es nur beim Feuer, das ein Gegner legt. Nachher
gemessen: Blaeher 0 von 5, Molotow weiter 5 von 5.

### Im Netz

Ein Gegner geht als `[x, y, winkel, ebene, art, lebensanteil, kennung,
vorlauf]`. Die beiden letzten sind neu:

* **Kennung**, damit der Gast zwischen zwei Meldungen zeichnen kann.
  Ohne sie stand jeder Gegner die halbe Zeit still und sprang dann -
  derselbe Fehler wie frueher bei den Granaten. Bei einem Laeufer faellt
  das gerade noch durch, bei einem 58 Pixel breiten Koloss nicht.
  Gemessen: Stillstand 2,2 Prozent, Median 0,57 px je Bild.
* **Vorlauf**, damit der Gast die Ankuendigung sieht. Ohne ihn saehe er
  den Stampfer erst am Schaden.

Gemessen ueber 25 Sekunden: Gastgeber und Gast zeigten in **250 von 250**
Proben dieselbe Zahl Gegner.

Nebenbei aufgefallen und mitbehoben: der **Gastgeber zeichnete gar keine
Lebensbalken** fuer Gegner, nur der Gast. Bei einem Laeufer, der nach
zwei Treffern liegt, faellt das nicht auf; bei einem Boss mit 2170 Leben
ist es der Unterschied zwischen "gleich ist er soweit" und "schiesse ich
hier ins Leere?". Jetzt zeichnen beide dasselbe.

---

## 12b. Version 0.27: Lobby, Regeln, Anzeige, und was dabei auffiel

Neunzehn Punkte auf einmal, darum hier nach Thema geordnet.

### Bewegung und Tempo

* **Dash statt Sprint** (`K.DASH`): zwei Ladungen, die nacheinander
  nachladen (3,4 s je Ladung; seit 0.31 drei Ladungen zu 2,7 s). Ein Stoss traegt rund zwei Kacheln
  (gemessen 75 px). Nicht im Sturz, nicht am Boden, nicht beim Medkit,
  nicht beim Ziehen.
* **Langsamer**: Spieler 108 statt 132 px/s, alle Gegner mal 0,85 im
  selben Verhaeltnis. Treffer auf weite Distanz gemessen 13 -> 23 Prozent.
* **Medkit in der Hand**: beim Anlegen (0,8 s) haelt die Figur das Medkit
  statt der Waffe, geht mit 0,55 und schiesst nicht.

### Am Boden

* Nicht mehr schieb- und drehbar. Ein Mitspieler in Reichweite **zieht**
  ihn mit G (`K.ZIEHEN`, 0,52 Tempo; dabei kein Schiessen, kein Aufhelfen).
* Wer liegt, sieht kein "aufhelfen" mehr neben einem anderen Liegenden.
* **Rufen** mit E (1,5 s Sperre): der Randpfeil bei den Mitspielern
  pulst, ist er im Bild, blinkt ueber ihm eine Marke und die Figur zuckt.
  Randpfeile zeigen auf jeden gefallenen Mitspieler ausserhalb des Bildes.
* **Versus**: eine Mannschaft verliert, sobald niemand mehr steht, der
  aufhelfen koennte - nicht erst, wenn alle Uhren abgelaufen sind.
  Rundenzahl einstellbar (gespielte Runden), Gleichstand bringt eine
  Runde als **Matchpoint**.

### Ebenen

* Im Mehrspieler sind obere Ebenen dort ausgeblendet, wo sie ueber
  Spielflaeche liegen (`Renderer.obermaske`); Plateaus ueber Fels bleiben.
  Q schaltet um, die Vorliebe fuer den Rundenstart (OBERE EBENEN) wandert
  mit dem Konto. Was faellt, bleibt sichtbar.
* Granaten behalten ihren Schwung beim Fall ueber eine Kante.
* **Wegenetz** (`wege.py`): Gegner folgen ueber Treppen und Rampen auf
  andere Ebenen; Bosse warten auf ihrer. Dabei gefunden: alle sieben
  Rampen auf STAUBTAL fuehrten seit 0.23 ins Loch.

### Regeln an einer Stelle (`regeln.py`)

Eine Regelsammlung ist ein Woerterbuch. `vorgabe()`, `saeubern(roh)`,
`sichtbar(d)`, `verstellen(d, k, +1)`, `anzeige(d, k)`. Pausenmenue,
Willkommen, Neustart und Lobby lesen alle diese Tabelle. Neu:

| Regel | Werte | Wo |
| --- | --- | --- |
| SCHWIERIGKEIT | leicht, normal, schwer, albtraum (`K.SCHWIERIGKEIT`) | mit Wellen |
| BOSSE | an/aus; aus heisst volle Welle statt Bosswelle | mit Wellen |
| AUSRUESTUNG: EINES FUER ALLE | ein Loadout des Gastgebers fuer jeden | ueberall |
| HALTEZEIT, VERFALL | 10-180 s, an/aus | huegel |
| HOECHSTDAUER | Minuten | versus, huegel |

### Die Lobby (`lobby.py`, `karten/lobby.txt`)

Wer aufmacht, landet in der Lobby (`--sofort` ueberspringt sie). Drei
Bereiche, im Kopf der Kartendatei als Rechtecke: **Arena** (PVP - nur
dort treffen sich Spieler, und nur wenn beide drin stehen), **Schiess-
stand** (vier Puppen: fallen nicht, heilen nach 2,5 s, zeigen den Schaden
als Zahl) und **Gehege** (Zombies, nur wenn jemand drin ist; sie bleiben
am Tor stehen). Auf dem Platz tut niemandem etwas weh. Nichts wird
gebucht.

Der Gastgeber stellt die Runden auf einer Tafel ein (P). Zu sehen ist
zuerst nur die naechste Runde und START; der **Rundenplan** klappt erst
auf Wunsch auf: mehrere Runden, kopieren/einfuegen, Schleife. Nach jeder
geplanten Runde zeigt die Siegtafel 12 s, was kommt, dann geht es weiter
- oder zurueck in die Lobby. Nachricht `plan` an alle Gaeste.

### Die Anzeige (`anzeige.py`)

Feste Orte statt gewachsener Plaetze, und Modi nach den Regeln: Hotbar
gross mit Loadout, klein mit allen Waffen; Vorrat nur bei knapper
Munition; oben Mitte je Spielart Uhr, Welle mit Restzahl und Bossbalken,
Teamstand, Versuspunkte, Kreisbalken. Die Raender bleiben fuer die Pfeile
frei.

### Nur gleiche Versionen (0.27.1)

**FEST.** Der Gast schickt im `hallo` seine Version (`K.VERSION`, gelesen
aus `rustfront_menu.py`), der Gastgeber vergleicht sie **genau** und sagt
sonst mit `abgelehnt` ab: `grund` "VERSION x NOETIG" (hoechstens 24
Zeichen, so viel zeigen alte Gaeste), dazu `version` und `deine`. Ein neuer
Gast zeigt dann die Tafel FALSCHE VERSION. Umgekehrt steht die Version im
`willkommen`/`neustart`; fehlt sie oder weicht sie ab, legt der Gast auf.

**GRUND.** Gastgeber und Gast teilen sich die Arbeit - der Gast schickt
Druecke, der Gastgeber rechnet. Ein Fehler, der in der einen Version
behoben ist, kommt mit der anderen zurueck: so geschehen mit der Treppe
(12.16, Nachtrag). Daraus folgt eine Pflicht: **wer am Netzcode etwas
aendert, zaehlt die Version hoch**, sonst greift die Pruefung nicht.

### Was dabei an Fehlern auffiel

* Der Gast sah die Gesamtmunition anderer Waffen nicht (nur die gehaltene
  ging mit) - und uebernahm die Waffenliste nie: mit eigenem Loadout zeigte
  seine Hotbar neun statt drei Waffen.
* Klaenge des Gastgebers (Bossansage, Spucken) kamen beim Gast nie an.
* Einzelne Tastendruecke fielen bei voller Leitung weg.
* Kartenwechsel beim Gast: zurueck auf die eingebaute Karte ging nicht,
  und die Mitspieler blieben in der alten Welt.
* Der Mannschaftswunsch ging verloren, wenn eine Teamrunde aus einer Runde
  ohne Mannschaften heraus anfing.
* Die Haengerwache setzte Gegner um, die am Ziel standen und kaempften.
* Spawnstellen ueber Loechern auf STAUBTAL.

---

## 12c. Version 0.28: Spielerkosmetik

Ein erster Versuch, wie Spieler selbst etwas ins Spiel bringen: ein
eigener **Ton** und ein eigenes **Bild** fuer die Blendgranate. Gemacht
wird beides in der Kontoseite (KONTO.html, Reiter KOSMETIK), abgelegt im
Konto (Tabelle `kosmetik`, `docs/KONTO.md` 5.6), verteilt in der Lobby,
gezeigt beim Werfen. Alles im Spiel steht in `dustfront/spielerkosmetik.py`;
das Gefecht bindet es wie die Lobby als Mixin ein (`KosmetikTeil`).

### Was der Spieler macht

In der Kontoseite: eine MP3 (oder WAV, OGG) laden, mit der Maus
zuschneiden, Bass bis +40 dB, LAUTER bis +30 dB (weich uebersteuert, tanh),
den klassischen Knall und das Pfeifen **aus dem Spiel** dazumischen,
abklingen lassen. Ein Bild laden, ausschneiden, Filter darueber (Helligkeit,
Kontrast, Farbe, Farbton, Pixel, Frittiert, Grau/Sepia/Umgekehrt, rund).
Darunter eine Vorschau in Spielgroesse mit Blitz und Ton.

### Die zwei Regeln fuer den Ton

**FEST.** 1,0 bis 4,0 Sekunden. Und er **wird immer leiser**: nach 120 ms
Anlauf fuehrt `ton_ausklingen` eine Obergrenze, die nie steigt, geradlinig
auf null faellt und im letzten Abschnitt null ist. Wird der Ton leiser,
folgt die Grenze - hoechstens um `ton_abfall` (0,95) je 20-ms-Abschnitt,
damit nach einer kurzen Luecke zwischen zwei Schlaegen noch etwas kommt.
Was darueber liegt, wird heruntergeregelt; zwischen den Abschnitten gilt
an jeder Kante die kleinere Verstaerkung, also bekommt keine Probe mehr,
als ihr Abschnitt darf.

**GRUND.** Ein Dauerton waere eine Waffe: wer ihn hoert, hoert keine
Schritte mehr. Ein zu kurzer Ton waere ein Klick, kein Knall.

**FEST.** Geprueft wird **im Spiel**, bei jedem Paket - auch beim eigenen
vom Server, auch bei dem eines Mitspielers. Die Seite rechnet die Grenze
fuer ihre Vorschau nach (`tonAusklingen`, Schritt fuer Schritt gleich),
laedt aber den Ton **davor** hoch.

**GRUND.** Eine veraenderte Seite oder ein veraenderter Klient kaeme sonst
mit einem Dauerton durch. Und weil das Spiel die Grenze genau einmal
rechnet, klingt es im Spiel Probe fuer Probe wie in der Vorschau -
`tests/kontoseite_browser.py` prueft genau das.

### Verteilen in der Lobby

Vier Meldungen, alle neben der Weltmeldung her:

| Meldung | Richtung | Inhalt |
| --- | --- | --- |
| `kos` | Gast → Gastgeber, Gastgeber → Gast | ein Teil eines Pakets: `k` Kennung, `i`/`n` Teil von, `d` Daten; vom Gastgeber dazu `von` |
| `kos_index` | Gastgeber → alle | wer welche Kosmetik hat: Nummer → Kennung |
| `kos_hat` | Gast → Gastgeber | was hier schon fertig angekommen ist |
| `kos_weg` | Gast → Gastgeber | ich habe meine entfernt |

Ein Paket ist JSON mit Base64: der Ton **so, wie er vom Konto kam**, und
das PNG. Seit 0.30 traegt das PNG einen tEXt-Abschnitt `dustfront` mit der
Lage im Weiss (`{"x", "y", "h"}`, Anteile am Bildschirm); fehlt er, fuellt
das Bild den ganzen Schirm (`spielerkosmetik.bild_lage`). Die Kennung ist `sha1(ton|bild)`, 16 Zeichen. Jeder Rechner
bereitet den Ton selbst auf; weil das festgelegt ist, kommt ueberall
dasselbe heraus, und die Kennung am Rohen stimmt bei allen.

**FEST.** Teile zu 8000 Zeichen, **zwei je Schritt**, hoechstens 100 je
Paket (das groesste erlaubte hat 92). Kommt eine neue Kennung, ist das alte
Paket hinfaellig - auch was davon noch in der Schlange wartet.

**GRUND.** Eine Viertelmegabyte vor jeder Weltmeldung, und die Lobby
ruckelte, waehrend geladen wird. `netz._schlange_kuerzen` wirft `kos`
nie weg - es ist keine Weltmeldung, die die naechste ersetzt.

Wer geht, nimmt seine Kosmetik mit: der Gastgeber streicht ihn aus dem
Index, und jeder Rechner wirft weg, was nicht mehr darin steht.

### Mit oder ohne - der Gastgeber entscheidet

Gibt es Kosmetik, hat die Tafel (P) und das Pausenmenue statt START zwei
Knoepfe: **MIT KOSMETIK** und **OHNE KOSMETIK**. Oben in der Lobby steht,
wie weit sie verteilt ist ("KOSMETIK LAEDT 2 VON 3").

**FEST.** Mit Kosmetik geht es erst, wenn **jeder Rechner jede Kosmetik
jedes anderen** hat (`kosmetik_stand`, beim Gastgeber aus den `kos_hat`
der Gaeste). Bis dahin ist der Knopf gesperrt, und `plan_starten` lehnt ab.
Die Entscheidung ist die Regel `kosmetik` in `regeln.py` - versteckt, in
keinem Menue, aber sie geht mit den Regeln zu den Gaesten und gilt fuer
den ganzen Rundenplan. In der Lobby gilt Kosmetik immer: dort probiert man
sie aus.

**GRUND.** Sonst hoerte der eine den Ton des Werfers und der andere den
gewoehnlichen Knall, und keiner wuesste, was der andere erlebt.

### Beim Werfen

`Granate` gibt ihren Werfer an `Welt.explosion(..., von=)` weiter, die
Wirkungsmeldung `x` traegt ihn als siebtes Feld (seine Nummer, -1 ohne).
`Welt.blitz` fragt die Szene; hat der Werfer Kosmetik und gilt sie, spielt
sie **seinen Ton** (so laut, wie ein Knall an dieser Stelle waere) statt
Knall und Pfeifen, und legt **sein Bild** ins Weiss - 144 Pixel, so
deckend, wie das Weiss noch ist. Wer keine hat, knallt wie immer.

### Version

**0.28.0.** Neue Meldungen und ein siebtes Feld in `x`: ein Gast von 0.27
verstuende die Lobby nicht mehr. Die Versionspruefung (0.27.1) weist ihn
ab, wie sie soll.

---

## 12d. Version 0.30: Sichtweite, Nebel, Blendung, fallende Gegner

### Sichtweite und Nebel

**FEST.** Das Mausrad stellt im Gefecht ein, wie viel Welt ins Bild passt:
`ZOOM["stufen"]` von 0,75 bis 2. Gezeichnet wird dafuer auf eine Flaeche in
Zoomgroesse (`Renderer.groesse`, `Kamera.zoom`) und danach auf 640 x 360
gebracht; die Anzeige kommt erst danach und bleibt scharf. Zielen rechnet
ueber `Kamera.zu_welt`, Namen, Randpfeile und Zielerfassung ueber
`Kamera.zu_bild`.

**FEST.** Ausserhalb des normalen Bildes (wo die Kamera bei Zoom 1 stuende)
liegt der Nebel. Gezeichnet wird zuerst nur das Gelaende
(`Renderer.nur_gelaende`), darauf der Nebel, und dann das volle Bild -
beschnitten auf das normale Bild (`set_clip`). Wesen ausserhalb werden also
**gar nicht** gezeichnet, und ihre Namen auch nicht.

**GRUND.** Wer weiter sieht, soll Ueberblick haben, keinen Vorteil. Ein
Zoom, der Gegner hinter dem Rand zeigt, waere ein Wandhack, den jeder
eingeschaltet laesst.

Die Ebenenansicht liegt im Gefecht dafuer auf Strg + Mausrad und auf
Bild hoch / Bild runter (umlegbar, `ansicht_hoch`, `ansicht_runter`). Im
Einzelspiel bleibt das Rad bei den Ebenen.

### Blendgranate

**FEST.** Unter `BLENDEN["schwelle"]` (0,4) gibt es kein Weiss. Wer
wegschaut (`abgewandt` 0,35) oder weiter als rund 250 Pixel weg steht,
sieht nur, was jeder sieht: eine weisse Explosion mit Glitzer und
Druckring - ohne Splitter, ohne Brandfleck. Darueber ist das Weiss ganz
weiss und deckend (`deckend_ab`), bis es abklingt.

### Fallende Gegner

**FEST.** Ein Gegner laeuft nie in ein Loch - die Kacheln sind fuer ihn
Wand. Der Rueckstoss steckt aber in einem eigenen Topf (`Gegner.stoss`) und
kennt diese Wand nicht: schiebt ein Treffer einen Gegner ueber die Kante,
faellt er auf die Ebene darunter, mit Sturz und Schaden wie eine Figur.
Waehrenddessen haelt `world.befreien` ihn nicht an der Kante fest
(`Gegner.geschoben`). Bosse lassen sich gar nicht schieben und fallen
darum auch nicht.

**GRUND.** Als Notbremse, nicht als Spielzug: vorher blieb ein Gegner, den
eine Salve ueber den Rand trug, an einer unsichtbaren Kante haengen.

### Lobby: unendliche Munition

`LobbyTeil._lobby_munition` fuellt jedes Magazin, und zwar **nach** dem
Schritt der Welt. Davor nahm der Schuss im selben Schritt gleich wieder
eine Patrone, und die Zahl sprang bei jedem Schuss von 100 auf 99 und
zurueck (gemeldet als Flackern beim MG).

## 12e. Version 0.31: Statistik, Abbrueche, ADMIN

### Wer bucht was

**FEST.** Gerechnet wird weiter nur beim Gastgeber (`Kaempfer.zaehlen`).
Neu gezaehlt: `gegner_abschuesse` und `boss_abschuesse`
(`entities.abschuss_buchen`), `treffer_spieler` und `treffer_gegner`
(`treffer_ziel_buchen`), und beim Buchen `schuesse_pvp`/`treffer_pvp` oder
`schuesse_pve`/`treffer_pve` nach `MODUS_ART`. PVPVE bekommt keine der
beiden - dort ist ein Schuss weder das eine noch das andere.

**FEST.** Ein Spieler faellt erst um und stirbt spaeter (Bodenzeit). Die
Waffe des Treffers, der ihn umwarf, merkt sich `Kaempfer.toeter_waffe`;
gebucht wird sie beim Abrechnen, einmal je Tod. Die Summe `abschuesse`
kommt weiter aus `Kaempfer.abschuesse` - die Zeile je Waffe aendert sie
nicht.

**FEST.** Wen man wie oft erledigt hat: `Kaempfer.opfer` je Nummer, beim
Buchen mit Name und Kontokennung (`_opfer_liste`). Die Kennung schickt der
Gast mit "hallo" (`kt`); wer ohne Konto spielt, steht nur mit Namen da.

### Abbrueche

**FEST.** Endet eine Runde, die laenger als `GEFECHT["abbruch_ab"]` lief,
nicht regulaer, bucht `_abbruch_buchen` sie als `ende = "abgebrochen"`:

* **Gastgeber geht** (ESC, Fenster zu, zurueck in die Lobby, neue Regeln):
  er schickt `{"t":"abbruch","partie","werte"}` an alle, spuelt die
  Leitungen und bucht sich selbst. Die Gaeste buchen ihre Zahlen unter
  derselben Partie.
* **Leitung reisst**: der Gast bucht den letzten `{"t":"stand"}`, den der
  Gastgeber alle `GEFECHT["zwischenstand_takt"]` Sekunden schickt.
* **Gast geht**: er bucht seinen letzten Zwischenstand.
* **Fenster zu**: `App._fenster_zu` verlaesst jetzt alle Szenen wie ESC -
  vorher endete die Schleife einfach, und die Runde war fuer alle weg.
  Danach laedt `Konto.hochladen_vor_ende` noch hoch, was offen ist.

**GRUND.** Getrennt von den regulaeren, weil sonst jede Statistik "je
Runde" kippt: eine nach einer Minute abgebrochene Runde hat wenige
Abschuesse und zaehlt nicht als Runde. Gebucht wird sie trotzdem, weil
die Zahlen darin gespielt wurden.

**FEST.** Jede gebuchte Zeile traegt `version` (`K.VERSION`). Nach einer
Aenderung am Gleichgewicht lassen sich die Zahlen davor und danach trennen.

### Der ADMIN

Ganz im Server (`docs/KONTO.md` 5.8) und auf der Kontoseite; im Spiel ist
nur der Name `admin` vorbehalten (`ablage.VORBEHALTEN`).

### Kleinere Fallen

* **Granaten beim Gast unsichtbar** (gemeldet): gesendet wurde nur, was
  "geschoss", "granate" oder "rauchgranate" hiess. Molotow, Blendgranate und
  Rakete hatten seit den Skins andere Bildnamen. Jetzt geht alles hinaus,
  was ein `Geschoss`, eine `Granate` oder eine `Rakete` ist, mit seinem
  Bildnamen.
* **Neustart beim Gast**: der Abbruch einer alten Runde wird gebucht,
  *bevor* die neuen Regeln gelesen werden - sonst stuende sie unter dem
  neuen Modus.

## 12f. Version 0.31.1: Plateaus als Felsbloecke, Zombies ohne Gewehr

**FEST.** Ein Plateau ist auf der oberen Ebene ein Stueck Boden ueber
Fels der unteren (`obermaske` 0). Sein Deckel wird deckend gezeichnet,
auch wenn die Etage sonst ausblendet; nur was ueber Spielflaeche liegt
(`obermaske` 1), wird durchsichtig (`_ausstanzen` mit
`BLEND_RGBA_MULT`) oder mit `oben_aus` ganz weggenommen.

**FEST.** Zwischen Deckel und Sockel zeichnet `Renderer.klippen_zeichnen`
eine Felswand: je Kante eines Plateaus (`Renderer.klippen`, zu ganzen
Strecken zusammengefasst und je Welt gemerkt) ein Viereck vom Deckelrand
zum Sockelrand. Beide Raender kommen aus `_abbildung` - genau der
Rechnung, mit der die Ebene selbst ins Bild kommt, samt der ganzzahligen
Groesse der Tiefenflaeche. Gezeichnet wird nur, was dem Auge zugewandt
ist; der Rest laege ohnehin unter dem Deckel. Gesteinsbaender, Fugen und
eine helle Oberkante stehen in `KLIPPEN`, die Farbe kommt aus der
Wandkachel des Kartensatzes.

**GRUND.** Gemeldet: von unten sah man den Felsblock, dann Boden "wie
Luft", dann blass und versetzt das Plateau. Die obere Ebene ist naeher am
Auge und darum groesser - das ist richtig. Falsch war, dass nichts den
Deckel mit dem Sockel verband und dass man durch den Deckel hindurchsah.

**Folge.** Was auf dem Boden hinter einem Plateau steht (vom Auge aus
gesehen), verdeckt jetzt der Deckel - wie bei einem echten Felsen. Und es
gilt fuer jede Etage, die auf Wand steht, also auch fuer die Arena.

**FEST.** Laeufer, Brecher und Speier zeichnet `_figur(..., bewaffnet=False)`:
kein Gewehrstummel, kurze Arme wie beim Bewaffneten (bis c + 8), nur einen
Pixel zur Mitte statt zwei, und in einem eigenen Ton: 30 Prozent vom
dunklen Ton zum Rumpfton (`art.ZOMBIE_ARMTON`).

**GRUND.** Der dunkle Rand des Kopfes lag vorher unter der Waffe. Ohne sie
liegt er genau zwischen den Armen, und in derselben Farbe wuchsen Arme und
Kopf zu einem dunklen Klotz zusammen. Ausprobiert und verworfen, jeweils
mit Bild: Klauen und Faeuste (0.31.1), laengere parallele Arme (0.31.3),
den Kopfrand aufhellen - die Arme aufzuhellen war das Unauffaelligste.

---

## 12g. Version 0.32: von Lobby zu Lobby

Gemeldet: "Es soll nicht mehr wirklich LAN-Gast und LAN-Gastgeber geben.
Man soll durch eine Datei direkt in die Lobby kommen und von da aus
anderen Lobbys im selben LAN beitreten koennen. Wenn ein Gast eine Runde
mit einem anderen Gastgeber verlaesst, soll er wieder zurueck in eine
Lobby kommen."

### Jeder ist Gastgeber seiner eigenen Lobby

`sitzung.eigene_lobby(app)` macht einen `Gastgeber` auf und schiebt ein
`Gefecht(lobby=True, ansagen=True, heimkehr=True)`. Es gibt keine Rolle
mehr, die man vorher waehlen muss: wer niemandem beitritt, ist Gastgeber,
und wer beitritt, war es bis eben.

**Der Port wandert.** Ist 50505 belegt - ein zweites Fenster auf demselben
Rechner -, wird 50506 genommen und so weiter (`NETZ["port_versuche"]`).
**FEST:** Unter Windows setzt der Gastgeber dafuer `SO_EXCLUSIVEADDRUSE`
statt `SO_REUSEADDR`. GRUND: `SO_REUSEADDR` heisst unter Windows "darf
sich auf einen belegten Port setzen"; das zweite Fenster haette 50505
bekommen, und die Verbindungen waeren zufaellig beim einen oder anderen
gelandet.

### Erst verbinden, dann umsteigen

`sitzung.beitreten(app, adresse, kennwort)` baut die Verbindung auf,
**bevor** die eigene Lobby zugeht. Scheitert sie, bleibt alles, wie es
war, und die Suche sagt warum (`fehler_kurz`: "DORT IST KEINE LOBBY
OFFEN", "KEINE ANTWORT - FALSCHE ADRESSE?" ...). Steht sie, ersetzt das
Gast-Gefecht den ganzen Stapel; die eigene Lobby wird dabei verlassen, wie
mit Esc - Gaeste, die dort waren, landen ihrerseits daheim.

### Zurueck nach Hause (`heimkehr`)

Ein Gast mit `heimkehr` geht in drei Faellen von selbst in eine neue
eigene Lobby, mit einem Hinweis oben:

| Fall | Hinweis |
| --- | --- |
| Menue: LOBBY / GEFECHT VERLASSEN | - |
| Leitung tot (Gastgeber hoert auf, Netz weg) | VERBINDUNG ZU <NAME> VERLOREN |
| abgewiesen (Kennwort, voll) | ABGEWIESEN: <GRUND> |

Bei einer falschen Version bleibt die Tafel mit beiden Versionen stehen
(12b), Esc fuehrt dann nach Hause statt aus dem Spiel. Die laufende
Runde wird vorher wie jeder Abbruch gebucht (12e). Ohne `heimkehr` - nur
in Pruefungen, die ein Gefecht von Hand bauen - bleibt es beim Alten:
Hinweis und Esc.

Der **Gastgeber** hat keinen Eintrag "verlassen": er ist der Server.
"GEFECHT VERLASSEN" heisst bei ihm "alle zurueck in die Lobby"
(`lobby_betreten`). *SPIEL BEENDEN* haben alle; vom Hauptmenue aus
gestartet fuehrt es dorthin zurueck.

### Die Suche (`lan.py`)

UDP, Port `NETZ["such_port"]` = 50504, ohne Server:

    Sucher  -> Rundruf  "DUSTFRONT?"
    Ansager -> Absender {"name","port","version","spieler","hoechstens",
                         "lobby","modus","karte","passwort","kennung"}

* **Gefragt wird, nicht gerufen.** Nur wer die Liste offen hat, fragt
  (alle `such_takt` = 1,5 s); nur wer gefragt wird, antwortet. Eine Lobby,
  die `such_vergessen` = 5 s nicht geantwortet hat, faellt heraus.
* **Drei Ziele je Frage:** 255.255.255.255, der Rundruf des eigenen
  /24-Netzes (Windows mit mehreren Netzkarten schickt den ersten nur auf
  einer hinaus) und 127.0.0.1.
* **`kennung`** ist eine Zufallszahl je Lobby. Sie haelt die eigene Lobby
  aus der eigenen Liste und fasst zusammen, was ueber zwei Wege antwortet
  (127.0.0.1 und die Netzadresse; die Netzadresse gewinnt).
* **Alles aus dem Netz wird geprueft** (`eintrag_pruefen`): kaputtes JSON,
  Ports ausserhalb 1-65535, Namen mit fremden Zeichen. Beitreten ist
  danach eine ganz normale Verbindung mit allen Pruefungen des Gastgebers
  (Version, Kennwort, Platz) - die Liste verspricht nichts.
* Das **Kennwort** geht nie hinaus, nur *ob* eines gilt. Wer eine Lobby
  mit Kennwort anklickt und keines eingetragen hat, wird erst danach
  gefragt.
* Eine Lobby mit anderer Version oder ohne freien Platz steht in der
  Liste, ist aber gesperrt und sagt warum.

Mehrere Lobbys auf einem Rechner teilen sich den Suchport
(`SO_REUSEADDR`, unter macOS zusaetzlich `SO_REUSEPORT`). Geht der Port
nicht auf, laeuft die Lobby trotzdem, sie ist nur nicht zu finden -
beitreten per Adresse geht weiterhin.

### Rundentafel: einfach und erweitert, Standardrunde

Gemeldet: "Menues fuer neue Spieler: Rundeneinstellungen in einfach und
erweitert, mit einer definierten Standardrunde."

* **Einfach** zeigt nur, was `regeln.EINFACH` nennt: Spielart, Karte,
  Runden, Endart und Dauer, Haltezeit, Schwierigkeit, Ausruestung. Alles
  andere steht unter **ERWEITERT** und behaelt dort seinen Wert. Die
  Wahl gilt je Spieler und bleibt stehen (`runden_erweitert` in
  `einstellungen.json`).
* Ist unter ERWEITERT etwas verstellt, sagt die einfache Ansicht es in
  einer Zeile (`regeln.verborgen_geaendert`) - sonst wundert man sich,
  warum die Munition knapp ist.
* **Standardrunde** (`K.STANDARDRUNDE`, `regeln.standardrunde`): TEAM auf
  STAUBTAL, zehn Minuten, jeder hat alles. Damit plant jede frische Lobby,
  und der Knopf STANDARDRUNDE setzt die gewaehlte Runde darauf zurueck.
  Fehlt die Karte, nimmt sie die eingebaute.

### Name ohne Konto

Angemeldet heisst man wie das Konto. Sonst gilt der Name aus der
Lobbysuche (`einstellungen.json`, `spielername`), und ganz ohne
`SPIELER` plus das Ende der eigenen Adresse (`SPIELER27`) - sonst hiesse
jede Lobby im Netz gleich.

### Internet

Die Startdatei dafuer ist mit LAN-GASTGEBER weggefallen. Es geht ueber
`python -m dustfront --host --online --passwort GEHEIM` (7.9); die anderen
tragen die Adresse in der Lobbysuche unter ADRESSE ein.

### Was im Netz wann dazukam (fuer die Fehlersuche)

Gewuenscht: "Wenn du etwas hinzufuegst, was Auswirkungen auf das LAN hat,
sag Bescheid - dann weiss ich, woran es liegt, wenn es spaeter nicht
geht." Darum hier jede Aenderung daran, was das Spiel im Netz oeffnet oder
schickt. **Neue Eintraege kommen unten dazu**, mit Version.

| Seit | Wer | Richtung | Port | Wofuer | Wenn es blockiert ist |
| --- | --- | --- | --- | --- | --- |
| 0.13 | Gastgeber | eingehend | TCP 50505 | das Spiel selbst | niemand kann beitreten |
| 0.13 | Gast | ausgehend | TCP 50505 | das Spiel selbst | Beitreten scheitert ("KEINE ANTWORT") |
| 0.19 | Gastgeber mit `--online` | Router, UPnP (UDP 1900, HTTP) | - | Port im Router freigeben | nur Internet betroffen, LAN nicht |
| 0.20 | alle mit Konto | ausgehend | HTTPS 443 | Supabase (Konto, Zahlen) | Spielen geht, Zahlen warten im Journal |
| 0.32 | **jeder** (eigene Lobby) | eingehend | TCP 50505, bei Belegung bis 50512 | die eigene Lobby | man kann anderen beitreten, aber niemand einem selbst |
| 0.32 | **jeder** (eigene Lobby) | eingehend | UDP 50504 | Antwort auf die Lobbysuche | die eigene Lobby steht bei anderen nicht in der Liste |
| 0.32 | wer die Lobbysuche offen hat | ausgehend, Rundruf | UDP 50504 | Lobbys im Netz finden | Liste bleibt leer - Adresse von Hand geht weiter |

Was seit 0.32 anders ist als bei den Playtests davor: Frueher oeffnete nur
der Gastgeber einen Port, jetzt jeder (jeder sitzt in seiner eigenen
Lobby). Darum kann die Firewall- oder Virenschutzabfrage jetzt bei allen
erscheinen. Wegklicken schadet dem Beitreten nicht. Und die Lobbysuche
braucht Rundrufe (Broadcast) im Netz; manche Firewalls und WLANs lassen die
nicht durch, dann bleibt nur die Adresse von Hand (sie steht in jeder
Lobby oben links).

Nicht im Netz, aber ebenfalls zwischen den Rechnern: was beide **gleich**
haben muessen. Der Gast laedt die Karte aus seinem eigenen Ordner, nur
ihr Name kommt ueber das Netz.

| Seit | Was | Wenn es nicht passt |
| --- | --- | --- |
| 0.32.27 | C4-Ladungen, ihre 5-Sekunden-Ladezeit und Admin-Befehle laufen ueber die bestehende Welt- und Eingabemeldung; der Brecher hat eine vergroesserte Trefferflaeche | Gastgeber und Gaeste muessen dieselbe Version haben, sonst fehlen C4-Zuenderstatus oder Trefferabgleich |
| 0.32.26 | Der Brecher hat 95 Leben und eine dunklere Gestalt ohne Bruststreifen | Gastgeber und Gast brauchen dieselbe Version, damit Gegnerwerte uebereinstimmen; kein Protokollwechsel |
| 0.32.24 | RPG-Schaden und Explosionsradius wurden auf 150 und 104 Weltpixel erhoeht | Gastgeber und Gast brauchen dieselbe Version, damit Treffer gleich berechnet werden |
| 0.32.23 | Die Endmeldung enthaelt je Spieler die MVP-Punkte und MVP-Auszeichnung der Runde | Gastgeber und Gast brauchen dieselbe Version, sonst kennt der Gast die MVP-Zeile nicht |
| 0.32.11 | STAUBTAL hat zwei neue Kachelarten (Aufzug `^` und `v`) | eine alte Version kennt sie nicht und saehe dort Boden - darum wird die Version beim Beitreten verglichen, und ein alter Gast wird abgewiesen |

Das persoenliche Music Kit wird vom eigenen Konto geladen und nur auf dem
eigenen Rechner fuer Sieg und Niederlage abgespielt. Es wird nicht ueber
das Gefecht an andere verteilt. Auf dem Kontoserver muss vorher die neue
Spalte samt Groessenpruefung aus `docs/KONTO.md`, Abschnitt 5.6, angelegt
und die aktualisierte ADMIN-Funktion aus Abschnitt 5.8 eingespielt sein.

**0.32.12:** Gameplay-Randfehler im gemeinsamen Spielerkern behoben:
verzoegerte Medkits heilen keine toten oder am Boden liegenden Spieler,
Waffenwechsel bricht die Heilung ab, Stuerze beenden den Dash, und
Geschosse mit Nulltempo loesen beim Treffer keinen Absturz aus. Kartenraender
gelten nicht als Loecher, dadurch wechseln Raketen dort nicht ungewollt die
Ebene. Das Drahtprotokoll bleibt gleich; Gastgeber und Gast muessen wegen
des geaenderten Spielverhaltens dieselbe Version verwenden.

**0.32.13:** Das Weltpaket schickt zusaetzlich `df`, die verbleibende Zeit
der Dash-Bildfolge. Damit zeichnet der Gast dieselben Nachbilder und den
Ausklang wie der Gastgeber. Kein neuer Port; aeltere Versionen kennen das
Feld nicht und werden wie ueblich beim Beitritt abgewiesen.

**0.32.14:** Die Dash-Animation wurde visuell ueberarbeitet. Das Netzpaket,
die Karte und die Mehrspielerregeln bleiben unveraendert.

**0.32.15:** Dash-Windlinien und Medkit-Pixelkorrektur sind rein visuell;
Netzpaket und Karten bleiben unveraendert.

**0.32.16:** Windlinien bauen sich nacheinander auf und das Muendungsfeuer
sitzt vor dem Lauf. Rein visuell; Netzpaket und Karten bleiben unveraendert.

**0.32.18:** Das Gefecht meldet jetzt auch Nachladen, Zu-Boden-Gehen und den
Rundenstart als Klangereignisse an Gaeste weiter. Der vorhandene Nahkampfeffekt
enthaelt ausserdem die Trefferart (organisch/metallisch), damit der Gast den
gleichen Einschlag wie der Gastgeber hoert. Kein neuer Port; wegen der neuen
Ereignisse muessen Gastgeber und Gaeste dieselbe Version nutzen.

**0.32.19:** Der lokale Nahkampfeingabeweg spielt keinen zusaetzlichen
Platzhalterklang mehr ab. Der Schwung- oder Trefferklang kommt wie zuvor aus
dem gemeldeten Welt-Ereignis; das Paketformat und die Netzereignisse bleiben
unveraendert. Gastgeber und Gast muessen wegen des Klangverhaltens dieselbe
Spielversion verwenden.

## 13. Was fehlt

**OFFEN**, bewusst, weil es ein Test war:

* **Keine Vorhersage beim Gast.** Ueber das Internet unspielbar. Wer das
  will, braucht Eingabepuffer, Rueckrechnung und Korrektur - das ist mehr
  Arbeit als der ganze jetzige Mehrspieler.
* **`NETZ["stumm_nach"]` wird nicht benutzt.** Ein Gast, dessen Rechner
  einfach stehen bleibt, faellt erst auf, wenn TCP die Leitung abbricht.
  Die Zahl steht bereit, die Pruefung fehlt.
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
* ~~Kein Wegesucher.~~ Seit 0.27 gibt es ihn (`wege.py`, 12b). Die
  Haengerwache bleibt als Rueckfall.

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
python -m dustfront --lobby
python -m dustfront --host --name MEISTER --modus huegel --ende zeit --wert 600
python -m dustfront --join 192.168.1.7:50505 --name GAST
python -m dustfront --bestenliste
```

`--modus` ist einer von `pvp pve pvpve team versus huegel`, `--ende` ist
`zeit` oder `abschuesse`, `--knapp` begrenzt die Munition. Zum Spielen
ohne Kommandozeile `DUSTFRONT.bat` bzw. `.command` starten und im
Hauptmenue MEHRSPIELER waehlen.

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

**Spielerkosmetik (0.28):** zu kurz, zu lang, falsches Format, ein Kopf,
der mehr Proben behauptet, als da sind; der Ton wird immer leiser, endet in
Stille, kein Abschnitt liegt ueber der Grenze, ein Knall, der schnell genug
abklingt, bleibt unangetastet; PNG zu gross, kaputt, kein PNG; Teile in
falscher Reihenfolge, falscher Fingerabdruck; das Konto merkt sich die
eigene und vergisst eine abgelehnte. Im Netz mit drei echten Rechnern:
alle bekommen alles, ein Neuer sperrt MIT KOSMETIK, bis er alles hat,
gefaelschte Pakete werden abgelehnt, mit Kosmetik klingt und zeigt die
Blendgranate den Werfer - beim Gastgeber wie beim Gast, im Bild
nachgewiesen -, ohne Kosmetik und ohne Werferkosmetik knallt sie wie immer;
aendern, entfernen und gehen kommen bei allen an.

**In `tests/kontoseite_browser.py`** (Chromium ueber Playwright, mit
vorgetaeuschtem Server): die Grenze der Seite ist Probe fuer Probe die des
Spiels; WAV und MP3 laden, zu kurz abgelehnt, Zuschneiden mit der Maus
bleibt in den Grenzen; was die Seite hochlaedt, nimmt das Spiel an und es
klingt dort wie in der Vorschau; entfernen loescht die Zeile; fehlt die
Tabelle, sagt die Seite, was zu tun ist.

---

## 17. Der eine Satz zum Merken

Der Gastgeber rechnet, der Gast zeigt an. Alles, was der Gast sehen soll,
muss in der Weltmeldung stehen - und alles, was nur einen Augenblick lang
wahr ist, muss gesammelt werden, bevor es ins Paket geht.
