#!/usr/bin/env bash
# ============================================================
#  SPIELTEST - direkt ins Spiel, ohne Menue und ohne Intro.
#
#  Zum Ausprobieren der Spielmechanik. Wer das ganze Spiel mit
#  Menue will, nimmt DUSTFRONT.command daneben.
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
echo "  DUSTFRONT - Spieltest"
echo
echo "  W A S D laufen, Maus zielen, links schiessen"
echo "  1 bis 6 Waffe, R nachladen, H Medkit"
echo "  E Treppe, Mausrad Ebene ansehen, Tab Inventar"
echo "  T Ziellinie, Esc Pause"
echo
"$PY" -m dustfront "$@" || abbrechen "Der Spieltest wurde mit einem Fehler beendet."
