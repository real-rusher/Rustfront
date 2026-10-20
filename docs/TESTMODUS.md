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
| 8 | INFO: was die KI denkt (Linien zu Ziel, Flanke, Deckung, Sammelpunkt; Zustand ueber jedem Bot, Ziel jedes Gegners) |
| 4 | Spawner auf / zu |
| 5 | Den zuletzt gespawnten Eintrag noch einmal am Zeiger |
| 6 | Gottmodus: AUS, UNVERWUNDBAR, UNSTERBLICH, UNSICHTBAR, ALLES |
| 1 | Ein Bot am Zeiger (Team und Waffe aus dem Spawner) |
| 2 | Ein Spieler am Zeiger, der nichts tut |
| 3 | Die Figur am Zeiger uebernehmen (ein Bot ruht so lange) - oder eine neue; noch einmal: zurueck zum Beobachter |
| Enter | Loeschen, was am Zeiger liegt |
| NUM (anklicken) / Esc | Testmenue |

## Der Spawner (Taste 4)

Links eine Liste von allem, was sich setzen laesst, rechts dessen
Einstellungen. **Pfeile** waehlen, **Tab** wechselt zu den Einstellungen,
**links/rechts** verstellt, **Enter** setzt am Zeiger - oder einfach in
die Welt **klicken**. Geht auch bei angehaltener Zeit; was man dann
setzt, steht sofort da.

| Gruppe | Eintraege | Einstellungen |
| --- | --- | --- |
| FIGUREN | Bot, Spieler (steht), Spieler (ich) | Anzahl, Streuung, Team (ROT, BLAU, FREI), Waffe, Leben |
| GEGNER, BOSSE | jede Art aus `K.GEGNER` und `K.BOSSE` | Anzahl, Streuung, Leben, KI an/aus |
| ZIELE | die Zielpuppe | Anzahl, Streuung |
| OBJEKTE | Buggy, Hotzone hier, Hotzone aus | Anzahl, Streuung, Richtung |
| BEUTE | Medkit, Munitionskiste, Raketenwerfer | Anzahl, Streuung |
| WURF | Granate, Rauch, Molotow, Blendgranate | Anzahl, Streuung, Zuender (liegt / sofort) |

## Das Testmenue (Esc)

Karte (Enter laedt, die Einstellungen bleiben), neu laden, Zeit,
Zeitfaktor, KI, Flugtempo, jeder Gottmodus einzeln (unverwundbar,
unsterblich, unsichtbar fuer KI, unendlich Munition), Wiedereinstieg
toter Figuren, Zombiewellen, Beute nachlegen, Blenden und Ruckeln des
Beobachters, die gewoehnlichen Einstellungen, zurueck zum Hauptmenue.

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
| 0.34.28 | Der Testmodus selbst: Beobachter, Ziffernblock, Spawner fuer Figuren, alle Gegner und Bosse, Zielpuppe, Buggy, Hotzone, Beute und Wurfwaffen; Gottmodi; INFO-Ansicht fuer Bots (auch Flanke, Niederhalten, Sturm aus 0.34.27) |
