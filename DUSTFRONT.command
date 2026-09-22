#!/usr/bin/env bash
# ============================================================
#  DUSTFRONT starten - unter macOS und Linux doppelklicken.
#
#  Unter macOS beim ersten Mal eventuell Rechtsklick -> Oeffnen,
#  sonst meckert der Gatekeeper.
#
#  Sucht Python, prueft pygame-ce, installiert es notfalls und
#  startet das Hauptmenue.
# ============================================================
set -u

# In den Ordner wechseln, in dem diese Datei liegt. Beim
# Doppelklick im Finder ist das Arbeitsverzeichnis sonst das
# Benutzerverzeichnis, und dann findet Python nichts.
cd "$(dirname "$0")" || exit 1

abbrechen() {
    echo
    echo "  $1"
    echo
    read -r -p "  Zum Schliessen Eingabetaste druecken. " _
    exit 1
}

# Python suchen.
PY=""
for kandidat in python3 python; do
    if command -v "$kandidat" >/dev/null 2>&1; then
        PY="$kandidat"
        break
    fi
done
[ -n "$PY" ] || abbrechen "Python wurde nicht gefunden. Hol es dir von python.org."

# pygame-ce pruefen und bei Bedarf nachinstallieren.
if ! "$PY" -c "import pygame" >/dev/null 2>&1; then
    echo
    echo "  pygame-ce fehlt. Wird jetzt installiert, das dauert"
    echo "  einmalig etwa eine Minute."
    echo
    "$PY" -m pip install pygame-ce || abbrechen "Installation fehlgeschlagen."
fi

# Los. Argumente werden durchgereicht, also geht auch --nosplash.
"$PY" rustfront_menu.py "$@" || abbrechen "DUSTFRONT wurde mit einem Fehler beendet."
