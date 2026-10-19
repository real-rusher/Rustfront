# DUSTFRONT auf iPhone und iPad

Seit 0.34.20, Branch `ios-port`. Ein echter Port: auf dem iPhone läuft
derselbe Python-Code wie am Rechner, mit pygame-ce. Nichts wird
nachgebaut oder gestreamt. Was sich unterscheidet, steht in
`dustfront/plattform.py` an einer Stelle.

Grundlage ist [pygame-ios](https://github.com/seekerluke/pygame-ios)
(MIT-Lizenz). Es bringt ein Xcode-Projekt mit Python 3.13, pygame-ce 2.5.6
und SDL2 als fertige Bibliotheken mit und legt den Spielcode hinein.

## Bauen (auf dem Mac)

Einmal vorbereiten:

1. **Xcode** aus dem App Store laden und einmal öffnen (Lizenz bestätigen,
   Zusatzkomponenten installieren lassen).
2. In Xcode unter *Settings → Accounts* mit der eigenen Apple-ID
   anmelden. Ein kostenloser Account reicht, um auf dem eigenen iPhone zu
   spielen; die App läuft dann 7 Tage und muss danach neu aufgespielt
   werden. Mit dem bezahlten Entwicklerprogramm (99 € im Jahr) läuft sie
   ein Jahr und kann über TestFlight an Freunde gehen.
3. **Python 3** von python.org, falls noch keines da ist (3.13 passt am
   besten zur Vorlage, jedes Python 3 geht).
4. Auf dem iPhone *Einstellungen → Datenschutz & Sicherheit →
   Entwicklermodus* einschalten (erscheint erst, nachdem das iPhone einmal
   per Kabel mit Xcode verbunden war).

Dann im Spielordner im Terminal:

```
git checkout ios-port
BUNDLE_ID=de.deinname.dustfront ios/bauen.sh
```

Die Bundle-ID muss weltweit eindeutig sein. Der eigene Name darin reicht
dafür. Das Skript:

* richtet pygame-ios in `ios/build/venv` ein (nicht im System-Python),
* stellt den Spielcode in `ios/build/DUSTFRONT` zusammen (ohne `.git`,
  Prüfungen und die cloudflared-Archive),
* lädt beim ersten Mal die Vorlage (gut 200 MB) und baut das Xcode-Projekt,
* stellt in der `Info.plist` Querformat, Vollbild, den Namen DUSTFRONT
  und die Begründung für das lokale Netz ein,
* setzt das App-Symbol und den Startbildschirm von DUSTFRONT ein (Bilder in `ios/bilder`, neu zu erzeugen mit
  `python ios/logo_bauen.py`),
* öffnet Xcode.

In Xcode:

1. Links das Projekt anklicken, unter *Signing & Capabilities* das eigene
   **Team** wählen.
2. Oben das angesteckte **iPhone** als Ziel wählen.
3. **Run** (▶). Beim ersten Mal auf dem iPhone unter *Einstellungen →
   Allgemein → VPN und Geräteverwaltung* dem eigenen Entwicklerzertifikat
   vertrauen.

Hat sich das Spiel geändert (neuer Stand des Branches), einfach
`ios/bauen.sh` noch einmal laufen lassen und in Xcode wieder auf Run.
Die Vorlage wird nicht neu geladen, Team und Einstellungen bleiben.

Ohne iPhone geht es auch im Simulator: als Ziel ein iPhone-Simulator
wählen. Die Finger sind dort die Maus. Mehrere Finger gleichzeitig gehen
im Simulator nur eingeschränkt (Wahltaste gedrückt halten).

## Steuerung

Im Spiel gehören die Finger der Steuerung (`dustfront/touch.py`):

| Was | Wie |
| --- | --- |
| Laufen | linke Hälfte: Daumen aufsetzen und ziehen, der Stick entsteht dort, wo der Daumen landet. Halb gezogen heißt langsamer gehen |
| Zielen und schießen | rechte Hälfte genauso. Leicht gezogen zielt, weiter gezogen schießt. Wie weit, sagt auch, wie weit eine Granate fliegt |
| DASH | gehalten; im Buggy die Handbremse |
| E | Treppe, Aufzug, einsteigen; gehalten: aufhelfen |
| R / F / + | nachladen / Nahkampf / Medkit |
| WFF | nächste Waffe der Hotbar |
| ZIEL | zielen mit dem Scharfschützengewehr, an und aus |
| II / EBN / INV | Pause / obere Ebenen ein und aus / Inventar (nur allein) |

In Menüs bleibt alles, wie es ist: ein Finger ist die Maus, zwei Finger
blättern. Oben rechts liegt ein kleiner **ESC**-Knopf für die Schirme, die
man sonst nur mit der Escape-Taste verlässt. In Textfelder tippen öffnet
die Bildschirmtastatur. Eine Tastatur am iPad geht ebenfalls, mit der
gewohnten Belegung.

Größen und Lagen der Knöpfe stehen in `dustfront/config.py` unter `TOUCH`.

## Crossplay

iPhone und Rechner spielen zusammen. Beide brauchen **dieselbe Version**
(sie steht unten im Hauptmenü). Der Rechner nimmt dafür denselben Stand
wie das iPhone, also diesen Branch, bis er in `multiplayer-test`
übernommen ist.

| | iPhone als Gast | iPhone als Gastgeber |
| --- | --- | --- |
| **Online-Code** | geht | geht nicht |
| **LAN (Adresse eintippen)** | geht | geht |
| **LAN-Lobbysuche** | geht vermutlich nicht | geht vermutlich nicht |

* **Online-Code als Gast.** Am Rechner baut cloudflared den Weg. Auf dem
  iPhone darf eine App kein zweites Programm starten. Deshalb macht dort
  `dustfront/wszugang.py` dasselbe in Python: ein WebSocket zu
  `CODE.trycloudflare.com`, darin die rohen Bytes des Spiels, Kopfzeile für
  Kopfzeile wie cloudflared. Der Gastgeber merkt keinen Unterschied.
* **Online-Code als Gastgeber** geht nicht. Den Tunnel selbst baut nur
  cloudflared (eine eigene Anmeldung bei Cloudflare), und das läuft auf
  iOS nicht. In der Lobby steht dann AUF IOS NUR BEITRETEN - LAN GEHT.
  Im eigenen WLAN aufmachen geht: Einstellungen, NETZ, IM LAN SICHTBAR.
  Die Adresse steht oben links in der Lobby.
* **Lobbysuche im LAN.** Sie ruft per UDP-Rundruf ins Netz, und das
  erlaubt iOS nur Apps mit einer Sonderberechtigung von Apple
  (Multicast-Entitlement). Ohne sie bleibt die Liste leer. Die Adresse von
  Hand geht immer. Beim ersten Mal fragt iOS, ob DUSTFRONT ins lokale Netz
  darf: **Erlauben**, sonst geht auch das nicht.

## Was noch nicht getestet ist

Gebaut und geprüft wurde alles auf Linux. Dort laufen die Touch-Steuerung
mit nachgestellten Fingern und der WebSocket-Weg gegen einen nachgestellten
Cloudflare-Server (`tests/test_spiel.py`, Abschnitt iOS). Die Prüfungen
laufen auch unter Python 3.13 mit pygame-ce 2.5.6, also mit genau den
Fassungen der Vorlage. Auf einem echten iPhone lief es noch nicht. Was
dort zuerst anzusehen ist:

* ob pygame-ios die Bildschirmtastatur so öffnet, wie SDL es verspricht,
  und ob ein Wort aus der Zwischenablage ankommt,
* ob Cloudflare den WebSocket ohne cloudflared genauso annimmt (der
  Handschlag ist derselbe, gemessen mit einem Prüfserver),
* wie flüssig es auf älteren iPhones läuft (Bildrate in den Einstellungen),
* ob die Knöpfe gut unter den Daumen liegen.

Fehler erscheinen in Xcode unten in der Konsole, wenn die App per Kabel
läuft.
