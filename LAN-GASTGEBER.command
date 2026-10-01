#!/usr/bin/env bash
# ============================================================
#  DUSTFRONT - LAN GASTGEBER
#  Macht eine Runde auf. Die Spielart und alles andere stellst
#  du danach im Spiel ein, in der Lobby (Taste P).
#  Unter macOS beim ersten Mal Rechtsklick -> Oeffnen.
# ============================================================
set -u
cd "$(dirname "$0")" || exit 1

abbrechen() {
    echo; echo "  $1"; echo
    read -r -p "  Zum Schliessen Eingabetaste druecken. " _
    exit 1
}

PY=""
for kandidat in python3 python; do
    command -v "$kandidat" >/dev/null 2>&1 && { PY="$kandidat"; break; }
done
[ -n "$PY" ] || abbrechen "Python wurde nicht gefunden. Hol es dir von python.org."

if ! "$PY" -c "import pygame" >/dev/null 2>&1; then
    echo; echo "  pygame-ce fehlt. Wird jetzt installiert."; echo
    "$PY" -m pip install pygame-ce || abbrechen "Installation fehlgeschlagen."
fi

echo
echo "  DUSTFRONT - LAN GASTGEBER"
echo
read -r -p "  Dein Name (Enter = GASTGEBER): " NAME
[ -n "${NAME:-}" ] || NAME="GASTGEBER"

echo
echo "  Wer soll mitspielen koennen?"
echo "    1  nur im eigenen Netz (LAN)"
echo "    2  auch ueber das Internet"
echo
read -r -p "  Welche (Enter = 1): " WAHL
ONLINE=""
PASSWORT=""
if [ "${WAHL:-1}" = "2" ]; then
    ONLINE="--online"
    echo
    echo "  Das Spiel versucht, den Port im Router selbst freizugeben."
    echo "  Klappt das nicht, sagt es gleich, was einzutragen ist."
    echo "  Wer die Adresse kennt, kann mitspielen - darum ein Kennwort:"
    read -r -p "  Kennwort (Enter = keins): " PASSWORT
fi

# Mehr wird hier nicht gefragt. Spielart, Karte, Runden und alles
# andere stellst du im Spiel ein: es geht zuerst in die Lobby, dort
# oeffnet P die Tafel dafuer.

echo
# shellcheck disable=SC2086
"$PY" -m dustfront --host --name "$NAME" --passwort "$PASSWORT" $ONLINE \
    || abbrechen "Beendet mit einem Fehler."
