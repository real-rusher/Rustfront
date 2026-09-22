#!/usr/bin/env bash
# ============================================================
#  DUSTFRONT - LAN GASTGEBER
#  Macht eine Runde auf und waehlt die Spielart.
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
echo "  Spielart:"
echo "    1  PVP     jeder gegen jeden"
echo "    2  PVE     alle zusammen gegen Wellen, mit Aufhelfen"
echo "    3  PVPVE   Wellen, und dabei jeder gegen jeden"
echo
read -r -p "  Welche (Enter = 1): " WAHL
case "${WAHL:-1}" in
    2) MODUS="pve" ;;
    3) MODUS="pvpve" ;;
    *) MODUS="pvp" ;;
esac

ENDE="zeit"
WERT=0
if [ "$MODUS" != "pve" ]; then
    echo
    echo "  Wann endet die Runde?"
    echo "    1  nach Zeit"
    echo "    2  nach Abschuessen"
    echo
    read -r -p "  Welche (Enter = 1): " WAHL
    if [ "${WAHL:-1}" = "2" ]; then
        ENDE="abschuesse"
        read -r -p "  Abschuesse bis Schluss (Enter = 20): " WERT
        WERT="${WERT:-20}"
    else
        read -r -p "  Minuten (Enter = 5): " MINUTEN
        WERT=$(( ${MINUTEN:-5} * 60 ))
    fi
fi

KNAPP=""
if [ "$MODUS" != "pvp" ]; then
    echo
    read -r -p "  Munition begrenzen, mit Nachschubkisten? (j/N): " WAHL
    case "${WAHL:-n}" in
        j|J) KNAPP="--knapp" ;;
    esac
fi

echo
# shellcheck disable=SC2086
"$PY" -m dustfront --host --name "$NAME" --modus "$MODUS" \
    --ende "$ENDE" --wert "$WERT" $KNAPP \
    || abbrechen "Beendet mit einem Fehler."
