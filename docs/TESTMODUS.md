# Testmodus

Seit 0.34.28. Ein eigener Modus zum schnellen Ausprobieren neuer Sachen:
aus dem Hauptmenue (**TESTMODUS**) oder mit

```
python -m dustfront --testmodus [--karte NAME]
```

Am Rechner wird er ueber den Ziffernblock und die Maus bedient, seit
0.34.63 auch auf iPhone und iPad mit dem Finger (siehe "Mit Touch"
unten). Alles steht in `dustfront/testmodus.py`, die Zahlen in
`dustfront/config.py` unter `TESTMODUS`.

## Mit Touch (iPhone, iPad, seit 0.34.63)

Am Rechner zum Ausprobieren mit `DUSTFRONT_TOUCH=1`.

| Was | Wie |
| --- | --- |
| Ziffernblock | antippen, wie mit der Maus. Ein Finger auf einer Taste wird nie ein Stick |
| Fliegen | linker Stick (linke Bildhaelfte, wie Laufen im Spiel) |
| Zeiger (wo 1, 2, 5, 3 und ENTF wirken) | rechter Stick |
| Zoomen | zwei Finger auf derselben Seite auseinander oder zusammen |
| Spawner (4) | Eintrag antippen; in die Welt tippen setzt ihn dort. Eine Einstellung rechts antippen: vor, im linken Drittel: zurueck (`K.TESTMODUS["touch_zurueck"]`). Zwei Finger blaettern in der Liste. ESC oben rechts schliesst |
| Testmenue | NUM (MENUE) oder II; Zeilen antippen wie die Einstellungen im Spawner |
| Eine Figur steuern (3) | wie im Spiel, mit allen Knoepfen. Der Ziffernblock klappt dann unter die Taste **NUM** oben (`K.TESTMODUS["touch_num"]`), sonst laege er unter Dash, E und Zielen. NUM klappt ihn auf und zu |

