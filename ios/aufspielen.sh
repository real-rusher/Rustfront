#!/usr/bin/env bash
# ============================================================
#  DUSTFRONT auf ein angestecktes iPhone oder iPad bringen -
#  bauen, signieren, aufspielen, starten. Ohne in Xcode zu
#  klicken (seit 0.34.63). Nur auf einem Mac.
#
#  Aufruf aus dem Spielordner:
#      ios/aufspielen.sh                  bauen, aufspielen, starten
#      ios/aufspielen.sh --testmodus      ... und gleich im Testmodus
#      ios/aufspielen.sh --nur-aufspielen nicht neu bauen, nur aufspielen
#      ios/aufspielen.sh --liste          welche Geraete angesteckt sind
#      ios/aufspielen.sh --xcode          wie bisher: bauen, Xcode oeffnen
#      ios/aufspielen.sh --hilfe
#
#  Einstellbar (alle werden in ios/build gemerkt, beim naechsten Mal
#  braucht es sie nicht mehr):
#      BUNDLE_ID=de.deinname.dustfront    die Kennung der App
#      TEAM_ID=ABCDE12345                 das Entwicklerteam
#      GERAET="iPad von Anna"             Name oder UDID, wenn mehrere dran sind
#      KARTE=wueste                       Karte fuer --testmodus
#
#  Einmal vorher noetig (siehe ios/LIESMICH.md):
#    * Xcode aus dem App Store, einmal geoeffnet.
#    * In Xcode unter Settings -> Accounts die eigene Apple-ID.
#    * Auf dem Geraet: einmal per Kabel mit dem Mac verbunden,
#      "Diesem Computer vertrauen", Entwicklermodus an.
#
#  Gebraucht werden die Werkzeuge, die Xcode mitbringt: xcodebuild
#  zum Bauen und Signieren, devicectl (ab Xcode 15) zum Aufspielen und
#  Starten. "open" nimmt das Skript nur mit --xcode, oder wenn das
#  Signieren nicht von allein klappt - dann oeffnet es Xcode an der
#  richtigen Stelle.
# ============================================================
set -euo pipefail

cd "$(dirname "$0")/.."
SPIEL="$(pwd)"
BAU="$SPIEL/ios/build"
ABGELEITET="$BAU/abgeleitet"       # was xcodebuild baut
PROTOKOLL="$BAU/xcodebuild.log"

TESTMODUS=0
NEU_BAUEN=1
NUR_LISTE=0
NUR_XCODE=0
for arg in "$@"; do
    case "$arg" in
        --testmodus) TESTMODUS=1 ;;
        --nur-aufspielen) NEU_BAUEN=0 ;;
        --liste) NUR_LISTE=1 ;;
        --xcode) NUR_XCODE=1 ;;
        -h|--hilfe|--help)
            sed -n '2,33p' "$0" | sed 's/^# \{0,1\}//'
            exit 0 ;;
        *)
            echo "  Unbekannt: $arg (ios/aufspielen.sh --hilfe)"
            exit 1 ;;
    esac
done

abbrechen() {
    echo
    echo "  $1"
    shift
    for zeile in "$@"; do
        echo "  $zeile"
    done
    echo
    exit 1
}

schritt() {
    echo
    echo "  == $1"
}

[ "$(uname)" = "Darwin" ] || abbrechen "Das geht nur auf einem Mac (Xcode)."
command -v xcodebuild >/dev/null 2>&1 \
    || abbrechen "Xcode fehlt. Aus dem App Store laden und einmal oeffnen."
command -v python3 >/dev/null 2>&1 \
    || abbrechen "Python 3 fehlt. Von python.org holen."

if [ "$NUR_XCODE" = 1 ]; then
    exec "$SPIEL/ios/bauen.sh"
fi

xcrun --find devicectl >/dev/null 2>&1 \
    || abbrechen "devicectl fehlt - das kommt mit Xcode 15 oder neuer." \
                 "Xcode im App Store aktualisieren, oder: ios/aufspielen.sh --xcode"

mkdir -p "$BAU"

# ---- Was gemerkt wird -------------------------------------------------
# GRUND: Bundle-ID und Team sollen nicht bei jedem Aufruf neu angegeben
# werden muessen - eine andere Bundle-ID waere fuer das iPhone eine
# andere App, mit leeren Einstellungen.
merken() {          # merken NAME WERT
    printf '%s\n' "$2" > "$BAU/$1"
}
gemerkt() {         # gemerkt NAME -> Wert oder leer
    if [ -f "$BAU/$1" ]; then
        head -n 1 "$BAU/$1"
    fi
}

