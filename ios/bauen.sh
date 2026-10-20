#!/usr/bin/env bash
# ============================================================
#  DUSTFRONT fuer iPhone und iPad bauen - auf einem Mac.
#
#  Braucht: macOS, Xcode (aus dem App Store, einmal geoeffnet),
#  Python 3 und Internet (beim ersten Mal ~200 MB Vorlage).
#
#  Aufruf aus dem Spielordner:
#      ios/bauen.sh                       # Bundle-ID bleibt die Vorgabe
#      BUNDLE_ID=de.deinname.dustfront ios/bauen.sh
#
#  Danach oeffnet sich Xcode mit dem Projekt. Dort einmal das eigene
#  Team waehlen (Signing & Capabilities), das iPhone anstecken und auf
#  Run druecken. Schritt fuer Schritt: ios/LIESMICH.md.
#
#  Erneut aufrufen, wenn sich das Spiel geaendert hat: die Vorlage wird
#  nicht neu geladen, nur der Spielcode in der App ersetzt. Team und
#  Einstellungen in Xcode bleiben dabei stehen.
# ============================================================
set -euo pipefail

cd "$(dirname "$0")/.."
SPIEL="$(pwd)"
BAU="$SPIEL/ios/build"
STUFE="$BAU/DUSTFRONT"             # was in die App kommt
# Die Fassung, fuer die pygame-ios eine fertige Vorlage hat (2.5.5, 2.5.6).
PYGAME_CE="${PYGAME_CE:-2.5.6}"
BUNDLE_ID="${BUNDLE_ID:-}"

abbrechen() {
    echo
    echo "  $1"
    echo
    exit 1
}

[ "$(uname)" = "Darwin" ] || abbrechen "Das geht nur auf einem Mac (Xcode)."
command -v xcodebuild >/dev/null 2>&1 \
    || abbrechen "Xcode fehlt. Aus dem App Store laden und einmal oeffnen."
PY=""
for kandidat in python3.13 python3; do
    if command -v "$kandidat" >/dev/null 2>&1; then
        PY="$kandidat"
        break
    fi
done
[ -n "$PY" ] || abbrechen "Python 3 fehlt. Von python.org holen."

# pygame-ios in eine eigene Umgebung, nicht ins System-Python. Auch
# Homebrew-Python laesst das zu (dort waere pip global gesperrt).
if [ ! -x "$BAU/venv/bin/pygame_ios" ]; then
    echo "  pygame-ios wird eingerichtet (einmalig) ..."
    mkdir -p "$BAU"
    "$PY" -m venv "$BAU/venv"
    "$BAU/venv/bin/pip" install --quiet --upgrade pip
    "$BAU/venv/bin/pip" install --quiet pygame-ios
fi

# Was in die App kommt. Nicht der ganze Ordner: pygame-ios kopiert alles,
# was es bekommt, und .git, Pruefungen und die cloudflared-Archive fuer
# Windows und macOS (60 MB) haben auf dem iPhone nichts verloren.
echo "  Spielcode wird zusammengestellt ..."
mkdir -p "$STUFE"
find "$STUFE" -mindepth 1 -maxdepth 1 ! -name pygame-ios-template -exec rm -rf {} +
rsync -a --exclude "__pycache__" --exclude "*.pyc" \
    dustfront assets karten wesen "$STUFE/"
cp rustfront_menu.py rustfront_splash.py splash_engine.py "$STUFE/"
cp ios/start.py "$STUFE/start.py"

echo "  Xcode-Projekt wird gebaut (pygame-ce $PYGAME_CE) ..."
( cd "$STUFE" && "$BAU/venv/bin/pygame_ios" . start.py "$PYGAME_CE" )

VORLAGE="$STUFE/pygame-ios-template"
[ -d "$VORLAGE" ] || abbrechen "pygame-ios hat kein Projekt angelegt (siehe oben)."

