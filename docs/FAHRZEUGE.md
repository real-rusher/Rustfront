# Fahrzeuge fuer grosse Karten (Plan, Stand 0.34.120)

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
| FUNKWAGEN | behalten; Bots, die mit ihm sprechen koennen, geben ihre Daten direkt ins Funknetz des Teams (nur mit aktivem Funk). Stoeren bleibt, aber er steht dabei auf der Karte | **0.34.111** |
| WERFER | behalten; schiesst nur im Umkreis gueltiger Ziele (von jemandem im Team gesehene oder markierte Gegner und Fahrzeuge, Hotzones, spaeter weitere Objectives). Sehr leicht zu zerstoeren, dann grosse Explosion, die alle im Umkreis toetet. Jeder Schuss verraet ihn kurz auf Karte oder Minikarte, mit eigenem Symbol | **0.34.112** |
| FLAKWAGEN | behalten; nur Bots fahren ihn (sie spawnen darin oder werden damit gedroppt), weil Spieler nicht zwischen Boden- und Luftzielen wechseln koennen | **0.34.114** |
| TRAGSCHRAUBER | behalten; das Zielproblem fuer Spieler loesen. Es soll spaeter mehr Hubschrauber geben, und man soll auf andere Etagen schiessen koennen | **0.34.113** |
| GLEITER, RAEUMER, LADUNGSTRAEGER | verworfen | - |
| LANDSCHIFF | **verworfen fuer diese Entwicklungsphase, aber gemerkt**: die fahrende Basis mit Plaetzen fuer Fahrer, Hauptturm und vier Seitentuerme, Einstieg der Gefallenen am Heck. Konzept und Zeichner liegen auf der Entscheidungsseite | zurueckgestellt |

## Reihenfolge

1. Krad, Jagdpanzer (0.34.107)
2. Trosswagen (0.34.108)
3. Spulenwagen (0.34.110), Funkwagen (0.34.111), Werfer (0.34.112; Werfer und Funkwagen gehoeren zusammen)
4. Luftziele: Flakwagen und Tragschrauber, mit einer Regel, wie Spieler
   Luftziele und andere Etagen anvisieren

Die Luftziel-Regel (seit 0.34.113 gebaut, der Vorschlag war): die Maus zielt
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

## Was 0.34.111 gebaut hat

* `Aufbauwagen(Buggy)` (Phasen fahren / baut auf / aufgebaut, rechte
  Maustaste) und `Funkwagen(Aufbauwagen)` in `dustfront/fahrzeug.py`,
  Werte `K.FUNKWAGEN`. Die Wirkung steht im Gefecht:
  `funkwagen_schritt` (markieren, stoeren), `funk_gestoert` (Bots, Nachschub),
  `_funk_hoert` (Funknetz ueber `lage_melden`).
* Zusatzwert je Art in der Fahrzeugmeldung (`netz_extra`, Feld 20) - der Werfer
  nutzt ihn fuer seine Einschlaege.
* Nachgereicht in 0.34.115: die Minikarte im Stoerkreis rauscht (nur Pings der
  Funkwagen), der Truppfunk wird gestoert (siehe unten).

## Was 0.34.112 gebaut hat

* `Werfer(Aufbauwagen)`, Werte `K.WERFER`. Regeln im Gefecht:
  `werfer_ziele` (gueltige Ziele der Seite: gesehen, markiert, Hotzone;
  Erweiterungspunkt fuer spaetere Objectives), `werfer_pruefen`,
  `werfer_schritt`, `_werfer_salve`, `_werfer_einschlag`; Zeichnen:
  `_werfer_zeichnen_boden` (rote Kreise, Zeiger), `_raketen_zeichnen`.
* Zeichen auf Minikarte und Nachschubkarte: `Minikarte.werfer_zeichen`.
* Ohne bekannte Seite (Testmodus ohne Team) gilt jeder Punkt als Ziel.

## Was 0.34.113 gebaut hat

* `dustfront/luft.py` (`LuftTeil`): `luft_ziele` (heute Tragschrauber,
  Spaehdrohnen, Abwuerfe am Schirm, Fallschirmjaeger), `luft_zielen`
  (Einrasten nach jeder Eingabe), `flaechenschaden` (Bomben, Raketen),
  `tragschrauber_schritt`, `_luftfahrzeuge_zeichnen`. Kugeln tragen ihr
  `luft_ziel` (`entities.Geschoss`) und treffen nur dieses.
* `Tragschrauber(Buggy)` mit Bodenphase und Flugphase (`_fliegen`, Landung,
  Absturz), Werte `K.TRAGSCHRAUBER`.
