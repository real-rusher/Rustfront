# Fahrzeuge fuer grosse Karten (Plan, Stand 0.34.110)

Zwoelf Entwuerfe fuer die SCHLACHT auf Karten, die groesser sind als
STAUBTAL - OFFEN. Bilder und Szenen dazu stehen auf der Entscheidungsseite
(Artifact "DUSTFRONT Fahrzeugkonzepte"); die Zeichner liegen dort als
`quelle/*.py.txt`. Hier steht, was der Besitzer entschieden hat und was
davon eingebaut ist.

## Entscheidungen

| Fahrzeug | Entscheidung | Stand |
| --- | --- | --- |
| KRAD | behalten; der Fahrer hat keine Waffe | **0.34.107** |
| JAGDPANZER | behalten; grosse, von vorn gepanzerte "Sniper" gegen Panzer | **0.34.107** |
| TROSSWAGEN | behalten; kein Aufsitzen - hinten dranstellen, mit E einmal Munition und ein Medkit (begrenzter Gesamtvorrat). Gegnerische Trosswagen lassen sich pluendern. Nicht per Drop anforderbar, einige erscheinen regelmaessig an der Basis. Fahrzeuge heilen nur, solange sie hinten dranhaengen (auch im Stehen) | **0.34.108** |
| SPULENWAGEN | behalten; EMP-Feld einschaltbar, dafuer muss der Wagen aufgebaut sein, es pulsiert am Ort, nur begrenzte Zeit, danach aufladen; schwaecherer Kettenblitz | **0.34.110** |
| FUNKWAGEN | behalten; Bots, die mit ihm sprechen koennen, geben ihre Daten direkt ins Funknetz des Teams (nur mit aktivem Funk). Stoeren bleibt, aber er steht dabei auf der Karte | offen |
| WERFER | behalten; schiesst nur im Umkreis gueltiger Ziele (von jemandem im Team gesehene oder markierte Gegner und Fahrzeuge, Hotzones, spaeter weitere Objectives). Sehr leicht zu zerstoeren, dann grosse Explosion, die alle im Umkreis toetet. Jeder Schuss verraet ihn kurz auf Karte oder Minikarte, mit eigenem Symbol | offen |
| FLAKWAGEN | behalten; nur Bots fahren ihn (sie spawnen darin oder werden damit gedroppt), weil Spieler nicht zwischen Boden- und Luftzielen wechseln koennen | offen |
| TRAGSCHRAUBER | behalten; das Zielproblem fuer Spieler loesen. Es soll spaeter mehr Hubschrauber geben, und man soll auf andere Etagen schiessen koennen | offen |
| GLEITER, RAEUMER, LADUNGSTRAEGER | verworfen | - |
| LANDSCHIFF | **verworfen fuer diese Entwicklungsphase, aber gemerkt**: die fahrende Basis mit Plaetzen fuer Fahrer, Hauptturm und vier Seitentuerme, Einstieg der Gefallenen am Heck. Konzept und Zeichner liegen auf der Entscheidungsseite | zurueckgestellt |

## Reihenfolge

1. Krad, Jagdpanzer (0.34.107)
2. Trosswagen (0.34.108)
3. Spulenwagen (0.34.110), Funkwagen, Werfer (Werfer und Funkwagen gehoeren zusammen)
4. Luftziele: Flakwagen und Tragschrauber, mit einer Regel, wie Spieler
   Luftziele und andere Etagen anvisieren

Vorschlag fuer die Luftziel-Regel (noch nicht entschieden): die Maus zielt
weiter in der Ebene; liegt der Zeiger auf dem *Bild* eines Luftziels (nicht
auf seinem Schatten), geht der Schuss auf das Luftziel. Dieselbe Regel
koennte fuer Helis und fuer Ziele auf anderen Etagen gelten.

## Was 0.34.107 gebaut hat

* `dustfront/fahrzeug.py`: `Krad(Buggy)` und `Jagdpanzer(Panzer)`, in
  `ARTEN`. Werte in `K.KRAD` und `K.JAGDPANZER`, Panzerung in
  `K.PANZERUNG`, Kanone `K.FAHRZEUG_WAFFEN["jagdkanone"]`.
* Krad: Beifahrer ueber die Aufsitz-Logik des Panzerwagens
  (`mehrspieler._transporter_bei`, `_mitfahren`), aber mit Waffe; das
  Geschoss kennt seinen Traeger (`entities.Geschoss`), sodass der Beifahrer
  das eigene Krad nicht trifft. Kein Schutz im Fahrzeug
  (`Kaempfer._fahrzeug_werte`, `fahrer_geschuetzt=False`).
* Jagdpanzer: Rohr schwenkt um `schwenk` Grad (`_aufbau_fuehren`),
  Zielfernrohr auf der rechten Maustaste (`Gefecht.scope_an`), eigene
  Seitenfaktoren (`werte["seiten"]`), `nur_mensch`.
* Bilder: `dustfront/art_neue_fahrzeuge.py`. Skins faellt auf die Farben der
  Mannschaft zurueck (kein Skin-Muster fuer die neuen Arten).
* SCHLACHT: eines mehr je Basis (Krad), Nachschub `krad` (3) und
  `jagdpanzer` (10); die Tafel hat zehn Zeilen.

## Was 0.34.108 gebaut hat

* `Trosswagen(Buggy)` in `dustfront/fahrzeug.py`, Werte `K.TROSSWAGEN`
  (Physik vom Panzerwagen, kein Aufsitzen, `nur_mensch`). Zone hinter dem
  Wagen (`zone_mitte`, `in_zone`), Reparatur eigener Fahrzeuge dort
  (`_reparieren`, `seite_von`).
* Nachschub holen: `Gefecht._nachschub_nehmen` (E hinten, vor dem
  Einsteigen). Hinweis in `_fahrzeug_hinweis`, Vorrat im Netz als Feld 17.
* Bild: `trosswagen_zeichnen` in `dustfront/art_neue_fahrzeuge.py` (der Fahrer
  sitzt unter dem Verdeck und ist nicht zu sehen).
* SCHLACHT: einer je Basis (`SCHLACHT["fahrzeuge"]`), nicht im Nachschub.

## Was 0.34.110 gebaut hat

* `Spulenwagen(Buggy)`, Werte `K.SPULENWAGEN` (Physik wie der Trosswagen,
  `blitz`, `feld`). Phasen 0 bereit / 1 baut auf / 2 Feld aktiv / 3 laedt;
  in 1 und 2 steht er. Der Puls (`_puls`) legt fremde Fahrzeuge und Technik
  im Kreis still, eigene nicht (`seite_von`). Der Blitz (`_blitz`) wie der
  Kettenblitz zu Fuss, nur schwaecher.
* Die Maustasten des Fahrers gelten fuer Fahrzeuge mit `schiesst = True`
  (`Gefecht._fahren`). Bodenkranz: `Gefecht._spulen_zeichnen`.
* Die Nachschubtafel hat eine Zeile je Eintrag (Platz fuer bis zu 14).