Der Beobachter hat nur die Knoepfe II (Testmenue) und EBN (obere Ebenen) -
Nachladen oder Dash braucht er nicht. Direkt im Testmodus starten:
`ios/aufspielen.sh --testmodus` (setzt `DUSTFRONT_START=testmodus`, das
geht am Rechner genauso).

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
| FIGUREN | Bot, Fahrer mit / ohne Fahrzeug, Schildträger, Spieler (steht), Spieler (ich) | Anzahl, Streuung, Team (ROT, BLAU, FREI), Waffe (auch fuer Spieler, seit 0.34.62), Leben, Aussehen (ZUFALL, STANDARD oder ein Skin; bei Spieler (ich) als Vorgabe EIGENES); beim Bot HIRN (KLASSISCH / GOAP, docs/KI.md) |
| GEGNER, BOSSE | jede Art aus `K.GEGNER` und `K.BOSSE` | Anzahl, Streuung, Leben, KI an/aus, HIRN (KLASSISCH / GOAP) |
| ZIELE | die Zielpuppe | Anzahl, Streuung |
| OBJEKTE | Buggy, Panzer, Panzerwagen, Nagelfeld, Hotzone hier, Hotzone aus | Anzahl, Streuung, Richtung |
| BEUTE | Medkit, Munitionskiste, Raketenwerfer | Anzahl, Streuung |
| WURF | Granate, Rauch, Molotow, Blendgranate, Haftladung, EMP-Granate, Gasgranate, Kuller, Knaller, Schneeball | Anzahl, Streuung, Zuender (liegt / sofort) |
| NPC | Haendler, Aerztin, Wissenschaftler, Fluechtling, Pilger, Schmuggler, Hirte, Ueberlebende | Anzahl, Streuung, Richtung; bei der Ueberlebenden das Stirnband |
| TIERE | Schaf, Ziege, Huhn | Anzahl, Streuung, Farbe (drei je Tier oder ZUFALL) |
| WAFFENBILDER | Figur mit Waffe (jede der 52 aus dem Waffenpaket) | Waffe, Team, Richtung |
| BAUEN, FALLEN, AUFKLÄRUNG, HILFE | Sandsackwand, Stacheldraht; Sprengfalle (Platte, Draht), Selbstschussanlage, Benzinkanister; Spaehdrohne, Horchposten; Sanitasche, Munitionskiste (seit 0.34.69, nur im Testmodus) | Anzahl, Streuung, Team, Richtung |
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
| 0.34.143 | Keine neuen Spawner-Eintraege. Krad zu zweit: ein Bot-Fahrer auf einem KRAD (FAHRER mit Fahrzeug) und ein BOT daneben - er sitzt im Beiwagen auf; die INFO-Ansicht (Taste 8) zeigt WARTET AUF BEIFAHRER, ZU ZWEIT, > KREIST und beim Beifahrer IM BEIWAGEN. Panzerbuechse: ein BOT mit PANZERBUECHSE vor einem PANZER mit PUPPE als Fahrer. Flammenwerfer: PUPPE mit FLAMMENWERFER als Waffe. Motoren: jeden Wagen setzen und fahren. |
| 0.34.142 | Keine neuen Spawner-Eintraege. Die INFO-Ansicht (Taste 8) zeigt FERN bei Bots, die weiter als 1200 px von jedem Menschen weg sind: sie denken seltener und rechnen im halben Takt. Im Testmodus nur, wenn man eine Figur selbst steuert (sonst gibt es keinen Menschen). |
| 0.34.140 | Keine neuen Spawner-Eintraege. Schwimmen: auf FLUSSTAL mit ICH oder einer PUPPE ins tiefe Wasser gehen (langsam, kein Schuss, nur der Kopf oben). Kolonne: zwei FAHRER MIT FAHRZEUG hintereinander setzen; die INFO-Ansicht (Taste 8) zeigt beim Hinteren "> KOLONNE" und eine tuerkise Linie zum Vordermann, bei Gegenverkehr "> RECHTS HALTEN". Szene in `tests/test_verhalten.py`: `kolonne`. |
| 0.34.139 | Keine neuen Spawner-Eintraege: FAHRER MIT FAHRZEUG (Buggy, Panzerwagen ...) setzen, ein leeres FAHRZEUG oder einen eigenen Mann (ZIELPUPPE, eigene Seite) auf seinen Weg stellen und zusehen, wie er vorausschauend um sie herumfaehrt, statt dagegen zu schieben. Szene in `tests/test_verhalten.py`: `ausweichen`. |
| 0.34.138 | Keine neuen Spawner-Eintraege; alles mit vorhandenen ausprobieren: FAHRZEUG TROSSWAGEN und dahinter ein leeres FAHRZEUG setzen, einsteigen, rechte Maustaste haengt an (Seil), noch einmal koppelt ab. Zwei Fahrzeuge gegeneinander fahren: leichte werden geschoben, schwere nur von schweren. FAHRZEUG FLAKWAGEN laesst sich jetzt selbst fahren. Nachschub-Abwuerfe zeigen die neue Abwurfzone (Fackeln, Rauch, Groesse je Fahrzeug). In GRAFIK: BESTE QUALITAET BEIM ZOOM. |
| 0.34.135 | Keine neuen Spawner-Eintraege. Werfer-Zielzonen ausprobieren: FRONT an, FAHRZEUG WERFER mit Team setzen, einsteigen, aufbauen - die Karte zeigt die Zonen tuerkis; AUFKLAERUNGSDROHNE (Nachschub) laesst 25 s eine Spur zurueck. |
| 0.34.133 | Keine neuen Spawner-Eintraege. Ausprobieren: FLUSSTAL laden, FRONT an, je Seite zehn Bots setzen, INFO (8): wenige Gruppen biegen zu einem Kampf ab, die anderen gehen weiter ihr Ziel; Stosstrupps (1-2) gehen hinter die Front. |
| 0.34.132 | Keine neuen Spawner-Eintraege (JE SEITE gilt nur in SCHLACHT-Runden). |
| 0.34.131 | Spawner OBJEKTE: EROBERUNGSPUNKT (TEAM = Besitzer), STARTBASIS (TEAM), WASSER: SEICHT und WASSER: TIEF (RADIUS; LEEREN nimmt es wieder weg) - ein Punkt oder eine Basis schaltet die Front ein. Testmenue FRONT: PUNKTE, GRUPPEN, FORMATIONEN (auf FLUSSTAL und KANALSTADT gleich mit den Punkten der Karte) und FRONT: PUNKTE VERTEILEN (ENTER: alle ROT, alle BLAU, frei, geteilt). INFO (8) zeigt je Gruppe den Weg, Linien zu den Formationsplaetzen und ueber dem Anfuehrer `G3 KEIL GEHT > B NORDBRÜCKE`. Bots fahren jetzt jedes Fahrzeug: FIGUREN, FAHRER MIT FAHRZEUG, FAHRZEUG WERFER/TRAGSCHRAUBER/... |
| 0.34.130 | Keine neuen Spawner-Eintraege. Ausprobieren: eine Figur mit SPIEGELLASER (oder einer anderen Chor-Waffe) steuern und durchfeuern - sie ueberhitzt, Kuehlton, KÜHLT am Zeiger; wegstecken und weiterschiessen. NACHSCHUB: NAPALM - dem Bomber nachhoeren, die Bomben fallen sehen, das neue Feuer. KUGELBLITZ: kleinere Blitze. |
| 0.34.129 | Zeile RESPAWN im Testmenue (wie im Escape-Menue einer Runde, fuer die gesteuerte Figur; 3 zum Steuern). Am Boden R halten gibt auf (mit VERWUNDETE BOTS oder einem Treffer am Boden ausprobieren). FREISCHALTEN gilt nur in SCHLACHT - ausprobieren in einer SCHLACHT-Runde mit kurzer Zeit (5 MIN) oder AUS. Pruefungen im Abschnitt 0.34.129 von `tests/test_spiel.py` |
| 0.34.127 | Keine neuen Spawner-Eintraege. Ausprobieren: TRAGSCHRAUBER fliegen und mit FLAKWAGEN (Bot, anderes Team) abschiessen lassen oder ENTF auf ihn: der Pilot ist sofort tot, das Wrack faellt brennend weiter und schlaegt auf; gegen eine Mauer geflogen prallt es ab. WERFER mit ENTF: die dichtere Explosion. |
| 0.34.126 | Keine neuen Spawner-Eintraege. Ausprobieren: KRAD oder BUGGY driften und gegen eine Wand fahren - kein Rutsch-Ton. WERFER aufbauen und schiessen: Rueckstrahl und Einschlaege als Teilchenwolken, das Gestell gemalt wie die anderen Fahrzeuge; ENTF auf den Werfer: die grosse Explosion. FUNKWAGEN aufbauen: der Mast ohne schwarzen Umriss, liegend kaum zu sehen. |
| 0.34.125 | Keine neuen Spawner-Eintraege. Ausprobieren: eine Salve des WERFERS oder eine Granate: nach dem Einschlag liegen keine schwarzen Quadrate mehr. FUNKWAGEN aufbauen: alle vier Seile gleich duenn. Als Video: `python werkzeug_aufnahme.py funkwagen werfer werfer_explosion schrottbombe flak krad` |
| 0.34.124 | Keine neuen Spawner-Eintraege (Funkwagen, Werfer, Tragschrauber, Flakwagen, Krad und Jagdpanzer stehen schon im Spawner). Ausprobieren: FUNKWAGEN setzen, mit der Figur einsteigen, rechte Maustaste: der Mast richtet sich auf, faehrt aus, der Kopf klappt auf, die Seile laufen aus, dann dreht sich der Kopf; noch einmal rechts: alles rueckwaerts. WERFER aufbauen und den Zeiger nah und weit setzen: die Rohre stehen nah steil, weit flacher. TRAGSCHRAUBER mit Bombe, FLAKWAGEN mit Bot gegen ihn: Schrottbombe und Leuchtspur. Pruefungen in den Abschnitten 0.34.123 und "Funkwagen: der Mast als 3D-Modell" von `tests/test_spiel.py` |
| 0.34.115 | Keine neuen Spawner-Eintraege (der Funkwagen steht schon im Spawner). Ausprobieren: FUNKWAGEN setzen (Team waehlen), mit der Figur einsteigen, rechte Maustaste = aufbauen, R = STOEREN; dann ICH (Beobachter -> Figur des anderen Teams) in den Kreis: die Minikarte rauscht, nur der Funkwagen steht als Ping darauf. Zwei Funkwagen mit sich deckenden Kreisen = zwei Pings. TRUPP mit Funk in den Kreis: der Spruch bricht ab (INFO/Funkring grau mit Kreuz). Pruefungen im Abschnitt "Gestoerte Minikarte" von `tests/test_spiel.py` |
| 0.34.114 | Spawner OBJEKTE: FLAKWAGEN (leer: nur ein Bot kommt hinein), NACHSCHUB: ABWURF: FLAKWAGEN (landet mit einem Bot am Steuer). FIGUREN: FAHRER MIT FAHRZEUG, FAHRZEUG FLAKWAGEN setzt einen Bot gleich hinein. Ausprobieren: einen Tragschrauber des anderen Teams fliegen lassen (oder ABWURF: MUNITION/SANITAETS fuer Team 1 setzen), Taste 8 (INFO): der Flak-Bot zeigt "> FLAK" mit einer Linie zum Bild des Ziels. Pruefungen im Abschnitt "Flakwagen" von `tests/test_spiel.py` |
| 0.34.113 | Spawner OBJEKTE: TRAGSCHRAUBER, NACHSCHUB: ABWURF: TRAGSCHRAUBER. Ausprobieren: SPIELER, ICH mit E einsteigen, Gas halten (ab 100 px/s hebt er ab), linke Maustaste Bombe, E landet. Zum Draufschiessen eine zweite Figur (Team 1, STEHT mit Waffe, oder einen BOT) setzen und die Maus auf das *Bild* des Tragschraubers legen - nicht auf den Schatten. Ein ABWURF (NACHSCHUB) ist ein Luftziel, das nur Flak trifft. Pruefungen im Abschnitt "Tragschrauber und die Luftziel-Regel" von `tests/test_spiel.py` |
| 0.34.112 | Spawner OBJEKTE: WERFER, NACHSCHUB: ABWURF: WERFER. Ausprobieren: SPIELER, ICH (Team 0) mit E einsteigen, rechte Maustaste baut auf; einen Gegner (Team 1) setzen und einen Kameraden (Team 0) in seiner Naehe: der Zeiger wird gruen, die linke Maustaste schiesst die Salve. Ohne Kamerad in der Naehe bleibt er rot (KEIN GÜLTIGES ZIEL); mit FUNKWAGEN im Kreis oder dem Spawner HOTZONE HIER gilt es auch. ENTF auf den Werfer zeigt die grosse Explosion. Pruefungen im Abschnitt "Werfer" von `tests/test_spiel.py` |
| 0.34.111 | Spawner OBJEKTE: FUNKWAGEN, NACHSCHUB: ABWURF: FUNKWAGEN. Ausprobieren: SPIELER, ICH (Team waehlen) mit E einsteigen, rechte Maustaste baut auf, R schaltet PEILEN/STOEREN; einen Gegner (Team 1) in den Kreis setzen und sehen, dass er markiert wird; einen BOT mit FUNKSPRUECHE-Regel im Kreis des Gegners setzen (er funkt nicht mehr). Pruefungen im Abschnitt "Funkwagen" von `tests/test_spiel.py` |
| 0.34.110 | Spawner OBJEKTE: SPULENWAGEN, NACHSCHUB: ABWURF: SPULENWAGEN. Ausprobieren: SPIELER, ICH mit E einsteigen; linke Maustaste Blitz, rechte baut das Feld auf (im Stand), einen PANZER daneben setzen und mit INFO sehen, dass er stillsteht (EMP-Rest). Pruefungen im Abschnitt "Spulenwagen" von `tests/test_spiel.py` |
| 0.34.109 | Nichts Neues zum Setzen: FAHRER MIT FAHRZEUG und SPIELER, ICH mit AUSSEHEN zeigen den Skin jetzt auch im Krad und im Jagdpanzer. Pruefungen im Abschnitt "0.34.109" von `tests/test_spiel.py` |
| 0.34.108 | Spawner OBJEKTE: TROSSWAGEN (Anzahl, Streuung, Richtung); FAHRER MIT FAHRZEUG kennt ihn nicht (nur Menschen am Steuer). Ausprobieren: SPIELER, ICH hinter den Wagen stellen und E druecken (Munition und Medkit, `[E] NACHSCHUB (n)` steht dort), einen beschaedigten PANZER hinten dranstellen (repariert sich). Pruefungen im Abschnitt "Trosswagen" von `tests/test_spiel.py` |
| 0.34.107 | Spawner OBJEKTE: KRAD und JAGDPANZER (Anzahl, Streuung, Richtung); Spawner NACHSCHUB: ABWURF: KRAD und ABWURF: JAGDPANZER; FAHRER MIT FAHRZEUG kennt beide (der Bot faehrt das Krad, nicht den Jagdpanzer). Zum Ausprobieren: SPIELER, ICH oder Taste 3, mit E einsteigen. Krad: ein zweiter Spieler setzt sich mit E in den Beiwagen und schiesst; der Jagdpanzer schwenkt nur 12 Grad, rechte Maustaste ist das Zielfernrohr. Pruefungen im Abschnitt "Krad und Jagdpanzer" von `tests/test_spiel.py` |
| 0.34.101 | Spawner, Gruppe NACHSCHUB: NAPALM-ANGRIFF - die Bahn beginnt am Zeiger und fuehrt in Richtung WINKEL; das Flugzeug hoert man nur, die Feuer liegen unregelmaessig mit Luecken. Bots laufen aus den Feuern (mit INFO sieht man ihre Gefahrenkreise wie beim Molotow). Pruefungen in `tests/test_spiel.py` (Abschnitt 0.34.101) und `python tests/test_verhalten.py napalm` |
| 0.34.100 | Spawner, Gruppe NACHSCHUB: ABWURF: MUNITION / MEDKITS / BUGGY / PANZERWAGEN / PANZER (am Fallschirm, weicht aus, wenn unten ein Wagen, ein anderer Abwurf oder Fels liegt; wer drunter steht, wird beiseite gestossen), AUFKLÄRUNGSDROHNE (grosser Starrfluegler hoch oben, markiert Leute und Fahrzeuge) und FALLSCHIRMJÄGER (fuenf Bots der gewaehlten Seite im Keil). Mit INFO (Taste 8) steht ueber Springern AM SCHIRM und die Hoehe, und wer gegen sie in Stellung geht, zeigt > SPRINGER: IN STELLUNG mit einer Linie zur Landestelle. Pruefungen in `tests/test_spiel.py` (Abschnitt 0.34.100) und `python tests/test_verhalten.py fallschirmjaeger` |
| 0.34.96 | KARTE: STAUBTAL_OFFEN. SPÄHDROHNE fliegt ueber allem (mit Schatten). WAFFE/Loadout: Nahkampfwaffen liegen auf F. Bots: VORSTOSS zeigt mit INFO weiter Basen und Mitte; Panzer am Steuer nehmen zuerst Fahrzeuge. Dropzonen und Nachschub gibt es nur in SCHLACHT (Rundenregel), Pruefungen in `tests/test_spiel.py` (Abschnitte 0.34.96) |
| 0.34.95 | Spawner: PANZERJÄGER (Panzerbuechse und Raketen). Testmenue: BOTS: VIELE WAFFEN (wie in Runden, Vorgabe aus), BOTS: PANZERJÄGER (BEI FAHRZEUGEN), BOTS: VORSTOSS WIE IN SCHLACHT - mit INFO stehen dann BASIS ROT, BASIS BLAU und MITTE als Kreise im Bild. FAHRER MIT FAHRZEUG zeigt das Funkgeraet (Wellen ueber der Antenne), solange der Bot faehrt; ein Panzerwagen, den ein Bot faehrt, nimmt den Spieler mit E hinten auf. SPÄHDROHNE: weiter Kreis, ihre Markierungen im Nebel. Flammenwerfer (WAFFE) als Feuerzunge. Pruefungen in `tests/test_spiel.py` (Abschnitte 0.34.95) und `python tests/test_verhalten.py vorstoss` |
| 0.34.94 | Bots ziehen das MG nur noch selten (K.BOTS waffen_gewicht); GEMISCHT behaelt seinen einen MG-Schuetzen. Fahrzeuge stehen flach (kein 3D mehr). `python tests/test_verhalten.py` laeuft die Szenen gleichzeitig auf allen Kernen (`--seriell` nacheinander); Pruefungen in `tests/test_spiel.py` (Abschnitt 0.34.94) |
| 0.34.91 | Testmenue NEBEL (SICHTWEITE) steht als Vorgabe auf AUS - ALLES SICHTBAR (einschalten wie bisher). Bots mit Spulengewehr zielen beim Laden ruhiger, und ohne Gegner im Blick drehen sich Bots nicht mehr ganz um sich selbst (Drehbremse) - zu sehen in der INFO-Ansicht; Pruefungen in `tests/test_spiel.py` (Abschnitt 0.34.91) und `python tests/test_verhalten.py drehen` |
| 0.34.88 | Der Beobachter hat immer eine Minikarte (ALLWISSEND: jeder darauf); in ANSICHT WIE RUNDE ist der Ziffernblock auch fuer Finger und Maus weg. Pruefungen im Abschnitt "Testmodus: Minikarte beim Beobachter" von `tests/test_spiel.py` |
| 0.34.87 | Nichts Neues zum Setzen; Spule, Revolver, Kuller, Granatwerfer und Drohne ausprobieren wie bisher (Spawner bzw. Ausruestung). Pruefungen im Abschnitt "Waffen: Spule, Revolver, Hotbar, Kuller, Granatwerfer, Drohne" von `tests/test_spiel.py` |
| 0.34.85 | Nichts Neues zum Setzen. Die Werkzeuge aller Klassen gibt es im Testmodus schon im Spawner (BAUEN, FALLEN, AUFKLÄRUNG, HILFE); JEDER HAT ALLES mit Gruppen-Hotbar und Taste X gilt in Runden ohne Loadouts. Pruefungen im Abschnitt "Jeder hat alles: Kategorien-Hotbar" von `tests/test_spiel.py` |
| 0.34.84 | INFO-Ansicht: ein Fahrer, der einen liegenden Kameraden deckt, zeigt "FÄHRT ... > DECKT LIEGENDEN" und eine gruene Linie zu dem Platz, an den er faehrt. Ausprobieren: FAHRER mit Panzer setzen, einen Bot seines Teams und einen Gegner, den Bot zu Boden bringen. Pruefungen in `tests/test_verhalten.py` (fahrzeug_bots) |
| 0.34.80 | INFO-Ansicht (Taste 8): **Spuren** der Bots - wo ein verschwundener Gegner zuletzt war, als lila Kreuz; die Spur, die er gerade prueft, mit gestrichelter Linie. Ausprobieren: einen Bot einen Gegner sehen lassen, den Gegner wegsetzen. Pruefungen in `tests/test_verhalten.py` (spuren, feuer_umweg) und im Abschnitt "Bots: Spuren statt vergessen" von `tests/test_spiel.py` |
| 0.34.79 | Nichts Neues zum Setzen: die Faehigkeiten der Klassen galten hier schon immer (`faehigkeiten_an` fest an). Neu sichtbar: die Anzeige **[C]** ueber dem Lebensbalken (bereit oder Sekunden). Im Gefecht und in der Lobby gelten sie jetzt auch (Regel KLASSEN-FAEHIGKEITEN). Pruefungen im Abschnitt "Klassen und neue Waffen in der Lobby" von `tests/test_spiel.py` |
| 0.34.77 | Testmenue ANSICHT WIE RUNDE (auch Taste **F2**): kein Ziffernblock, kein Status, kein Zeiger, keine Kreise, keine INFO - die Welt sieht aus wie in einer normalen Runde; Spawner und Menue gehen trotzdem auf. MINIKARTE ALLWISSEND: alle Kaempfer in ihren Farben, Zombies, Bosse und Tiere, auch als Beobachter. NACHSCHUB AM KARTENRAND: alle 3 s ein GOAP-Bot fuer die kleinere Seite (0 von Westen, 1 von Osten), bis 24 Bots (`K.TESTMODUS["nachschub"]`). Alle drei bleiben ueber einen Kartenwechsel. Pruefungen im Abschnitt "Kein Flimmern, Schild, Fahrzeug schuetzt, Testmodus" von `tests/test_spiel.py` |
| 0.34.73 | FIGUREN: BOT und SPIELER, ICH haben eine KLASSE (K.KLASSEN): Waffen aus ihrer Auswahl, ihre Vorteile, und mit Figur legt Taste C ihre Faehigkeit hin (Sanitasche, Munitionskiste, Selbstschussanlage, Sprengfalle, Sandsackwand, Kraehenfuesse, Drohne, Horchposten, Stacheldraht, Kanister; jede mit Pause). Pruefungen im Abschnitt "Klassen" und "Balancing" von `tests/test_spiel.py` |
| 0.34.72 | Jede neue Waffe, jeder Wurf und jedes Ding der Ausruestung klingt nach sich selbst - im Testmodus mit BILDRATE (KLAENGE PRUEFEN) zu hoeren. Pruefungen im Abschnitt "Klaenge fuer Waffenpaket, Fahrzeuge und Ausruestung" von `tests/test_spiel.py` |
| 0.34.71 | FIGUREN: FAHRER MIT FAHRZEUG (Panzer, Panzerwagen oder Buggy, der Bot sitzt am Steuer und kaempft), FAHRER OHNE FAHRZEUG (geht zum naechsten freien und steigt ein), SCHILDTRÄGER (Schild von vorn, Pistole). TRUPPS: TRUPP AUS VORLAGE (PANZERZUG, MOT. SCHÜTZEN, SCHILDWALL, SPÄHTRUPP, STURMTRUPP; jedes Mitglied mit eigenem Aussehen, Waffe und Wurfwaffe, mit Fahrzeug samt Fahrer). Die INFO-Ansicht zeigt FÄHRT ..., SUCHT FAHRZEUG und SCHILD. Pruefungen im Abschnitt "Bots fahren, Schildtraeger, Trupp-Vorlagen" von `tests/test_spiel.py` und "Ein Bot faehrt den Panzer und kaempft" in `tests/test_verhalten.py` |
| 0.34.70 | BOT: WAFFE kennt jetzt alle Waffen, und der Bot kaempft damit (Nahkampf heran, Spule voll laden, Flamme in Reichweite). Bots meiden Feuer, Gas, entdeckte Fallen, Stacheldraht und scharfe Wuerfe - zu sehen, wenn man eine Brandflaeche oder Gaswolke (WURF, Zuender sofort) auf sie setzt. Pruefungen im Abschnitt "Bots: Gefahren und neue Waffen" von `tests/test_spiel.py` und "Bots meiden brennenden Boden" in `tests/test_verhalten.py` |
| 0.34.69 | Neue Spawner-Gruppen (TEAM: wem es gehoert, RICHTUNG): BAUEN (Sandsackwand, Stacheldraht), FALLEN (Sprengfalle mit Platte oder Draht, Selbstschussanlage, Benzinkanister), AUFKLÄRUNG (Spaehdrohne, Horchposten), HILFE (Sanitasche, Munitionskiste). Testmenue: FERNGLAS (mit Figur: markiert im Kegel zum Zeiger). Markierte Gegner zeigt eine rote Raute; INFO (Taste 8) zeigt versteckte Fallen, Draht, Reichweite und Ziel des Geschuetzes, den Kreis der Drohne und die Welle des Horchpostens. Pruefungen im Abschnitt "Bauen, Fallen, Aufklaerung, Hilfe im Testmodus" von `tests/test_spiel.py` |
| 0.34.68 | FIGUREN: WAFFE kennt Spulengewehr, Kettenblitz, Spiegellaser, Kugelblitz und Flammenwerfer (SPIELER, ICH; eine Puppe oder ein paar Zombies als Ziel). Pruefungen im Abschnitt "Energiewaffen und Flammenwerfer" von `tests/test_spiel.py` |
| 0.34.67 | WURF: GASGRANATE, KULLER, KNALLER, SCHNEEBALL (Zuender liegt / sofort). FIGUREN: WAFFE kennt Wurfmesser und Speer (rechte Maustaste wirft, darueberlaufen hebt auf). Haftladung und EMP blinken. Pruefungen im Abschnitt "Wuerfe aus dem Waffenpaket" von `tests/test_spiel.py` |
| 0.34.66 | FIGUREN: WAFFE kennt Vorschlaghammer, Schockstab, Schlagring, Kettensaege, Bolzenschussgeraet und Nagler (SPIELER, ICH zum Ausprobieren, eine Puppe als Ziel). Die INFO-Ansicht (Taste 8) zeigt bei Bots BETÄUBT, GEFROREN und FEST; ueber jeder Figur ist der Zustand auch ohne INFO zu sehen. Das NAGELFELD wirkt nur noch auf Reifen. Pruefungen im Abschnitt "Nahkampf, Bolzer, Nagler, Zustaende" von `tests/test_spiel.py` |
| 0.34.65 | WURF: HAFTLADUNG (klebt an Fahrzeug oder Figur, faehrt mit) und EMP-GRANATE (legt Fahrzeuge still); OBJEKTE: NAGELFELD. Die INFO-Ansicht (Taste 8) zeigt unter jedem Fahrzeug Leben, den letzten Treffer (Schadensart, Seite, Anteil, was ankam), EMP- und Platt-Rest und die Ladungen fuer Hecknebel und Naegel. Am Steuer (SPIELER, ICH, dann E) wirft R Hecknebel und F den Nagelstreuer. Pruefungen im Abschnitt "Fahrzeug-Panzerung, Haftladung, EMP, Hecknebel, Nagelstreuer" von `tests/test_spiel.py` |
| 0.34.63 | Der Testmodus auf iPhone und iPad (und am Rechner mit `DUSTFRONT_TOUCH=1`), siehe "Mit Touch" oben: Ziffernblock antippen, linker Stick fliegt, rechter bewegt den Zeiger; Spawner und Testmenue mit dem Finger (links auf eine Einstellung: zurueck), zwei Finger blaettern im Spawner; mit Figur klappt der Ziffernblock unter NUM. Neu auch am Rechner: das Mausrad blaettert in der Liste des Spawners, und `DUSTFRONT_START=testmodus` startet gleich im Testmodus. Pruefungen im Abschnitt "Testmodus mit Touch" von `tests/test_spiel.py` |
| 0.34.62 | FIGUREN: SPIELER, STEHT und SPIELER, ICH haben eine WAFFE - ALLE ist die Hotbar wie bisher, jede andere Wahl ein Loadout mit dieser Waffe vorn (dazu Sturmgewehr und Granate), auch eine der zwoelf neuen. So laesst sich jede neue Waffe selbst ausprobieren (SPIELER, ICH) oder an einer Puppe zeigen. BOT kann die neuen ebenfalls tragen (WAFFE), schiesst aber nur mit Schusswaffen. Pruefungen im Abschnitt "Die Waffen aus dem Waffenpaket, spielbar" von `tests/test_spiel.py` |
| 0.34.61 | Spawner WAFFENBILDER: FIGUR MIT WAFFE - eine stehende Figur, die eine der 52 Waffen aus dem Waffenpaket haelt (WAFFE, TEAM, RICHTUNG). Nur das Bild: sie schiesst nicht, faellt aber um wie ein NPC. Pruefungen im Abschnitt "Waffenbilder aus dem Waffenpaket" von `tests/test_spiel.py` |
| 0.34.60 | Skins, NPCs und Tiere aus dem Figurenpaket. FIGUREN: Einstellung AUSSEHEN (ZUFALL - beim Bot sein Soldat wie im Spiel -, STANDARD, oder einer der 29 Skins); SPIELER, ICH nimmt als Vorgabe das eigene Aussehen aus AUSRUESTUNG. Neue Gruppen NPC und TIERE: NPCs stehen (Verhalten kommt mit der Kampagne), Tiere laufen ein Stueck und bleiben stehen; die INFO-Ansicht (Taste 8) zeigt eine gruene Linie zum Laufziel und LAEUFT bzw. STEHT. Beide nehmen Schaden, sterben mit Fleck und Laut, ENTF toetet sie; niemand greift sie an (Fraktion `zivil`). Pruefungen im Abschnitt "Skins, NPCs und Tiere" von `tests/test_spiel.py` |
| 0.34.59 | Spawner OBJEKTE: PANZER und PANZERWAGEN (Anzahl, Streuung, Richtung). Passt einer nicht an den Zeiger, sucht er den naechsten freien Platz. Zum Fahren eine Figur setzen (SPIELER, ICH, oder Taste 3) und mit E einsteigen: W/S fahren, A/D drehen, die Maus zielt, linke Maustaste Kanone bzw. Ring-MG, rechte Bug-MG. Zum Rammen GEGNER mit KI AUS vor die Front setzen. ENTF TOETET laesst ihn hochgehen (Wrack). Aufnahmen `panzer` und `panzerwagen` in `werkzeug_aufnahme.py`. Pruefungen im Abschnitt "Panzer und Panzerwagen" von `tests/test_spiel.py` |
| 0.34.58 | Testmenue BILDRATE (KLAENGE PRUEFEN): WIE EINGESTELLT, 30, 15, 8 oder 4 BILDER/S; bleibt ueber einen Kartenwechsel. Zum Hoeren: einen Bot oder eine gesteuerte Figur mit Sturmgewehr oder LMG feuern lassen und die Bildrate senken - die Schuesse kommen im gleichmaessigen Takt, auch wenn das Spiel unter 24 Bildern in Zeitlupe laeuft. Pruefungen im Abschnitt "Klaenge" von `tests/test_spiel.py`. Testmenue BOTS UEBERMUETIG: AUS (Vorgabe) oder AN - wie FLIEHEN, bleibt ueber einen Kartenwechsel; AN geht ein zuversichtlicher Trupp in "druck" und verlaesst die Deckung (INFO zeigt beim Trupp Zustand und ZUV). Marsch: einen TRUPP ohne Gegner setzen - er geht im Keil hinter dem Anfuehrer, haelt ab und zu zum Sichern (die anderen schauen zur Seite und nach hinten), um Ecken der Spur nach; mit mehr als fuenf Mann in kleinen Keilen hintereinander. Ein ANGRIFF-Auftrag in der Naehe oder ein bekannter Gegner: die Linie. Die Trupp-Anzeige zeigt die Plaetze, INFO beim Trupp MARSCH, (SICHERT) waehrend eines Halts und (WARTET) bei dem, dessen Platz die Spur des Anfuehrers noch nicht erreicht hat. Funk: zu sehen mit zwei Trupps, einer in der Unterzahl - der Funker zeigt einen Haken und drei Ringe, wenn der Spruch durch ist (mit Klang), ein rotes Kreuz und einen Ring, der zusammenfaellt, wenn er abbricht. ZEIT STEHT: Lebende stehen still (vorher zitterten sie). Als Beobachter rufen Liegende nicht um Hilfe (kein "!", kein Zittern, kein Ruf), als Spieler weiter. Pruefungen im Abschnitt "Testmodus" von `tests/test_spiel.py` und `python tests/test_verhalten.py marsch` |
| 0.34.57 | Nichts Neues zum Einschalten - der Testmodus laeuft schneller, am deutlichsten mit vielen Trupps und VERWUNDETE BOTS (Bergung). Die Bots entscheiden wie vorher - Sicht und Deckung geben auf jede Frage dieselbe Antwort. Pruefungen im Abschnitt "Bildrate" von `tests/test_spiel.py` |
| 0.34.56 | Testmenue BOTS FLIEHEN IN PANIK: AUS - WIE IN RUNDEN (Vorgabe) oder AN - WIE KAMPAGNE; bleibt ueber einen Kartenwechsel. Zu sehen mit INNENLEBEN PANIK auf einem Bot im Freien: AUS wechselt er die Deckung, AN rennt er weg (INFO GEDANKEN zeigt `darf_fliehen`). Verhaltens-Test `python tests/test_verhalten.py keine_flucht` |
| 0.34.55 | Nichts Neues zum Einschalten - die Fehler sind behoben: mit VERWUNDETE BOTS und zwei Liegenden nebeneinander greift der Helfer den Richtigen, INFO (Stufe GEDANKEN) zeigt beim Aufhelfen den Fakt `hilft_schon`, und das Umschauen geht nur noch zur Flanke. Verhaltens-Tests `python tests/test_verhalten.py planer bergen_fluessig drehen` |
| 0.34.54 | Testmenue NEBEL (SICHTWEITE): AUS - ALLES SICHTBAR hebt den Nebel jenseits des normalen Bildes auf, herausgezoomt sieht man jeden Gegner bis an den Rand (bleibt ueber einen Kartenwechsel). Feuerschutz beim Bergen zu sehen mit VERWUNDETE BOTS und einem Gegner, der schiesst (Bot oder selbst gesteuert): die anderen stehen auf AUS DECKUNG FEUERN / NIEDERHALTEN; Verhaltens-Test `python tests/test_verhalten.py feuerschutz` |
| 0.34.53 | INFO zeigt beim Bergen wie bisher den Retter; neu ist nur, dass es einer ist und die anderen ZUR STELLE/AUS DECKUNG in Deckung bleiben - zu sehen mit VERWUNDETE BOTS und Szene `bergen_puppen`; Verhaltens-Test `python tests/test_verhalten.py bergen` |
| 0.34.52 | Mit festem Zufall (`tm._bot_rnd.seed(n)`) stellt der Testmodus jedes Mal dasselbe auf - Trupps, Spawner, Merkmale, Namen; darauf baut die neue Verhaltens-Suite `tests/test_verhalten.py` (Szenen nach der Schlacht, Schusslinie, Deckung, geknickte Front, Bergen, Last; einzeln: `python tests/test_verhalten.py bergen`) |
| 0.34.51 | INFO zeigt bei geknickter Front jeden Abschnitt als eigene Linie mit Strich zu seiner Gruppe; `sauber_trupps` (fuer Aufnahmen): Trupps auch in der sauberen Ansicht; Szene `abschnitte` |
| 0.34.50 | Testmenue BOTS SPRINTEN (AN/AUS); Sprechblase ueber dem, der gerade zuruft; Zurufe unten links (hell) neben dem Funk; INFO zeigt Ausdauer (Balken), FLANKIERT und eine orange Linie zu dem, der auf ihn schoss; neue Aktionen umstellen (Ziel flanke_sichern) in GEDANKEN |
| 0.34.48 | Funkwellen rot, gestrichelt, drehend, erst wenn der Funker spricht; Szenen `mauer`, `panik`, `bergen_mauer`, `ueberfall`; neue Aktion deckung_wechseln (GEDANKEN); Arme und Ring beim Ziehen und Aufhelfen |
| 0.34.46 | Funkwellen rot, klein, am Boden unter dem Funker (`_funkwellen_zeichnen`); ueber Liegenden steht VERWUNDET statt der letzten Aktion |
| 0.34.44 | Wirklich kein "[E] AUF" mehr ueber Liegenden fuer den Beobachter (auch `_darf_helfen`); Szene `deckung` (aus der Deckung feuern, Panik = verkriechen) |
| 0.34.43 | Funksprueche als Wellen vom Funker (Ringe, solange er spricht; wer den Spruch bekommt, blinkt); der Text steht weiter unten links. Neue Bot-Aktionen aus_deckung_feuern und verkriechen erscheinen in GEDANKEN; Panik ausloesen geht mit INNENLEBEN: PANIK |
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