* Abwuerfe und Fallschirmjaeger sind Luftziele, aber nur fuer Flak
  (`nur_flak`): gewoehnliche Waffen rasten dort nicht ein - bis der Flakwagen
  da ist, aendert sich fuer sie nichts. Mit der Regel koennte man den Flakwagen
  auch Menschen geben; entschieden ist: nur Bots.

## Was 0.34.114 gebaut hat

* `Flakwagen(Panzerwagen)` (`fahrzeug.py`), Werte `K.FLAKWAGEN`, Waffe
  `FAHRZEUG_WAFFEN["flak_mg"]`, Gewichtung gegen Luftziele `K.FLAK`.
* Nur Bots am Steuer (`nur_bot`): `_freier_buggy` schliesst Menschen aus, ein
  Abwurf setzt mit `SchlachtTeil.bot_ans_steuer` einen Bot der Seite hinein.
* Bot-KI: `bots.BotHirn._flak_feuern` - naechstes Luftziel der Gegner, Zeiger
  auf dessen Bild, `LuftTeil._vorhalten` rechnet den Vorhalt.
* Wer im Flakwagen sitzt, rastet auch auf `nur_flak`-Ziele ein (Abwuerfe,
  Fallschirmjaeger) - die Regel aus 0.34.113 ist damit komplett.

## Was 0.34.115 gebaut hat

* `Gefecht.funk_stoerer(punkt, team, ebene)`: alle gegnerischen Funkwagen auf
  STOEREN, die diesen Punkt erfassen (Gastgeber und Gast); `funk_gestoert_bei`
  fragt nur noch, ob die Liste leer ist.
* `Minikarte`: im Stoerkreis `_rauschen` statt aller Punkte, dazu `_pings` -
  je erfassendem Funkwagen einer. Werte `K.MINIKARTE["gestoert"]`.
* Truppfunk: `bot_goap._funken_tun` bricht im Stoerkreis ab (Pause), und
  `trupp.funk_senden` laesst gestoerte Anfuehrer nichts hoeren.
* Funkwagen-Zusatzwert im Netz: `[Betriebsart, Basis-Team]`.

## Was 0.34.117 bis 0.34.120 gebaut haben (Wuensche nach den Videos)

* **0.34.117** Abwurf: Wanne und Aufbau als ein Bild gedreht
  (`SchlachtTeil._fracht_ganz`); Jagdpanzer ohne sichtbaren Fahrer (Luke
  immer zu); Trosswagen 20 % groesser; Basis: zwei Trosswagen und ein
  Flakwagen mit Bot, der im Konvoi faehrt (`bots._konvoi_fahren`,
  `K.FLAK["konvoi_*"]`).
* **0.34.118** Flak: `Flakgranate` (Zeitzuender, Wolke), gut 2 Schuss/s;
  Abwuerfe am Schirm: Kisten und Fallschirmjaeger platzen mit eigener
  Animation, Fahrzeuge verlieren den Schirm (`Abwurf.gerissen`) und kommen mit
  4 % Leben an.
* **0.34.119** Tragschrauber: ein Schatten aus der Silhouette (samt Rotor);
  Bomben als eigene Bilder, senkrecht, eine auf einmal.
* **0.34.120** Funkwagen und Werfer: Auf- und Abbau mit Animation
  (`Aufbauwagen.fortschritt`); neues 3D-Raketengestell (`art_werfer.py`,
  `luft._werfer_gestelle_zeichnen`), das sich zum Zeiger dreht, Raketen
  nacheinander aus den Rohren, Rohre laden einzeln nach, Rueckstrahl; der
  Werfer geht mit der groessten Explosion hoch (`Welt._werfer_explosion`),
  Fahrer und alle im Umkreis sterben, kein Wrack, nur Einzelteile.
* **0.34.124** Nacharbeit (Uebergabe in `docs/UEBERGABE.md`): Effektsystem
  `effekte.py`, 3D-Zeichner `drei_d.py`; Schrottbombe (`art_bombe.py`); das
  Werfer-Gestell als echtes 3D-Modell aus Schrottrohren, das die Rohre nach
  der Zielentfernung hebt, Raketen als 3D-Modell im Bogen; Flak mit
  Leuchtspur; der Funkwagen-Mast als 3D-Modell (`art_funkmast.py`,
  `luft._funkmasten_zeichnen`): liegt eingepackt auf dem Dach, richtet sich
  auf, faehrt aus, Kopf klappt auf, Seile laufen aus, der Kopf dreht sich
  (`Funkwagen.kopf`, `K.FUNKWAGEN["kopf_dreh"]`).
* **Trosswagen, was es gibt und was nicht:** das Aufnehmen von Medkit und
  Munition hat eine Einblendung ("[E] NACHSCHUB (n)", wer hinten steht); ein
  **Anhaengen** von Fahrzeugen gibt es nicht - Fahrzeuge werden nur in der
  Zone hinter dem Wagen repariert.

