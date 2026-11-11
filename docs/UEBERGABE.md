# Uebergabe: Nacharbeit an den Fahrzeugen (Stand: fertig, 0.34.125)

Wunsch des Besitzers (wortgetreu zusammengefasst): die letzten Aenderungen
(0.34.117 bis 0.34.120) haben viele Designfehler. Zu tun, jeweils
**komplett neu, ohne Bezug auf das Bisherige**, so wie urspruenglich gewuenscht:

1. Bomben am Hubschrauber (Tragschrauber) komplett neu machen und designen. - **erledigt**: zweiter Anlauf nach Einwand des Besitzers (keine moderne Fliegerbombe, nichts am Heli sichtbar, klein, Schrott): kleine rostige Blechdose mit Draht, Naegeln, Klebeband und Lunte; der Fahrer laesst sie neben der Kanzel fallen (`bombe.abwurf` in config), sie ueberschlaegt sich, Lunte glimmt, Funken, Rauchfaden. Klaenge `bombe_ab` (Zuenden) und `bombe_fall` (Zischen) neu.
2. Alle Explosionen, Rauch, sonstige Effekte und Animationen neu. - **erledigt**: Effektsystem; Auf-/Abbau: der Werfer hebt sein 3D-Gestell mit dem Aufbau (Stuetzen wie in 0.34.120), der Funkwagen-Mast ist ein 3D-Modell (`art_funkmast.py`, `luft._funkmasten_zeichnen`): liegt eingepackt auf dem Dach, richtet sich auf, faehrt aus, Kopf klappt auf, Seile laufen aus, Kopf dreht sich (`Funkwagen.kopf`, `K.FUNKWAGEN["kopf_dreh"]`). Die flachen Bilder `funkwagen_aufbau_N`/`funkwagen_aktiv_N` und `peilrahmen_zeichnen` sind weg.
3. Raketen und 3D-Teil beim Werfer komplett neu. - **erledigt**: `art_werfer.py` neu (3D-Gestell aus sechs ungleichen Schrottrohren auf alter Felge, dreht und hebt sich, `gestell(gieren, erhebung, maske)`; Raketen `rakete(gieren, kippen)`), Steilheit nach Zielentfernung (`WERFER.hub`, `hub_dreh`, Netzfeld 6 der Werfer-Meldung), Flugbahn als Bezierkurve aus dem Rohr (`Gefecht._raketen_bahn`), Rauchspur, Rueckstrahl am hinteren Rohrende (`werfer_start`-Radius = Steilheit*1000 + Richtung). Die alten Dekale `werfer_teil_N` und `werfer_rohre_*` sind weg (Tests anpassen!).
4. Flak-Schuesse komplett neu. - **erledigt**: Granate unsichtbar (`flak_leer`), sichtbar ist die Leuchtspur aus dem Effektsystem (`effekte.flak_schuss`, Fx-Art `leuchtspur`), die zur Hoehe des Luftziels steigt; eigenes Muendungsfeuer (Feuerstern, Pulverrauch), das allgemeine Muendungsfeuer entfaellt fuer Flak (`Welt.schussknall`). Netz: neue Explosionsart `flak_schuss`, Radius = Richtung + 360*(Strecke + 2048*Hoehe).
5. Luke auf dem Jagdpanzer entfernen, stilgerechte Luke fest in den Wannen-Sprite. - **erledigt**
6. Krad: Beifahrer mit Waffe und Ausrichtung zeigen, nur begrenzt drehbar. - **erledigt**
7. Hubschrauber ganz oben darf keine Bodenwesen schieben. - **erledigt** (Ursache: der Pilot als Figur am Boden; `Welt.auseinander` ignoriert jetzt Insassen)
8. Am Ende alles praesentieren: Videos und Bilder. - **erledigt** (0.34.125): `python werkzeug_aufnahme.py funkwagen werfer werfer_explosion schrottbombe flak krad` schreibt sechs Videos nach `aufnahmen/` (23 bis 28). Beim Ansehen fielen zwei Fehler auf und sind behoben: schwarze Quadrate bei jedem Einschlag (`effekte._zeichne`, Brocken) und ungleich dicke Seile am Funkmast.

