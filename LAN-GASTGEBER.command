#!/usr/bin/env bash
# ============================================================
#  DUSTFRONT - LAN GASTGEBER
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
"$PY" -m dustfront --host --name "$NAME" \
    || abbrechen "Beendet mit einem Fehler."
