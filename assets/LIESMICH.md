# assets — Texturen

Hier liegen die Bilder. Der Ordner ist absichtlich fast leer: das Spiel
zeichnet sich jedes Bild selbst, solange keine Datei da ist.

## Die Regel

Eine Datei `assets/<name>.png` ersetzt das im Code gezeichnete Bild. **Es
ist keine Zeile Code zu aendern**, kein Eintrag irgendwo nachzutragen, kein
Neustart-Trick noetig. Datei hinlegen, Spiel starten, fertig.

Statt `.png` gehen auch `.webp` und `.bmp`. Gesucht wird in dieser
Reihenfolge, die erste gefundene gewinnt.

## Welche Namen es gibt

    python -m dustfront --vorlagen

schreibt jedes Bild, das das Spiel kennt, nach `assets_vorlage/` — in der
richtigen Groesse, mit dem richtigen Dateinamen, dazu eine Uebersichtstafel
`_uebersicht.png` mit allen Bildern nebeneinander. Man malt ueber eine
Vorlage, kopiert sie hierher und ist fertig. Umbenennen entfaellt, der Name
stimmt schon.

    python -m dustfront --assets

sagt umgekehrt, welcher Name gerade aus einer Datei kommt und welcher noch
aus dem Code. Damit prueft man, ob eine neue Datei wirklich angenommen wurde.

Die vollstaendige Tabelle steht ausserdem im README unter "Texturen und
Klaenge ersetzen" und als `BILD_MASS` in `dustfront/config.py`.

## Groesse

Jedes Bild hat ein Sollmass, das in `BILD_MASS` steht. Wer genau in diesem
Mass malt, bekommt die Datei Pixel fuer Pixel so ins Spiel, wie sie ist.

Wer groesser malt, darf das: die Datei wird beim Laden hart auf das Sollmass
gerechnet, ohne Weichzeichnen. Ein sauberes Vielfaches — doppelt, dreifach,
vierfach — rechnet dabei exakt herunter und sieht am besten aus. Krumme
Masse funktionieren auch, verlieren aber Pixel.

Wer dauerhaft ein anderes Mass will, aendert die Zahl in `BILD_MASS`. Das
ist die eine Stelle dafuer.

## Worauf beim Malen zu achten ist

* **Kacheln** sind 32x32 und muessen randlos aneinanderpassen.
* **Figuren** sitzen mittig auf einer quadratischen Flaeche und schauen nach
  rechts, also auf 0 Grad. Das Spiel dreht sie von dort aus. Wer nach oben
  malt, dessen Figur laeuft seitwaerts.
* **Durchsichtigkeit** benutzen, wo nichts ist. Die Vorlagentafel legt
  Durchsichtiges auf ein Schachbrett, damit man den Rand sieht.
* **Waffensymbole** sind winzig (26x11). Dort zaehlt nur die Silhouette:
  Laenge des Laufs, Dicke des Gehaeuses, was oben und unten heraussteht.
* **Schatten, Blut, Brandfleck, Wandschatten und Vignette** haben kein
  festes Mass im Spiel. Sie richten sich nach dem, was sie wirft, und ihr
  Mass in der Tabelle ist nur das Basismass, von dem aus gerechnet wird.
  Hier malt man eine Form, keine feste Groesse - und am besten in
  Graustufen mit Alpha, damit sie sich unter alles legen kann.

## Wenn etwas schiefgeht

Eine Datei, die sich nicht lesen laesst, kostet nichts: das Spiel nimmt den
Platzhalter und laeuft weiter. Den Grund zeigt `python -m dustfront
--assets`.

Ein grelles Pink im Spiel heisst: diesen Namen kennt weder eine Datei noch
der Code. Dann stimmt der Name nicht.