# ---- Info.plist: Querformat, Vollbild, Name, Netz ----------------------
PB=/usr/libexec/PlistBuddy
setzen() {          # setzen DATEI SCHLUESSEL TYP WERT
    # Der Wert in Anfuehrungszeichen: sonst endet ein Satz am ersten Leerzeichen.
    "$PB" -c "Set :$2 \"$4\"" "$1" 2>/dev/null || "$PB" -c "Add :$2 $3 \"$4\"" "$1"
}
liste_setzen() {    # liste_setzen DATEI SCHLUESSEL WERT...
    local datei="$1" schluessel="$2"
    shift 2
    "$PB" -c "Delete :$schluessel" "$datei" 2>/dev/null || true
    "$PB" -c "Add :$schluessel array" "$datei"
    local i=0
    for wert in "$@"; do
        "$PB" -c "Add :$schluessel:$i string $wert" "$datei"
        i=$((i + 1))
    done
}
gefunden=0
while IFS= read -r plist; do
    # Nur die der App selbst, nicht die der eingebetteten Bibliotheken.
    "$PB" -c "Print :CFBundleExecutable" "$plist" >/dev/null 2>&1 || continue
    case "$plist" in *.framework/*|*.xcframework/*) continue ;; esac
    echo "  Info.plist: $plist"
    setzen "$plist" CFBundleDisplayName string DUSTFRONT
    setzen "$plist" UIRequiresFullScreen bool true
    setzen "$plist" UIStatusBarHidden bool true
    setzen "$plist" UIViewControllerBasedStatusBarAppearance bool false
    # GRUND: Ohne diesen Satz verweigert iOS jede Verbindung ins eigene
    # WLAN, und eine LAN-Lobby ist nicht zu erreichen. Der Text erscheint
    # in der Abfrage beim ersten Mal.
    setzen "$plist" NSLocalNetworkUsageDescription string \
        "DUSTFRONT verbindet sich mit Lobbys im eigenen WLAN."
    liste_setzen "$plist" UISupportedInterfaceOrientations \
        UIInterfaceOrientationLandscapeLeft UIInterfaceOrientationLandscapeRight
    liste_setzen "$plist" "UISupportedInterfaceOrientations~ipad" \
        UIInterfaceOrientationLandscapeLeft UIInterfaceOrientationLandscapeRight
    gefunden=1
done < <(find "$VORLAGE" -name "*Info.plist" -not -path "*/Support/*")
[ "$gefunden" = 1 ] || echo "  WARNUNG: keine Info.plist gefunden - Querformat in Xcode setzen."

# ---- Bundle-ID ---------------------------------------------------------
if [ -n "$BUNDLE_ID" ]; then
    while IFS= read -r pbx; do
        sed -i '' -E "s/PRODUCT_BUNDLE_IDENTIFIER = [^;]+;/PRODUCT_BUNDLE_IDENTIFIER = $BUNDLE_ID;/" "$pbx"
        echo "  Bundle-ID: $BUNDLE_ID"
    done < <(find "$VORLAGE" -name project.pbxproj)
fi

# ---- App-Symbol und Startbildschirm ------------------------------------
# Statt des Logos von pygame-ce das Zeichen von DUSTFRONT (ios/bilder,
# erzeugt mit ios/logo_bauen.py). Der Startbildschirm kommt nicht mehr aus
# der Storyboard-Datei der Vorlage, sondern aus der Info.plist
# (UILaunchScreen, ab iOS 14): Bild und Hintergrundfarbe aus dem
# Asset-Katalog. GRUND: Wie die Vorlage ihren Startbildschirm baut, kann
# sich mit jeder Fassung aendern - dieser Weg haengt nicht davon ab.
BILDER="$SPIEL/ios/bilder"
KATALOG="$(find "$VORLAGE" -name "*.xcassets" -type d -not -path "*/Support/*" | head -n 1)"
if [ -n "$KATALOG" ]; then
    SYMBOL="$KATALOG/AppIcon.appiconset"
    rm -rf "$SYMBOL"
    mkdir -p "$SYMBOL"
    cp "$BILDER/AppIcon.png" "$SYMBOL/AppIcon.png"
    cat > "$SYMBOL/Contents.json" <<'JSON'
{
  "images" : [
    { "filename" : "AppIcon.png", "idiom" : "universal", "platform" : "ios", "size" : "1024x1024" }
  ],
  "info" : { "author" : "xcode", "version" : 1 }
}
JSON
    START="$KATALOG/Startbild.imageset"
    mkdir -p "$START"
    cp "$BILDER/Startbild.png" "$START/Startbild.png"
    # Als @3x: 960 Pixel breit sind dann 320 Punkte, auf jedem iPhone und
    # iPad gut mittig und nicht randvoll.
    cat > "$START/Contents.json" <<'JSON'
{
  "images" : [
    { "filename" : "Startbild.png", "idiom" : "universal", "scale" : "3x" }
  ],
  "info" : { "author" : "xcode", "version" : 1 }
}
JSON
    mkdir -p "$KATALOG/Starthimmel.colorset"
    # Derselbe Nachthimmel wie hinter dem Zeichen (8, 13, 21).
    cat > "$KATALOG/Starthimmel.colorset/Contents.json" <<'JSON'
{
  "colors" : [
    { "color" : { "color-space" : "srgb", "components" : {
        "alpha" : "1.000", "red" : "0.031", "green" : "0.051", "blue" : "0.082" } },
      "idiom" : "universal" }
  ],
  "info" : { "author" : "xcode", "version" : 1 }
}
JSON
    while IFS= read -r plist; do
        "$PB" -c "Print :CFBundleExecutable" "$plist" >/dev/null 2>&1 || continue
        case "$plist" in *.framework/*|*.xcframework/*) continue ;; esac
        "$PB" -c "Delete :UILaunchStoryboardName" "$plist" 2>/dev/null || true
        "$PB" -c "Delete :UILaunchScreen" "$plist" 2>/dev/null || true
        "$PB" -c "Add :UILaunchScreen dict" "$plist"
        "$PB" -c "Add :UILaunchScreen:UIImageName string Startbild" "$plist"
        "$PB" -c "Add :UILaunchScreen:UIColorName string Starthimmel" "$plist"
    done < <(find "$VORLAGE" -name "*Info.plist" -not -path "*/Support/*")
    # Ohne das nimmt Xcode die Storyboard-Datei aus den Build-Einstellungen
    # und ueberschreibt den Eintrag oben wieder.
    while IFS= read -r pbx; do
        sed -i '' -E "/INFOPLIST_KEY_UILaunchStoryboardName = [^;]*;/d" "$pbx"
        sed -i '' -E "s/ASSETCATALOG_COMPILER_APPICON_NAME = [^;]+;/ASSETCATALOG_COMPILER_APPICON_NAME = AppIcon;/" "$pbx"
    done < <(find "$VORLAGE" -name project.pbxproj)
    echo "  App-Symbol und Startbild: DUSTFRONT"
else
    echo "  WARNUNG: kein Asset-Katalog gefunden - App-Symbol bleibt das der Vorlage."
fi

# ---- Mindestens iOS 15 -------------------------------------------------
# Die Vorlage verlangt iOS 13. Aktuelle Xcode-Fassungen bauen nur noch ab
# iOS 15 und brechen sonst mit "IPHONEOS_DEPLOYMENT_TARGET is set to 13.0"
# ab (gemeldet). Jedes iPhone ab dem XS kann iOS 15 und mehr.
while IFS= read -r pbx; do
    sed -i '' -E "s/IPHONEOS_DEPLOYMENT_TARGET = 1[0-4](\.[0-9]+)?;/IPHONEOS_DEPLOYMENT_TARGET = 15.0;/" "$pbx"
done < <(find "$VORLAGE" -name project.pbxproj)

PROJEKT="$(find "$VORLAGE" -maxdepth 3 -name "*.xcodeproj" | head -n 1)"
[ -n "$PROJEKT" ] || abbrechen "Kein .xcodeproj gefunden in $VORLAGE."
echo
echo "  Fertig: $PROJEKT"
echo "  In Xcode: Team waehlen (Signing & Capabilities), iPhone waehlen, Run."
echo
open "$PROJEKT" || true
