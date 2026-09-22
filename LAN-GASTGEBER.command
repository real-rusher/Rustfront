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
echo "    4  TEAM    zwei Mannschaften, Abschuesse zaehlen fuer das Team"
echo "    5  VERSUS  zwei Mannschaften, ein Leben je Runde, mit Aufhelfen"
echo "    6  HUEGEL  zwei Mannschaften, haltet den Kreis in der Mitte"
echo
read -r -p "  Welche (Enter = 1): " WAHL
case "${WAHL:-1}" in
    2) MODUS="pve" ;;
    3) MODUS="pvpve" ;;
    4) MODUS="team" ;;
    5) MODUS="versus" ;;
    6) MODUS="huegel" ;;
    *) MODUS="pvp" ;;
esac

ENDE="zeit"
WERT=0
case "$MODUS" in
    pvp|pvpve|team)
        echo
        echo "  Wann endet die Runde?"
        echo "    1  nach Zeit"
        echo "    2  nach Abschuessen"
        echo
        read -r -p "  Welche (Enter = 1): " WAHL
        if [ "${WAHL:-1}" = "2" ]; then
            ENDE="abschuesse"
            if [ "$MODUS" = "team" ]; then
                read -r -p "  Teamabschuesse bis Schluss (Enter = 30): " WERT
                WERT="${WERT:-30}"
            else
                read -r -p "  Abschuesse bis Schluss (Enter = 20): " WERT
                WERT="${WERT:-20}"
            fi
        else
            read -r -p "  Minuten (Enter = 5): " MINUTEN
            WERT=$(( ${MINUTEN:-5} * 60 ))
        fi
        ;;
    versus|huegel)
        # Beide enden von selbst: versus nach Rundensiegen, huegel am
        # vollen Kreis. Die Zeit ist nur die Notbremse.
        echo
        read -r -p "  Hoechstdauer in Minuten (Enter = 10): " MINUTEN
        WERT=$(( ${MINUTEN:-10} * 60 ))
        ;;
esac

KNAPP=""
if [ "$MODUS" != "pvp" ]; then
    echo
    read -r -p "  Munition begrenzen, mit Nachschubkisten? (j/N): " WAHL
    case "${WAHL:-n}" in
        j|J) KNAPP="--knapp" ;;
    esac
fi

echo
read -r -p "  Einstiegsschutz, 2 Sekunden unverwundbar? (J/n): " WAHL
SCHUTZ=""
case "${WAHL:-j}" in
    n|N) SCHUTZ="--kein-schutz" ;;
esac

echo
read -r -p "  Medkits beim Einstieg (Enter = 1): " MEDKITS
MEDKITS="${MEDKITS:-1}"

read -r -p "  Medkits immer wieder auf der Karte? (J/n): " WAHL
MEDSPAWN=""
case "${WAHL:-j}" in
    n|N) MEDSPAWN="--keine-medkits" ;;
esac

echo
# shellcheck disable=SC2086
"$PY" -m dustfront --host --name "$NAME" --modus "$MODUS" \
    --ende "$ENDE" --wert "$WERT" --medkits "$MEDKITS" \
    $KNAPP $SCHUTZ $MEDSPAWN \
    || abbrechen "Beendet mit einem Fehler."
