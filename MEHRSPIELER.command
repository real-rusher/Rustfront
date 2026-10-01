#!/usr/bin/env bash
# ============================================================
#  DUSTFRONT MEHRSPIELER - unter macOS und Linux doppelklicken.
#
#  Startet direkt in die eigene Lobby, ohne Fragen. Anderen Lobbys
#  im selben Netz trittst du im Spiel bei (Esc -> ANDERER LOBBY
#  BEITRETEN). Ersetzt seit 0.32 LAN-GAST und LAN-GASTGEBER.
#
#  Unter macOS beim ersten Mal eventuell Rechtsklick -> Oeffnen,
#  sonst meckert der Gatekeeper.
#
#  Sucht Python, prueft pygame-ce und installiert es notfalls.
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

# Los, direkt in die eigene Lobby.
"$PY" -m dustfront --lobby "$@" || abbrechen "DUSTFRONT wurde mit einem Fehler beendet."
