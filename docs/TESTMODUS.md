# Testmodus

Seit 0.34.28. Ein eigener Modus zum schnellen Ausprobieren neuer Sachen:
aus dem Hauptmenue (**TESTMODUS**) oder mit

```
python -m dustfront --testmodus [--karte NAME]
```

Nicht auf iPhone und iPad: bedient wird er ueber den Ziffernblock und
die Maus. Alles steht in `dustfront/testmodus.py`, die Zahlen in
`dustfront/config.py` unter `TESTMODUS`.

## Der Beobachter

Man faengt als Beobachter an: keine Figur, nur eine Kamera, die mit
**W A S D** fliegt (mit **Umschalt** dreimal so schnell, Tempo im
Testmenue). Das **Mausrad** zoomt.

**Nichts in der Welt nimmt den Beobachter wahr oder trifft ihn - auch
nichts, was spaeter dazukommt.** Er steht in keiner Liste, die
irgendetwas im Spiel befragt: nicht in `welt.wesen` (Kugeln,
Explosionen, Stoesse) und nicht in `kaempfer` (Bots, Gegner, Beute).
Blendgranaten und Kameraruckeln treffen ihn auch nicht (im Testmenue
einschaltbar, wenn man sehen will, wie es aussieht).

## Der Ziffernblock

Steht immer am rechten Bildrand, jede Taste mit ihrer Wirkung. Die
Tasten lassen sich auch **anklicken** (fuer Tastaturen ohne Ziffernblock).

| Taste | Wirkung |
| --- | --- |
| 0 | Zeit anhalten / weiterlaufen lassen - fuer **alles**: Wesen, Partikel, Uhren der Bots |
| . | Ein Schritt (1/10 Sekunde), haelt die Zeit dabei an |
| + / - | Zeitfaktor: x0,1 bis x4 |
| / | KI aus / an - Bots und Gegner stehen, schiessen und schlagen nicht |
| * | Leeren: alles weg ausser der Figur, die man gerade steuert |
| 7 / 9 | Ebene runter / hoch |
| 8 | INFO: AUS, KURZ, GEDANKEN. KURZ: was die KI denkt (Linien zu Ziel, Flanke, Deckung, Sammelpunkt; Zustand ueber jedem Bot, bei GOAP `ZIEL > AKTION`; Ziel jedes Gegners). GEDANKEN: dazu links die GOAP-Figur am Zeiger - Merkmale, jedes Ziel mit Dringlichkeit, Plan, wahre Fakten, Zahlen, Protokoll |
| 4 | Spawner auf / zu |
| 5 | Den zuletzt gespawnten Eintrag noch einmal am Zeiger |
| 6 | Gottmodus: AUS, UNVERWUNDBAR, UNSTERBLICH, UNSICHTBAR, ALLES |
| 1 | Ein Bot am Zeiger (Team und Waffe aus dem Spawner) |
| 2 | Ein Spieler am Zeiger, der nichts tut |
| 3 | Die Figur am Zeiger uebernehmen (ein Bot ruht so lange) - oder eine neue; noch einmal: zurueck zum Beobachter |
| Enter | Loeschen, was am Zeiger liegt - oder, mit ENTF-TASTE: TOETET im Testmenue, toeten: es stirbt wie im Spiel, mit Fleck und Todeslaut (ein Buggy geht hoch) |
| NUM (anklicken) / Esc | Testmenue |

## Der Spawner (Taste 4)

Links eine Liste von allem, was sich setzen laesst, rechts dessen
Einstellungen. **Pfeile** waehlen, **Tab** wechselt zu den Einstellungen,
**links/rechts** verstellt, **Enter** setzt am Zeiger - oder einfach in
die Welt **klicken**. Geht auch bei angehaltener Zeit; was man dann
setzt, steht sofort da.

| Gruppe | Eintraege | Einstellungen |
| --- | --- | --- |
| FIGUREN | Bot, Spieler (steht), Spieler (ich) | Anzahl, Streuung, Team (ROT, BLAU, FREI), Waffe, Leben; beim Bot HIRN (KLASSISCH / GOAP, docs/KI.md) |
| GEGNER, BOSSE | jede Art aus `K.GEGNER` und `K.BOSSE` | Anzahl, Streuung, Leben, KI an/aus, HIRN (KLASSISCH / GOAP) |
| ZIELE | die Zielpuppe | Anzahl, Streuung |
| OBJEKTE | Buggy, Hotzone hier, Hotzone aus | Anzahl, Streuung, Richtung |
| BEUTE | Medkit, Munitionskiste, Raketenwerfer | Anzahl, Streuung |
| WURF | Granate, Rauch, Molotow, Blendgranate | Anzahl, Streuung, Zuender (liegt / sofort) |
| TRUPPS | Trupp; Halten hier, Angriff hier, Frei, Igel hier (fuer den naechsten Trupp der Mannschaft) | Groesse, Team, Anfuehrer (mit Funk / ohne Funk / keiner), Waffen (gemischt / zufall), Leben; beim Halten: wichtig |

## Das Testmenue (Esc)

