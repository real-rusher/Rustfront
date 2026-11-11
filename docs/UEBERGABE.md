# Uebergabe: Nacharbeit an den Fahrzeugen (Stand: in Arbeit)

Wunsch des Besitzers (wortgetreu zusammengefasst): die letzten Aenderungen
(0.34.117 bis 0.34.120) haben viele Designfehler. Zu tun, jeweils
**komplett neu, ohne Bezug auf das Bisherige**, so wie urspruenglich gewuenscht:

1. Bomben am Hubschrauber (Tragschrauber) komplett neu machen und designen. - **erledigt (ungeprueft im Bild)**
2. Alle Explosionen, Rauch, sonstige Effekte und Animationen neu. - **Effektsystem erledigt**, Auf-/Abbau-Animationen von Funkwagen/Werfer noch offen
3. Raketen und 3D-Teil beim Werfer komplett neu. - **offen**
4. Flak-Schuesse komplett neu. - **offen** (Wolke schon neu, Geschoss/Leuchtspur/Muendungsfeuer nicht)
5. Luke auf dem Jagdpanzer entfernen, stilgerechte Luke fest in den Wannen-Sprite. - **erledigt**
6. Krad: Beifahrer mit Waffe und Ausrichtung zeigen, nur begrenzt drehbar. - **erledigt**
7. Hubschrauber ganz oben darf keine Bodenwesen schieben. - **erledigt** (Ursache: der Pilot als Figur am Boden; `Welt.auseinander` ignoriert jetzt Insassen)
8. Am Ende alles praesentieren: Videos und Bilder. - **offen**

Danach: Tests in `tests/test_spiel.py` ergaenzen (alte Pruefungen zu Krad-Skin
`krad_beiwagen_*`, Tragschrauber-Schatten `tragschrauber_schatten`, Bomben
`bombe_rahmen`/`bombe_fall`, Flak-Wolkenart, Werfer-Explosion muessen an das
neue Verhalten angepasst werden), alle fuenf Suiten gruen, Version erhoehen
(README-Zeilen, docs/MEHRSPIELER.md: Netz geaendert - neue Explosionsarten
`einschlag`, `bombe`, `bombe_los`; Radius traegt bei Luftarten die Hoehe;
Tragschrauber Feld 20 Bombe mit Richtung).

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
* `dustfront/art_bombe.py` - Bombenmodell (3D); Tragschrauber-Bild mit Bomben
  `tsb<N>_<Bild>`, Schatten `tss<N>`, fallende Bombe `bombe_fallend`.
* Jagdpanzer: `_kommandantenluke` in `art_neue_fahrzeuge.jagdpanzer_wanne`.
* Krad: `Krad.beifahrer_sitz/beifahrer_klemmen`, `K.KRAD beifahrer_bogen`,
  Zeichnen `LuftTeil._beifahrer_zeichnen`, Klemmen in `Spieler.schritt`.

## Noch zu tun (Reihenfolge)

1. Werfer: `art_werfer.py` ersetzen durch 3D-Gestell aus `drei_d.py`
   (Rohre als Zylinder, Wiege, Hub), Raketen als 3D-Modell im Flug
   (`mehrspieler._raketen_zeichnen`, mit `effekte.rauchspur`).
2. Flak: neues Geschoss-Bild (Leuchtspur steigt zur Zielhoehe), Muendungsfeuer.
3. Funkwagen/Werfer Auf-/Abbau-Animationen neu.
4. Tests, Doku, Version, Videos und Bilder (Skripte im Scratchpad gingen
   verloren - neu schreiben: Testmodus, `tm.zeichnen`, ffmpeg).