BUNDLE_ID="${BUNDLE_ID:-$(gemerkt bundle_id)}"
if [ -z "$BUNDLE_ID" ]; then
    # Eine Kennung, die es weltweit nur einmal gibt: mit dem Namen des
    # Benutzers am Mac. Die Vorgabe der Vorlage gehoert meist schon einem
    # anderen Team, und dann lehnt Apple das Signieren ab.
    wer="$(id -un | tr -cd '[:alnum:]' | tr '[:upper:]' '[:lower:]')"
    BUNDLE_ID="de.dustfront.${wer:-spieler}"
fi
merken bundle_id "$BUNDLE_ID"

# ---- Geraete ----------------------------------------------------------
geraete_lesen() {
    # Eine Zeile je iPhone oder iPad: UDID, Name, Art, Verbindung,
    # Entwicklermodus. devicectl schreibt JSON; gelesen wird es mit Python,
    # weil die Felder mit jeder Xcode-Fassung etwas wandern.
    local json="$BAU/geraete.json"
    rm -f "$json"
    xcrun devicectl list devices --json-output "$json" >/dev/null 2>&1 || true
    [ -s "$json" ] || return 0
    python3 - "$json" <<'PY'
import json, sys
try:
    daten = json.load(open(sys.argv[1]))
except (OSError, ValueError):
    sys.exit(0)
for g in (daten.get("result") or {}).get("devices") or []:
    hw = g.get("hardwareProperties") or {}
    dp = g.get("deviceProperties") or {}
    cp = g.get("connectionProperties") or {}
    if hw.get("platform", "iOS") not in ("iOS", "iPadOS"):
        continue
    if hw.get("reality") == "virtual":
        continue
    udid = hw.get("udid") or g.get("identifier") or ""
    if not udid:
        continue
    weg = cp.get("transportType") or "-"
    gepaart = cp.get("pairingState", "paired") == "paired"
    da = gepaart and (weg in ("wired", "localNetwork")
                      or cp.get("tunnelState") == "connected")
    print("\t".join([udid, dp.get("name") or hw.get("marketingName") or "?",
                     hw.get("deviceType") or "?", weg if da else "nicht verbunden",
                     dp.get("developerModeStatus") or "?"]))
PY
}

schritt "Angesteckte Geraete"
GERAETE="$(geraete_lesen)"
if [ -z "$GERAETE" ]; then
    abbrechen "Kein iPhone oder iPad gefunden." \
              "Per Kabel anstecken, entsperren und 'Diesem Computer vertrauen'." \
              "Beim allerersten Mal: Xcode oeffnen (Window -> Devices and Simulators)," \
              "bis das Geraet dort erscheint."
fi
printf '%s\n' "$GERAETE" | while IFS=$'\t' read -r udid name art weg modus; do
    echo "    $name ($art)  $weg  Entwicklermodus: $modus  [$udid]"
done
if [ "$NUR_LISTE" = 1 ]; then
    exit 0
fi

GERAET="${GERAET:-}"
ZEILE=""
if [ -n "$GERAET" ]; then
    ZEILE="$(printf '%s\n' "$GERAETE" | awk -F'\t' -v g="$GERAET" '$1 == g || $2 == g {print; exit}')"
    [ -n "$ZEILE" ] || abbrechen "Kein Geraet mit Name oder UDID '$GERAET'." \
                                 "ios/aufspielen.sh --liste zeigt, welche dran sind."
else
    # Ein verbundenes, per Kabel zuerst.
    ZEILE="$(printf '%s\n' "$GERAETE" | awk -F'\t' '$4 == "wired" {print; exit}')"
    [ -n "$ZEILE" ] || ZEILE="$(printf '%s\n' "$GERAETE" | awk -F'\t' '$4 != "nicht verbunden" {print; exit}')"
    [ -n "$ZEILE" ] || abbrechen "Die Geraete sind gepaart, aber gerade nicht verbunden." \
                                 "Per Kabel anstecken und entsperren."
