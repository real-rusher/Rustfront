#!/usr/bin/env bash
# ============================================================
#  DUSTFRONT - LAN GAST
#  Verbindet sich mit einem Gastgeber. Die Spielart bestimmt der.
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
echo "  DUSTFRONT - LAN GAST"
echo
read -r -p "  Dein Name (Enter = GAST): " NAME
[ -n "${NAME:-}" ] || NAME="GAST"

echo
echo "  Die Spielart bestimmt der Gastgeber."
echo
echo "  In welche Mannschaft willst du, falls mit Mannschaften gespielt wird?"
echo "    1  ROT"
echo "    2  BLAU"
echo "    3  egal, teil mich ein"
echo
read -r -p "  Welche (Enter = 3): " WAHL
case "${WAHL:-3}" in
    1) TEAM="rot" ;;
    2) TEAM="blau" ;;
    *) TEAM="auto" ;;
esac

echo
WOHIN=""
while [ -z "$WOHIN" ]; do
    read -r -p "  Adresse des Gastgebers: " WOHIN
done
read -r -p "  Kennwort, falls eines gilt (Enter = keins): " PASSWORT

echo
"$PY" -m dustfront --join "$WOHIN" --name "$NAME" --team "$TEAM" \
    --passwort "${PASSWORT:-}" \
    || abbrechen "Beendet mit einem Fehler."
