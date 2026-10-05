"""Startet SCHNEEFELD als normale Einzelspielerpartie in einem eigenen Fenster."""

from __future__ import annotations

from dustfront.main import starten


if __name__ == "__main__":
    raise SystemExit(starten(auftrag={"karte": "schneefeld"}))
