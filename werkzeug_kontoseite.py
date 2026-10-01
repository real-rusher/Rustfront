"""Erzeugt KONTO.html - die Kontoseite zum Doppelklicken.

Warum ein Werkzeug und keine handgeschriebene Datei
---------------------------------------------------

Weil die Seite dieselben Sachen anzeigen muss, die im Spiel gelten:
dieselben Waffen, dieselben Namen der Werte, dieselben Farben, dieselbe
Schrift, denselben Zugang zum Server. Wer das von Hand doppelt pflegt,
pflegt es genau einmal - beim naechsten Mal laeuft es auseinander, und
dann zeigt die Seite Zahlen an, die es im Spiel gar nicht gibt.

Also steht hier nichts zweimal. Alles, was die Seite ueber DUSTFRONT
weiss, wird beim Erzeugen aus `dustfront.config`, `dustfront.font` und
`assets/` geholt und in die Datei hineingeschrieben.

Warum alles in **eine** Datei
-----------------------------

Weil sie lokal liegen und durch Doppelklick aufgehen soll. Eine Seite
unter `file://` darf keine Nachbardateien laden - kein `fetch` auf eine
JSON daneben, kein `<script src=...>`, das der Browser nicht verweigert.
Bilder gehen als `data:`-URI mit, die Schrift als Punktmuster, der Rest
steht im Quelltext. Eine Datei, kein Server, kein Installieren.

    python werkzeug_kontoseite.py            schreibt KONTO.html
    python -m dustfront --kontoseite         dasselbe aus dem Spiel heraus

Was die Seite **nicht** tut: sie rechnet nichts aus, was das Spiel
rechnet. Sie zeigt an, was auf dem Server steht, und schreibt genau
zwei Sachen zurueck - den Anzeigenamen und die Loadouts. Alles andere
ist zu lesen und nicht zu aendern; Zahlen, die man selbst setzen kann,
waeren keine Statistik mehr.
"""
from __future__ import annotations

import base64
import json
import os
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

ZIEL = "KONTO.html"


def _nur_lobby(modus) -> bool:
    return isinstance(modus, dict) and bool(modus.get("lobby"))


def _farbe(rgb) -> str:
    return "#%02x%02x%02x" % tuple(int(c) for c in rgb[:3])


def daten() -> dict:
    """Alles, was die Seite ueber das Spiel wissen muss, an einer Stelle."""
    import pygame

    pygame.init()
    pygame.display.set_mode((64, 64))

    from dustfront import ablage as A
    from dustfront import config as K
    from dustfront.font import _G, _TRANS, GH, GW
    from dustfront.core import Bilder
    from dustfront.main import asset_ordner

    bilder = Bilder(asset_ordner())

    def bild_uri(name: str) -> str:
        """Ein Spielbild als data:-URI. So braucht die Seite keine
        Nachbardateien - unter file:// duerfte sie die gar nicht laden."""
        import io

        puffer = io.BytesIO()
        pygame.image.save(bilder.bild(name).convert_alpha(), puffer, "PNG")
        return "data:image/png;base64," + base64.b64encode(
            puffer.getvalue()).decode("ascii")

    zugang = A.server_lesen()
    waffen = {}
    for schluessel, w in K.WAFFEN.items():
        waffen[schluessel] = {
            "name": w.get("name", schluessel.upper()),
            "art": w.get("art", ""),
            "bild": bild_uri(K.skin("%s_symbol" % schluessel)),
        }
    return {
        "version": K.VERSION,
        "phase": K.PHASE,
        "server": {"url": zugang["url"], "schluessel": zugang["schluessel"],
                   "postfach": zugang.get("postfach", "spieler.dustfront")},
        "werte": [{"schluessel": s, "name": n, "art": a} for s, n, a in K.WERTE],
        "waffenwerte": list(K.WAFFEN_WERTE),
        "waffen": waffen,
        "loadout": {
            "plaetze": K.LOADOUT["plaetze"],
            "waffen": K.LOADOUT["waffen"],
            "wuerfe": K.LOADOUT["wuerfe"],
            "auswahl_waffen": list(K.LOADOUT["auswahl_waffen"]),
            "auswahl_wuerfe": list(K.LOADOUT["auswahl_wuerfe"]),
            "vorlagen": [dict(v) for v in K.LOADOUT["vorlagen"]],
            "namenslaenge": K.LOADOUT["namenslaenge"],
        },
        # Nur den Namen, nicht die ganze Spielart: in K.MODI steht ein
        # Wuerfel voller Regeln, und die gehen die Seite nichts an. Die
        # Lobby nicht - aus ihr wird nie etwas gebucht, sie haette auf der
        # Seite eine Spalte, die immer leer bleibt.
        "modi": {k: (v.get("name") or k.upper()) if isinstance(v, dict) else str(v)
                 for k, v in K.MODI.items() if not _nur_lobby(v)},
        "modi_hinweis": {k: v.get("hinweis", "") for k, v in K.MODI.items()
                         if isinstance(v, dict) and not _nur_lobby(v)},
        "teams": [{"name": t["name"], "farbe": _farbe(t["hud"]),
                   "dunkel": _farbe(t["hud_dunkel"])}
                  for t in K.TEAMS["kombi"]],
        "seltenheit": [{"name": s["name"], "farbe": _farbe(s["farbe"]),
                        "anteil": s["anteil"]} for s in K.SELTENHEIT],
        "rollen": dict(sorted(K.SKIN_ROLLEN.items())),
        "figur": bild_uri(K.skin("figur")),
        "farben": {
            "amber": _farbe(K.C_AMBER), "creme": _farbe(K.C_CREAM),
            "matt": _farbe(K.C_MUTED), "matt_dunkel": _farbe(K.C_MUTED_DK),
            "grund": _farbe(K.C_VOID),
        },
        "schrift": {"breite": GW, "hoehe": GH, "zeichen": dict(_G),
                    "ersatz": dict(_TRANS)},
        "namenslaenge": A.NAMENSLAENGE,
        "wortlaenge": A.WORTLAENGE,
    }


def schreiben(pfad: str | Path = ZIEL) -> Path:
    d = daten()
    quelle = Path(__file__).with_name("kontoseite_vorlage.html")
    roh = quelle.read_text(encoding="utf-8")
    # Ein einziger Platzhalter. Er steht in der Vorlage in einer Zeile
    # fuer sich, damit man beim Lesen sofort sieht, wo die Daten
    # hineinkommen - und damit ein Suchen-und-Ersetzen nichts anderes
    # trifft.
    marke = "/*DATEN*/"
    if marke not in roh:
        raise SystemExit("In %s fehlt der Platzhalter %s" % (quelle, marke))
    text = roh.replace(marke, json.dumps(d, ensure_ascii=False, indent=1))
    ziel = Path(pfad)
    ziel.write_text(text, encoding="utf-8")
    return ziel


if __name__ == "__main__":
    import sys

    ziel = schreiben(sys.argv[1] if len(sys.argv) > 1 else ZIEL)
    print("geschrieben: %s (%.0f KB)"
          % (ziel, ziel.stat().st_size / 1024.0))
    print("Zum Ansehen: die Datei doppelklicken.")