Erledigt in 0.34.124: Tests in `tests/test_spiel.py` angepasst und ergaenzt,
Version erhoeht (README, `rustfront_menu.py`), docs/MEHRSPIELER.md (Netz
geaendert), docs/FAHRZEUGE.md, docs/TESTMODUS.md. Die Versionen 0.34.121 bis
0.34.123 in Kommentaren waren Zwischenstaende, veroeffentlicht ist 0.34.124.

## Rueckmeldung zu 0.34.125 (umgesetzt in 0.34.126)

* Drift-Ton `buggy_rutschen` ganz entfernt ("nie wieder hoeren") - nicht ersetzen.
* Explosionen: keine gemalten Wolkenballen mehr, sondern eine grosse Wolke aus
  Pixel-Teilchen wie bei den alten Explosionen (`effekte.Teilchen`; `rauch()` und
  `feuer()` erzeugen sie). Besonders der Rueckstrahl des Werfers.
* Funkmast: ohne schwarzen Umriss, feste Farben beim Aufrichten (`drei_d.ton_fest`),
  liegend im Lack des Dachs (`art_funkmast.TARNUNG`).
* Werfer-Gestell und Raketen: nicht 3D, sondern klassisch gemalt (`art_werfer.py`),
  je Drehung und Aufrichtung ein eigenes Bild.

## Was neu gebaut ist (Dateien)

* `dustfront/effekte.py` - neues Effektsystem: Teilchen mit Hoehe,
  Schwerkraft, Abprall, Schatten; gemalte Rauch-/Feuer-Sprites (vier
  Lichtstufen), Funkenstreifen, flatternde Stofffetzen, Druckringe, Blitz;
  Dekale `fx_brand_N`, `fx_teil_N`. Rezepte: flak, kiste_platzt,
  mensch_luft, schirm_reisst, absturz, raketenstart, einschlag,
  werfer_explosion, bombe, bombe_los. Angebunden ueber `Welt.explosion`
  (Tabelle `ARTEN`), gezeichnet in `Renderer.effekte_zeichnen`.
* `dustfront/drei_d.py` - kleiner 3D-Zeichner (Kegelstumpf, Platte, Quader,
  drehen/kippen/rollen, Projektion Bild-y = y - z, Licht in Stufen). Gedacht
  auch fuer das neue Werfer-Gestell und die Raketen.
* `dustfront/art_bombe.py` - Schrottbombe `schrottbombe(winkel)` (12 Stufen),
  `lunte_spitze(winkel)`; gezeichnet im Fall von `luft._bomben_fallend_zeichnen`.
  Der Tragschrauber hat wieder sein normales Bild und `tragschrauber_schatten`.
* `dustfront/art_funkmast.py` - Mast des Funkwagens als 3D-Modell
  (`funkmast(gieren, fortschritt, drehung)`, `schatten(...)`, `stellung`),
  gezeichnet in `luft._funkmasten_zeichnen`.
* Jagdpanzer: `_kommandantenluke` in `art_neue_fahrzeuge.jagdpanzer_wanne`.
* Krad: `Krad.beifahrer_sitz/beifahrer_klemmen`, `K.KRAD beifahrer_bogen`,
  Zeichnen `LuftTeil._beifahrer_zeichnen`, Klemmen in `Spieler.schritt`.

## Noch zu tun

Nichts aus diesem Auftrag. Zur Beobachtung: der Test "Panik in der Deckung"
in `tests/test_spiel.py` haengt vom Hash-Zufall von Python ab: mit
`PYTHONHASHSEED=1` gruen (alter und neuer Stand), ohne festen Wert in beiden
Laeufen von 0.34.124 rot (einmal plante der Bot vorher
`deckung_wechseln`, einmal wich er einer Granate aus). Ob der alte Stand
bei anderen Werten auch rot wird, ist nicht geprueft. Die Lobby-Tests mit
echten Sockets scheitern gelegentlich, wenn der Rechner nebenher ausgelastet ist.
