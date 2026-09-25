#!/usr/bin/env bash
# ============================================================
#  PROBELAUF - den Wandler laufen sehen und selbst fahren.
#
#  Zeigt die Laufmaschine von aussen: Beine, Gang, Schaden.
#  Wer das Spiel selbst will, nimmt DUSTFRONT.command daneben.
#
#  Unter macOS beim ersten Mal Rechtsklick -> Oeffnen.
# ============================================================
set -u

# In den Ordner dieser Datei wechseln. Beim Doppelklick im Finder
# ist das Arbeitsverzeichnis sonst das Benutzerverzeichnis.
cd "$(dirname "$0")" || exit 1

abbrechen() {
    echo
    echo "  $1"
    echo
    read -r -p "  Zum Schliessen Eingabetaste druecken. " _
    exit 1
}

PY=""
for kandidat in python3 python; do
    if command -v "$kandidat" >/dev/null 2>&1; then
        PY="$kandidat"
        break
    fi
done
[ -n "$PY" ] || abbrechen "Python wurde nicht gefunden. Hol es dir von python.org."

if ! "$PY" -c "import pygame" >/dev/null 2>&1; then
    echo
    echo "  pygame-ce fehlt. Wird jetzt installiert, das dauert"
    echo "  einmalig etwa eine Minute."
    echo
    "$PY" -m pip install pygame-ce || abbrechen "Installation fehlgeschlagen."
fi

echo
echo "  DUSTFRONT - Probelauf"
echo
echo "  W S Schub, A D Kurs, Shift Ueberlast"
echo "  H Autopilot, Tab Ansicht naeher oder weiter"
echo "  1 2 3 Warhound, Reaver, Imperator"
echo "  4 ein Bein ausfallen lassen, 5 alle richten"
echo "  F3 Zahlen, Esc zurueck"
echo
"$PY" -m dustfront --probe "$@" || abbrechen "Der Probelauf wurde mit einem Fehler beendet."
