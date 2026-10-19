"""
DUSTFRONT auf iOS - der Einstieg der App
=========================================

pygame-ios benennt diese Datei beim Bauen in `__main__.py` um und startet
sie, sobald die App aufgeht (siehe ios/LIESMICH.md). Sie tut nur das, was
vor dem Import von pygame passieren muss, und gibt dann an das
Hauptmenue weiter - genau wie DUSTFRONT.command auf dem Mac.

Die Einstellungen fuer SDL kommen als Umgebungsvariablen, weil pygame
sie nur beim Start liest:

* Querformat, in beide Richtungen. Das Spiel ist 16:9 und hat keine
  Fassung fuer hochkant.
* Der Balken unten (Home-Indikator) wird blass und braucht zwei Wischer.
  Sonst landet man mitten im Gefecht auf dem Homescreen, weil der linke
  Daumen beim Laufen nach unten rutscht.
"""

import os
import sys

os.environ.setdefault("SDL_IOS_ORIENTATIONS", "LandscapeLeft LandscapeRight")
os.environ.setdefault("SDL_IOS_HIDE_HOME_INDICATOR", "2")

HIER = os.path.dirname(os.path.abspath(__file__))
if HIER not in sys.path:
    sys.path.insert(0, HIER)

import rustfront_menu  # noqa: E402  (erst nach den Umgebungsvariablen)

rustfront_menu.main()