Karte (Enter laedt, die Einstellungen bleiben), neu laden, Zeit,
Zeitfaktor, KI, Flugtempo, INFO, KI-DATEN NEU LADEN (liest `wesen/*.txt`
neu und gibt jeder GOAP-Figur ein neues Gehirn), ZIEL ERZWINGEN (der
Figur in der Gedankenansicht ein Ziel aufzwingen, links/rechts blaettert,
"-" laesst sie wieder frei denken), INNENLEBEN (links/rechts waehlt, Enter
loest es an der gezeigten GOAP-Figur aus: Panik, Stress, Kamerad faellt,
Granate neben ihm, Ruhe), jeder Gottmodus einzeln (unverwundbar,
unsterblich, unsichtbar fuer KI, unendlich Munition), Wiedereinstieg
toter Figuren, Zombiewellen, Beute nachlegen, Blenden und Ruckeln des
Beobachters, SAUBERE ANSICHT (nur die Welt und ueber jedem Kopf die
Aktion - kein Ziffernblock, keine Tafeln, kein Funk, herausgezoomt ohne
Nebel; fuer Aufnahmen), ENTF-TASTE (LOESCHT: weg ohne Spur; TOETET:
stirbt mit Fleck und Todeslaut), VERWUNDETE BOTS (Bots liegen erst und
koennen einmal geborgen und wiederbelebt werden), die gewoehnlichen
Einstellungen, zurueck zum Hauptmenue.

## Aufnahmen

`python werkzeug_aufnahme.py` rechnet fertige Szenen im Testmodus und
schreibt sie als Video mit Ton nach `aufnahmen/` (braucht ffmpeg); `--liste`
zeigt die Szenen, Namen dahinter nehmen nur diese auf. `--zeitlupe` legt je
Szene eine Fassung in halbem Tempo dazu, `--ohne-ton` laesst den Ton weg. Eine neue Szene ist
eine Funktion `szene_NAME` und ein Eintrag in `SZENEN`.

## Was nicht passiert

Gebucht wird nichts - keine Runde, kein Abschuss, keine Statistik. Der
Testmodus lauscht nur lokal und hat ein Zufallskennwort: beitreten kann
niemand.

## Neue Features

**Jedes neue Feature muss im Testmodus ausprobierbar sein** - im Spawner,
als Taste oder als Zeile im Testmenue (siehe `AGENTS.md`, Abschnitt
Testmodus). Diese Seite bekommt dazu eine Zeile:

| Seit | Was im Testmodus dazukam |
| --- | --- |
| 0.34.42 | Kein "[E] AUF" mehr ueber Liegenden, solange man Beobachter ist |
| 0.34.41 | Spawner TRUPP: IGEL HIER (einigeln am Zeiger); INFO zeigt Igelplatz, Engstelle mit Breite und die Blickrichtung jedes Manns; Szenen `igel` und `engstelle` |
| 0.34.40 | Testmenue VERWUNDETE BOTS (vorgegeben AN): Bots fallen erst zu Boden, werden geborgen (Rauch, in Deckung ziehen, aufhelfen) und einmal wiederbelebt, danach geschwaecht; der zweite Tod hinterlaesst eine andere Leiche, die nach sechs Sekunden verschwindet. ENTF TOETET legt einen Bot erst hin. INFO zeigt die Bergung (Kreis, Bedrohung, Retter); GEDANKEN zeigt GESCHWAECHT; Szene `bergen` |
| 0.34.39 | Spawner-Gruppe TRUPPS: TRUPP (Groesse, Team, Anfuehrer mit/ohne Funk/keiner, Waffen gemischt/zufall, Leben), TRUPP: HALTEN HIER (wichtig), TRUPP: ANGRIFF HIER, TRUPP: FREI; INFO zeigt Frontlinie, Stellungen, Zustand und die letzten Funksprueche, ein Funkspruch steht mit Balken ueber dem, der funkt (auch in der sauberen Ansicht); GEDANKEN mit Rolle und Lage im Trupp; Szenen `trupp` und `hilferuf` in `werkzeug_aufnahme.py` |
| 0.34.38 | INFO KURZ zeigt unter jedem GOAP-Bot Stress (Balken), Zuversicht (P B N Z H), PANIK/SCHRECK und Kreise mit Linien zu dem, was er hoert; GEDANKEN zeigt Stress, Zuversicht, Panik, Schreck, eingeschossen, Bindung und Bedenkzeit; Testmenue INNENLEBEN (PANIK, STRESS +0,3, KAMERAD FAELLT, GRANATE NEBEN IHM, RUHE) fuer die gezeigte Figur |
| 0.34.35 | `werkzeug_aufnahme.py` mit Ton (`Tonband`) und `--zeitlupe` |
| 0.34.34 | Kein eigener Eintrag: ENTF-TASTE TOETET loest jetzt Fleck und Todeslaut aus (die Leiche ist wieder draussen) |
| 0.34.33 | Testmenue ENTF-TASTE: LOESCHT / TOETET - jeden Tod am Zeiger ausloesen; Szene `tod` in `werkzeug_aufnahme.py` |
| 0.34.32 | Testmenue SAUBERE ANSICHT; `werkzeug_aufnahme.py` nimmt Szenen als Video auf |
| 0.34.31 | Nichts Neues zum Ausprobieren; zwei GOAP-Fehler behoben, die die Gedankenansicht in Aufnahmen gezeigt hat (SUCHEN hinter einer Kiste, der Kreis in HUEGEL) |
| 0.34.30 | Zombies und Bosse mit GOAP: Spawner GEGNER/BOSSE mit HIRN, KURZ zeigt `ZIEL > AKTION` auch ueber ihnen, GEDANKEN, ZIEL ERZWINGEN und KI-DATEN NEU LADEN gelten fuer sie mit |
| 0.34.29 | Zielorientierte KI: Spawner BOT mit HIRN KLASSISCH / GOAP, INFO-Stufe GEDANKEN (Taste 8 zweimal), Testmenue ZIEL ERZWINGEN und KI-DATEN NEU LADEN |
| 0.34.28 | Der Testmodus selbst: Beobachter, Ziffernblock, Spawner fuer Figuren, alle Gegner und Bosse, Zielpuppe, Buggy, Hotzone, Beute und Wurfwaffen; Gottmodi; INFO-Ansicht fuer Bots (auch Flanke, Niederhalten, Sturm aus 0.34.27) |