fi
UDID="$(printf '%s' "$ZEILE" | cut -f1)"
NAME="$(printf '%s' "$ZEILE" | cut -f2)"
MODUS="$(printf '%s' "$ZEILE" | cut -f5)"
echo "  Ziel: $NAME"
if [ "$MODUS" = "disabled" ]; then
    abbrechen "Auf '$NAME' ist der Entwicklermodus aus." \
              "Einstellungen -> Datenschutz & Sicherheit -> Entwicklermodus, einschalten," \
              "das Geraet startet neu. Danach dieses Skript noch einmal."
fi

# ---- Team -------------------------------------------------------------
team_suchen() {
    # 1. Aus dem Entwicklerzertifikat im Schluesselbund: die Team-ID steht
    #    dort als OU (Organizational Unit).
    local cn
    cn="$(security find-identity -v -p codesigning 2>/dev/null \
          | sed -nE 's/.*"(Apple Development: [^"]+)".*/\1/p' | head -n 1)"
    if [ -n "$cn" ]; then
        security find-certificate -c "$cn" -p 2>/dev/null \
            | openssl x509 -noout -subject 2>/dev/null \
            | sed -nE 's/.*OU ?= ?([A-Z0-9]{10}).*/\1/p' | head -n 1
        return 0
    fi
    # 2. Aus den Einstellungen von Xcode (Settings -> Accounts). So
    #    findet es auch ein Team, fuer das es noch kein Zertifikat gibt -
    #    das legt xcodebuild dann selbst an.
    defaults read com.apple.dt.Xcode IDEProvisioningTeams 2>/dev/null \
        | sed -nE 's/.*teamID = "?([A-Z0-9]{10})"?;.*/\1/p' | head -n 1
}
TEAM_ID="${TEAM_ID:-$(gemerkt team_id)}"
[ -n "$TEAM_ID" ] || TEAM_ID="$(team_suchen || true)"
if [ -z "$TEAM_ID" ]; then
    echo
    echo "  Kein Entwicklerteam gefunden."
    echo "  Einmal in Xcode unter Settings -> Accounts die Apple-ID hinzufuegen"
    echo "  (ein kostenloser Account reicht), dann dieses Skript noch einmal."
    echo "  Oder die Team-ID angeben: TEAM_ID=ABCDE12345 ios/aufspielen.sh"
    echo
    open -a Xcode 2>/dev/null || true
    exit 1
fi
merken team_id "$TEAM_ID"
echo "  Team: $TEAM_ID   App: $BUNDLE_ID"

# ---- Bauen ------------------------------------------------------------
if [ "$NEU_BAUEN" = 1 ]; then
    schritt "Xcode-Projekt bauen (ios/bauen.sh)"
    OHNE_XCODE=1 BUNDLE_ID="$BUNDLE_ID" "$SPIEL/ios/bauen.sh"
fi
VORLAGE="$BAU/DUSTFRONT/pygame-ios-template"
PROJEKT="$(find "$VORLAGE" -maxdepth 3 -name "*.xcodeproj" 2>/dev/null | head -n 1 || true)"
[ -n "$PROJEKT" ] || abbrechen "Kein Xcode-Projekt in $VORLAGE." \
                               "Erst ohne --nur-aufspielen laufen lassen."

SCHEMA="$(xcodebuild -list -json -project "$PROJEKT" 2>/dev/null | python3 -c '
import json, sys
try:
    p = json.load(sys.stdin)["project"]
except (ValueError, KeyError):
    sys.exit(0)
schemata = [s for s in p.get("schemes", []) if "test" not in s.lower()]
ziele = p.get("targets", [])
print((schemata or ziele or [""])[0])
')"
[ -n "$SCHEMA" ] || abbrechen "Im Projekt steht kein Schema." "Mit --xcode in Xcode nachsehen."

schritt "Signieren und bauen fuer $NAME (xcodebuild)"
echo "  Das dauert beim ersten Mal ein paar Minuten. Protokoll: $PROTOKOLL"
# -allowProvisioningUpdates legt Zertifikat und Profil selbst an, wie der
# Haken "Automatically manage signing" in Xcode. Dafuer muss die
# Apple-ID in Xcode angemeldet sein. -allowProvisioningDeviceRegistration
# traegt das Geraet beim Team ein, falls es dort noch fehlt.
if ! xcodebuild \
        -project "$PROJEKT" \
        -scheme "$SCHEMA" \
        -configuration Debug \
        -destination "id=$UDID" \
        -derivedDataPath "$ABGELEITET" \
        -allowProvisioningUpdates \
        -allowProvisioningDeviceRegistration \
        DEVELOPMENT_TEAM="$TEAM_ID" \
        CODE_SIGN_STYLE=Automatic \
        build > "$PROTOKOLL" 2>&1; then
    echo
    grep -E "error:|Signing|provision|Provisioning" "$PROTOKOLL" | tail -n 12 | sed 's/^/    /' || true
    hinweis="Mit --xcode oeffnen, unter Signing & Capabilities das Team waehlen und Run druecken."
    if grep -q "No Account\|No Accounts\|not signed in" "$PROTOKOLL"; then
        hinweis="In Xcode unter Settings -> Accounts die Apple-ID hinzufuegen."
    elif grep -q "is not available\|cannot be registered\|already been taken" "$PROTOKOLL"; then
        hinweis="Die Bundle-ID ist vergeben. Eine eigene waehlen: BUNDLE_ID=de.deinname.dustfront ios/aufspielen.sh"
    elif grep -q "Developer Mode\|developer mode" "$PROTOKOLL"; then
        hinweis="Auf dem Geraet den Entwicklermodus einschalten (Datenschutz & Sicherheit)."
    elif grep -q "locked\|Locked" "$PROTOKOLL"; then
        hinweis="Das Geraet entsperren und noch einmal."
    fi
    echo
    echo "  Bauen hat nicht geklappt. $hinweis"
    echo "  Xcode wird mit dem Projekt geoeffnet."
    echo
    open "$PROJEKT" || true
    exit 1
fi

APP="$(find "$ABGELEITET/Build/Products" -maxdepth 2 -type d -path "*-iphoneos/*.app" 2>/dev/null | head -n 1 || true)"
[ -n "$APP" ] || abbrechen "xcodebuild war fertig, aber keine App gefunden." "Protokoll: $PROTOKOLL"
APP_ID="$(/usr/libexec/PlistBuddy -c "Print :CFBundleIdentifier" "$APP/Info.plist" 2>/dev/null || echo "$BUNDLE_ID")"

# ---- Aufspielen und starten -------------------------------------------
schritt "Aufspielen auf $NAME"
xcrun devicectl device install app --device "$UDID" "$APP" \
    || abbrechen "Aufspielen hat nicht geklappt." \
                 "Ist das Geraet entsperrt und per Kabel dran?"

schritt "Starten"
starten() {         # starten [JSON mit Umgebungsvariablen]
    if [ -n "${1:-}" ]; then
        xcrun devicectl device process launch --device "$UDID" --terminate-existing \
            --environment-variables "$1" "$APP_ID"
    else
        xcrun devicectl device process launch --device "$UDID" --terminate-existing "$APP_ID"
    fi
}
UMGEBUNG=""
if [ "$TESTMODUS" = 1 ]; then
    # Liest rustfront_menu._startauftrag: gleich in den Testmodus.
    UMGEBUNG="{\"DUSTFRONT_START\": \"testmodus\", \"DUSTFRONT_KARTE\": \"${KARTE:-staubtal}\"}"
fi
if ! starten "$UMGEBUNG" > "$BAU/starten.log" 2>&1; then
    if [ -n "$UMGEBUNG" ] && grep -qi "environment" "$BAU/starten.log"; then
        # Eine aeltere devicectl-Fassung ohne Umgebung: dann eben normal,
        # der Testmodus steht im Hauptmenue.
        echo "  (Ohne Direktstart - TESTMODUS steht im Hauptmenue.)"
        TESTMODUS=0
        starten "" > "$BAU/starten.log" 2>&1 || true
    fi
fi
if grep -qi "error\|failed" "$BAU/starten.log"; then
    sed 's/^/    /' "$BAU/starten.log" | tail -n 6
    echo
    echo "  Die App ist drauf, liess sich aber nicht starten."
    echo "  Beim ersten Mal: auf dem Geraet unter Einstellungen -> Allgemein ->"
    echo "  VPN und Geraeteverwaltung dem eigenen Entwicklerzertifikat vertrauen,"
    echo "  dann DUSTFRONT antippen (oder: ios/aufspielen.sh --nur-aufspielen)."
    echo
    exit 1
fi

echo
echo "  Fertig: DUSTFRONT laeuft auf $NAME."
if [ "$TESTMODUS" = 1 ]; then
    echo "  Gestartet im Testmodus (Karte ${KARTE:-staubtal})."
fi
echo "  Mit einem kostenlosen Apple-Account laeuft die App 7 Tage - danach"
echo "  einfach noch einmal: ios/aufspielen.sh"
echo
